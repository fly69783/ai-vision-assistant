const MAX_FILE_BYTES = 8 * 1024 * 1024;
const REQUEST_TIMEOUT_MS = 30_000;
const HEALTH_TIMEOUT_MS = 6_000;
const ALLOWED_FILE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

const form = document.querySelector("#analysis-form");
const fileInput = document.querySelector("#image-file");
const cameraInput = document.querySelector("#camera-file");
const fileDrop = document.querySelector("#file-drop");
const fileError = document.querySelector("#file-error");
const fileDetails = document.querySelector("#file-details");
const clearImageButton = document.querySelector("#clear-image-button");
const taskSelect = document.querySelector("#task");
const targetField = document.querySelector("#target-field");
const targetInput = document.querySelector("#target");
const queryField = document.querySelector("#query-field");
const queryInput = document.querySelector("#query");
const previewWrap = document.querySelector("#preview-wrap");
const imagePreview = document.querySelector("#image-preview");
const submitButton = document.querySelector("#submit-button");
const serviceState = document.querySelector("#service-state");
const serviceStateText = document.querySelector("#service-state-text");
const networkBanner = document.querySelector("#network-banner");
const networkBannerTitle = document.querySelector("#network-banner-title");
const networkBannerMessage = document.querySelector("#network-banner-message");
const installButton = document.querySelector("#install-button");
const updateButton = document.querySelector("#update-button");
const capabilityList = document.querySelector("#capability-list");
const resultPanel = document.querySelector(".result-panel");
const resultTitle = document.querySelector("#result-title");
const emptyResult = document.querySelector("#empty-result");
const resultContent = document.querySelector("#result-content");
const resultBadge = document.querySelector("#result-badge");
const requestTime = document.querySelector("#request-time");
const narration = document.querySelector("#narration");
const resultMessage = document.querySelector("#result-message");
const qualityGrid = document.querySelector("#quality-grid");
const warningsSection = document.querySelector("#warnings-section");
const warningsList = document.querySelector("#warnings-list");
const evidenceSection = document.querySelector("#evidence-section");
const evidenceList = document.querySelector("#evidence-list");
const speakButton = document.querySelector("#speak-button");
const stopSpeechButton = document.querySelector("#stop-speech-button");
const speechState = document.querySelector("#speech-state");
const resultAnnouncer = document.querySelector("#result-announcer");

let selectedFile = null;
let previewUrl = null;
let deferredInstallPrompt = null;
let waitingServiceWorker = null;
let reloadingForUpdate = false;

const statusLabels = {
  success: "分析成功",
  partial: "部分完成",
  no_result: "没有可靠结果",
  unavailable: "能力未配置",
  rejected: "画面不合格",
  error: "运行错误",
};

const providerLabels = {
  detector: "目标检测",
  ocr: "文字识别",
  vision: "视觉理解",
};

function setHidden(element, hidden) {
  element.hidden = hidden;
  element.classList.toggle("is-hidden", hidden);
}

function setServiceState(text, className = "") {
  serviceState.classList.remove("is-online", "is-offline");
  if (className) serviceState.classList.add(className);
  serviceStateText.textContent = text;
}

function setConnectionNotice(title = "", message = "") {
  networkBanner.hidden = !title;
  networkBannerTitle.textContent = title;
  networkBannerMessage.textContent = message;
}

function setFileError(message = "") {
  fileError.textContent = message;
  fileError.hidden = !message;
  fileDrop.classList.toggle("has-error", Boolean(message));
}

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validateFile(file) {
  if (!file) return "请先拍照或选择一张图片。";
  if (!ALLOWED_FILE_TYPES.has(file.type)) return "只支持JPEG、PNG或WebP图片。";
  if (file.size === 0) return "这张图片是空文件，请重新选择。";
  if (file.size > MAX_FILE_BYTES) return "图片超过8MB，请压缩或重新拍摄。";
  return "";
}

function resetResult(message = "尚未提交图片") {
  window.speechSynthesis?.cancel();
  setHidden(resultContent, true);
  setHidden(emptyResult, false);
  emptyResult.querySelector("p").textContent = message;
  resultAnnouncer.textContent = "";
  speechState.textContent = "";
}

function clearSelectedFile({ keepError = false } = {}) {
  selectedFile = null;
  fileInput.value = "";
  cameraInput.value = "";
  imagePreview.removeAttribute("src");
  imagePreview.alt = "待分析图片预览";
  fileDetails.textContent = "已选择图片";
  setHidden(previewWrap, true);
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  if (!keepError) setFileError();
  resetResult();
}

