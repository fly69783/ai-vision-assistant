const form = document.querySelector("#analysis-form");
const fileInput = document.querySelector("#image-file");
const fileLabel = document.querySelector("#file-label");
const fileDrop = document.querySelector("#file-drop");
const taskSelect = document.querySelector("#task");
const targetField = document.querySelector("#target-field");
const targetInput = document.querySelector("#target");
const queryField = document.querySelector("#query-field");
const queryInput = document.querySelector("#query");
const previewWrap = document.querySelector("#preview-wrap");
const imagePreview = document.querySelector("#image-preview");
const submitButton = document.querySelector("#submit-button");
const serviceState = document.querySelector("#service-state");
const capabilityList = document.querySelector("#capability-list");
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

let previewUrl = null;

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

function setServiceState(text, className) {
  serviceState.classList.remove("is-online", "is-offline");
  if (className) serviceState.classList.add(className);
  serviceState.lastChild.textContent = text;
}

function renderCapabilities(capabilities) {
  capabilityList.replaceChildren();
  capabilities.forEach((capability) => {
    const item = document.createElement("div");
    item.className = "capability-item";

    const name = document.createElement("strong");
    name.textContent = providerLabels[capability.provider] || capability.provider;

    const message = document.createElement("p");
    message.textContent = `${capability.configured ? "已配置" : "未配置"} · ${capability.message}`;

    item.append(name, message);
    capabilityList.append(item);
  });
}

async function checkHealth() {
  try {
    const response = await fetch("/api/v1/health", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const health = await response.json();
    const readyCount = health.capabilities.filter((item) => item.configured).length;
    setServiceState(`服务在线 · ${readyCount}/3项能力已配置`, "is-online");
    renderCapabilities(health.capabilities);
  } catch (error) {
    setServiceState("服务未连接", "is-offline");
    capabilityList.textContent = `无法读取能力状态：${error.message}`;
  }
}

function updateTaskFields() {
  const task = taskSelect.value;
  const needsTarget = task === "find_object";
  const needsQuery = task === "visual_question";
  targetField.classList.toggle("is-hidden", !needsTarget);
  queryField.classList.toggle("is-hidden", !needsQuery);
  targetInput.required = needsTarget;
  queryInput.required = needsQuery;
}

function showPreview(file) {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  if (!file) {
    previewWrap.classList.add("is-hidden");
    fileLabel.textContent = "选择一张图片";
    return;
  }
  previewUrl = URL.createObjectURL(file);
  imagePreview.src = previewUrl;
  fileLabel.textContent = file.name;
  previewWrap.classList.remove("is-hidden");
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
  section.classList.toggle("is-hidden", !values.length);
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = formatter(value);
    list.append(item);
  });
}

function renderResult(data) {
  emptyResult.classList.add("is-hidden");
  resultContent.classList.remove("is-hidden");
  resultBadge.dataset.status = data.status;
  resultBadge.textContent = statusLabels[data.status] || data.status;
  requestTime.textContent = `${data.latency_ms.toFixed(1)} ms`;
  narration.textContent = data.narration;
  const repeatedMessage = data.message.trim() === data.narration.trim();
  resultMessage.textContent = repeatedMessage ? "" : data.message;
  resultMessage.classList.toggle("is-hidden", repeatedMessage);

  qualityGrid.replaceChildren();
  addMetric("画面尺寸", `${data.quality.width} × ${data.quality.height}`);
  addMetric("平均亮度", data.quality.brightness.toFixed(1));
  addMetric("清晰度分数", data.quality.blur_score.toFixed(1));
  addMetric("质量结论", data.quality.status === "accepted" ? "可以分析" : "建议重拍");

  renderList(warningsSection, warningsList, data.warnings, (item) => item);
  renderList(
    evidenceSection,
    evidenceList,
    data.evidence,
    (item) => `${providerLabels[item.source] || item.source} · ${item.content} · 置信度${item.confidence}`,
  );
}

function renderError(message) {
  emptyResult.classList.add("is-hidden");
  resultContent.classList.remove("is-hidden");
  resultBadge.dataset.status = "error";
  resultBadge.textContent = "请求失败";
  requestTime.textContent = "";
  narration.textContent = "这次没有完成分析。";
  resultMessage.textContent = message;
  resultMessage.classList.remove("is-hidden");
  qualityGrid.replaceChildren();
  warningsSection.classList.add("is-hidden");
  evidenceSection.classList.add("is-hidden");
}

fileInput.addEventListener("change", () => showPreview(fileInput.files[0]));
taskSelect.addEventListener("change", updateTaskFields);

["dragenter", "dragover"].forEach((eventName) => {
  fileDrop.addEventListener(eventName, (event) => {
    event.preventDefault();
    fileDrop.classList.add("is-dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  fileDrop.addEventListener(eventName, (event) => {
    event.preventDefault();
    fileDrop.classList.remove("is-dragging");
  });
});

fileDrop.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer.files;
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  showPreview(file);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  submitButton.disabled = true;
  submitButton.firstElementChild.textContent = "正在检查与分析";
  window.speechSynthesis?.cancel();

  const body = new FormData(form);
  try {
    const response = await fetch("/api/v1/analyze", { method: "POST", body });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `请求失败：HTTP ${response.status}`);
    renderResult(data);
  } catch (error) {
    renderError(error.message);
  } finally {
    submitButton.disabled = false;
    submitButton.firstElementChild.textContent = "开始分析";
  }
});

speakButton.addEventListener("click", () => {
  if (!("speechSynthesis" in window) || !narration.textContent) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(narration.textContent);
  utterance.lang = "zh-CN";
  utterance.rate = 1;
  window.speechSynthesis.speak(utterance);
});

stopSpeechButton.addEventListener("click", () => window.speechSynthesis?.cancel());

updateTaskFields();
checkHealth();