async function useFile(file, sourceLabel) {
  const validationMessage = validateFile(file);
  if (validationMessage) {
    clearSelectedFile({ keepError: true });
    setFileError(validationMessage);
    resultAnnouncer.textContent = validationMessage;
    return;
  }

  const candidateUrl = URL.createObjectURL(file);
  imagePreview.src = candidateUrl;
  try {
    if (typeof imagePreview.decode === "function") await imagePreview.decode();
  } catch {
    URL.revokeObjectURL(candidateUrl);
    clearSelectedFile({ keepError: true });
    setFileError("浏览器无法读取这张图片，请换一张或重新拍摄。");
    return;
  }

  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = candidateUrl;
  selectedFile = file;
  imagePreview.alt = `待分析图片预览：${file.name || "手机拍摄图片"}`;
  fileDetails.textContent = `${sourceLabel} · ${file.name || "手机拍摄图片"} · ${formatFileSize(file.size)}`;
  setFileError();
  setHidden(previewWrap, false);
  resetResult("图片已准备好，尚未开始分析");
}

function renderCapabilities(capabilities = []) {
  capabilityList.replaceChildren();
  if (!capabilities.length) {
    capabilityList.textContent = "服务没有返回能力状态。";
    return;
  }

  capabilities.forEach((capability) => {
    const item = document.createElement("div");
    item.className = "capability-item";
    item.dataset.configured = String(capability.configured);

    const heading = document.createElement("div");
    const name = document.createElement("strong");
    const state = document.createElement("span");
    name.textContent = providerLabels[capability.provider] || capability.provider;
    state.className = "capability-state";
    state.textContent = capability.configured ? "已配置" : "待接入";
    heading.append(name, state);

    const message = document.createElement("p");
    message.textContent = capability.message;
    item.append(heading, message);
    capabilityList.append(item);
  });
}

async function fetchWithTimeout(resource, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(resource, { ...options, signal: controller.signal });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function readJsonResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error("服务返回了无法识别的内容，请检查后端是否正常启动。");
  }
  return response.json();
}

function apiErrorMessage(data, statusCode) {
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail)) {
    return data.detail.map((item) => item.msg || "输入内容不符合要求").join("；");
  }
  return `请求失败：HTTP ${statusCode}`;
}

async function checkHealth() {
  if (!navigator.onLine) {
    setServiceState("当前离线", "is-offline");
    setConnectionNotice(
      "当前处于离线状态",
      "仍可查看页面，但图片分析需要连接后端服务。",
    );
    capabilityList.textContent = "恢复网络后会重新读取AI能力状态。";
    return;
  }

  setServiceState("正在检查服务");
  try {
    const response = await fetchWithTimeout(
      "/api/v1/health",
      { headers: { Accept: "application/json" }, cache: "no-store" },
      HEALTH_TIMEOUT_MS,
    );
    const health = await readJsonResponse(response);
    if (!response.ok) throw new Error(apiErrorMessage(health, response.status));
    const readyCount = health.capabilities.filter((item) => item.configured).length;
    setServiceState(`服务在线 · ${readyCount}/3项能力已配置`, "is-online");
    setConnectionNotice();
    renderCapabilities(health.capabilities);
  } catch (error) {
    const message = error.name === "AbortError" ? "服务检查超时" : "服务未连接";
    setServiceState(message, "is-offline");
    setConnectionNotice(
      navigator.onLine ? "分析服务暂时不可达" : "当前处于离线状态",
      "网页外壳仍可使用，恢复连接或启动后端后即可继续分析。",
    );
    capabilityList.textContent = `暂时无法读取能力状态：${error.message}`;
  }
}

function updateTaskFields() {
  const task = taskSelect.value;
  const needsTarget = task === "find_object";
  const needsQuery = task === "visual_question";
  setHidden(targetField, !needsTarget);
  setHidden(queryField, !needsQuery);
  targetInput.required = needsTarget;
  queryInput.required = needsQuery;
  targetInput.setCustomValidity("");
  queryInput.setCustomValidity("");
}

function addMetric(label, value) {
  const item = document.createElement("div");
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value;
  item.append(term, description);
  qualityGrid.append(item);
}

function renderList(section, list, values, formatter) {
  list.replaceChildren();
  setHidden(section, !values.length);
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = formatter(value);
    list.append(item);
  });
}

function focusResult(summary) {
  resultAnnouncer.textContent = summary;
  window.requestAnimationFrame(() => {
    resultTitle.focus({ preventScroll: true });
    resultPanel.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start",
    });
  });
}

function renderResult(data) {
  setHidden(emptyResult, true);
  setHidden(resultContent, false);
  resultBadge.dataset.status = data.status;
  resultBadge.textContent = statusLabels[data.status] || data.status;
  requestTime.textContent = `耗时 ${Number(data.latency_ms).toFixed(1)} ms`;
  narration.textContent = data.narration;
  const message = data.message || "";
  const repeatedMessage = message.trim() === data.narration.trim();
  resultMessage.textContent = repeatedMessage ? "" : message;
  setHidden(resultMessage, repeatedMessage);
  speechState.textContent = "";

  qualityGrid.replaceChildren();
  addMetric("画面尺寸", `${data.quality.width} × ${data.quality.height}`);
  addMetric("平均亮度", Number(data.quality.brightness).toFixed(1));
  addMetric("清晰度分数", Number(data.quality.blur_score).toFixed(1));
  addMetric("质量结论", data.quality.status === "accepted" ? "可以分析" : "建议重拍");

  renderList(warningsSection, warningsList, data.warnings || [], (item) => item);
  renderList(
    evidenceSection,
    evidenceList,
    data.evidence || [],
    (item) => `${providerLabels[item.source] || item.source} · ${item.content} · 置信度${item.confidence}`,
  );
  focusResult(`${resultBadge.textContent}。${data.narration}`);
}

function renderError(message) {
  setHidden(emptyResult, true);
  setHidden(resultContent, false);
  resultBadge.dataset.status = "error";
  resultBadge.textContent = "请求失败";
  requestTime.textContent = "";
  narration.textContent = "这次没有完成分析。";
  resultMessage.textContent = message;
  setHidden(resultMessage, false);
  qualityGrid.replaceChildren();
  setHidden(warningsSection, true);
  setHidden(evidenceSection, true);
  speechState.textContent = "";
  focusResult(`请求失败。${message}`);
}

function setSubmitting(isSubmitting) {
  submitButton.disabled = isSubmitting;
  submitButton.setAttribute("aria-busy", String(isSubmitting));
  submitButton.classList.toggle("is-loading", isSubmitting);
  submitButton.firstElementChild.textContent = isSubmitting ? "正在检查与分析" : "开始分析";
}

function updateNetworkState() {
  const isOffline = !navigator.onLine;
  document.body.classList.toggle("is-offline", isOffline);
  if (isOffline) {
    setConnectionNotice(
      "当前处于离线状态",
      "仍可查看页面，但图片分析需要连接后端服务。",
    );
    setServiceState("当前离线", "is-offline");
    capabilityList.textContent = "恢复网络后会重新读取AI能力状态。";
  } else {
    checkHealth();
  }
}

fileInput.addEventListener("change", () => useFile(fileInput.files[0], "相册或文件"));
cameraInput.addEventListener("change", () => useFile(cameraInput.files[0], "手机拍摄"));
clearImageButton.addEventListener("click", () => {
  clearSelectedFile();
  cameraInput.focus();
});
taskSelect.addEventListener("change", updateTaskFields);
targetInput.addEventListener("input", () => targetInput.setCustomValidity(""));
queryInput.addEventListener("input", () => queryInput.setCustomValidity(""));

["dragenter", "dragover"].forEach((eventName) => {
  fileDrop.addEventListener(eventName, (event) => {
    event.preventDefault();
    fileDrop.classList.add("is-dragging");
  });
});

fileDrop.addEventListener("dragleave", (event) => {
  if (!fileDrop.contains(event.relatedTarget)) fileDrop.classList.remove("is-dragging");
});

fileDrop.addEventListener("drop", (event) => {
  event.preventDefault();
  fileDrop.classList.remove("is-dragging");
  const [file] = event.dataTransfer.files;
  useFile(file, "拖放文件");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const validationMessage = validateFile(selectedFile);
  if (validationMessage) {
    setFileError(validationMessage);
    resultAnnouncer.textContent = validationMessage;
    cameraInput.focus();
    return;
  }
  const trimmedTarget = targetInput.value.trim();
  const trimmedQuery = queryInput.value.trim();
  targetInput.setCustomValidity(
    taskSelect.value === "find_object" && !trimmedTarget ? "请输入要查找的物品。" : "",
  );
  queryInput.setCustomValidity(
    taskSelect.value === "visual_question" && !trimmedQuery ? "请输入你想问的问题。" : "",
  );
  if (!form.reportValidity()) return;
  if (!navigator.onLine) {
    renderError("当前没有网络连接。网页可以离线打开，但图片分析需要连接后端服务。");
    return;
  }

  setSubmitting(true);
  window.speechSynthesis?.cancel();
  resultAnnouncer.textContent = "正在检查画面并分析，请稍候。";

  const body = new FormData(form);
  body.set("file", selectedFile, selectedFile.name || `capture-${Date.now()}.jpg`);
  if (trimmedTarget) body.set("target", trimmedTarget);
  else body.delete("target");
  if (trimmedQuery) body.set("query", trimmedQuery);
  else body.delete("query");

  try {
    const response = await fetchWithTimeout("/api/v1/analyze", { method: "POST", body });
    const data = await readJsonResponse(response);
    if (!response.ok) throw new Error(apiErrorMessage(data, response.status));
    renderResult(data);
  } catch (error) {
    if (error.name === "AbortError") {
      renderError("等待超过30秒，已停止本次请求。请检查网络或模型服务后重试。");
    } else if (!navigator.onLine) {
      renderError("请求过程中网络断开了，请恢复连接后重试。");
    } else if (error instanceof TypeError) {
      renderError("无法连接分析服务，请确认后端已经启动。");
    } else {
      renderError(error.message);
    }
  } finally {
    setSubmitting(false);
  }
});

if (!("speechSynthesis" in window)) {
  speakButton.disabled = true;
  stopSpeechButton.disabled = true;
  speechState.textContent = "当前浏览器不支持语音朗读。";
}

speakButton.addEventListener("click", () => {
  if (!("speechSynthesis" in window) || !narration.textContent) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(narration.textContent);
  utterance.lang = "zh-CN";
  utterance.rate = 1;
  utterance.onstart = () => {
    speechState.textContent = "正在朗读结果。";
  };
  utterance.onend = () => {
    speechState.textContent = "朗读完成。";
  };
  utterance.onerror = () => {
    speechState.textContent = "朗读失败，可以直接阅读上方文字。";
  };
  window.speechSynthesis.speak(utterance);
});

stopSpeechButton.addEventListener("click", () => {
  window.speechSynthesis?.cancel();
  speechState.textContent = "已停止朗读。";
});

window.addEventListener("online", updateNetworkState);
window.addEventListener("offline", updateNetworkState);
window.addEventListener("pagehide", () => {
  window.speechSynthesis?.cancel();
  if (previewUrl) URL.revokeObjectURL(previewUrl);
});

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  installButton.hidden = false;
});

installButton.addEventListener("click", async () => {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  installButton.hidden = true;
});

window.addEventListener("appinstalled", () => {
  deferredInstallPrompt = null;
  installButton.hidden = true;
  resultAnnouncer.textContent = "视界助手已经安装到设备。";
});

updateButton.addEventListener("click", () => {
  waitingServiceWorker?.postMessage({ type: "SKIP_WAITING" });
  updateButton.disabled = true;
  updateButton.textContent = "正在更新";
});

async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  try {
    const registration = await navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
    if (registration.waiting) {
      waitingServiceWorker = registration.waiting;
      updateButton.hidden = false;
    }
    registration.addEventListener("updatefound", () => {
      const installingWorker = registration.installing;
      installingWorker?.addEventListener("statechange", () => {
        if (installingWorker.state === "installed" && navigator.serviceWorker.controller) {
          waitingServiceWorker = installingWorker;
          updateButton.hidden = false;
        }
      });
    });
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (reloadingForUpdate) return;
      reloadingForUpdate = true;
      window.location.reload();
    });
  } catch (error) {
    console.warn("Service Worker注册失败：", error);
  }
}

const requestedTask = new URLSearchParams(window.location.search).get("task");
if ([...taskSelect.options].some((option) => option.value === requestedTask)) {
  taskSelect.value = requestedTask;
}

if (window.matchMedia("(display-mode: standalone)").matches) installButton.hidden = true;
updateTaskFields();
updateNetworkState();
registerServiceWorker();
