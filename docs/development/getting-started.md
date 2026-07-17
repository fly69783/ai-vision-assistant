# 开发入门

## 1. 打开项目

用VS Code或PyCharm打开克隆得到的仓库根目录（例如`D:/ai-vision-assistant`），不要只打开某一个Python文件。

## 2. 激活环境

在Anaconda Prompt中运行：

```powershell
conda activate ai-vision
python --version
```

应看到Python 3.11.x。如果不是3.11，先不要安装依赖。

## 3. 安装依赖

```powershell
python -m pip install -r requirements-dev.txt
```

`requirements.txt`只含基础服务需要的包；`requirements-dev.txt`另外包含测试和代码检查工具。

安装本地目标检测与OCR：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_local_ai.ps1 -Enable
```

这个脚本要求环境中已经安装匹配显卡的Torch和Torchvision，并会安装RapidOCR、ONNX Runtime、缓存模型和保存本地能力开关。完成后关闭并重新打开终端。

安装本地Qwen3-VL视觉理解模型：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_local_vlm.ps1 -Enable
```

脚本会安装或复用Ollama，下载`qwen3-vl:4b-instruct-q4_K_M`（约3.3GB），并把项目切换为仅本地视觉模式。完成后重开终端。第一次分析需要把模型加载到显卡，通常明显慢于后续请求。

不再使用时可释放模型占用的显存，权重仍保留在硬盘：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_local_vlm.ps1
```

## 4. 检查环境

```powershell
python scripts/check_environment.py
```

基础检查通过后，还可以单独验证和预热本地模型：

```powershell
python scripts/check_local_ai.py
```

最终能力状态以启动后的`/api/v1/health`为准；正常配置应显示3/3项能力可用。

## 5. 启动项目

最简单的Windows方式：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_dev.ps1
```

也可以手动启动：

```powershell
python -m uvicorn app.main:app --reload
```

打开：

- 网页测试台：<http://127.0.0.1:8000>
- API文档：<http://127.0.0.1:8000/api/v1/docs>
- 健康检查：<http://127.0.0.1:8000/api/v1/health>

## 6. 运行测试

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1
```

每次提交前至少保证Ruff和pytest通过。

## 7. 在手机上测试网页/PWA

本机浏览器访问`http://127.0.0.1:8000`可以测试PWA。手机不能访问电脑的`127.0.0.1`；需要让后端监听局域网地址，并让手机通过同一Wi-Fi下电脑的地址访问。摄像头和PWA安装在非`localhost`环境通常要求HTTPS，所以正式真机验收应使用HTTPS反向代理或部署地址。

真机至少检查：后置摄像头拍照、相册选图、安装到主屏幕、语音播报、断网提示、网络恢复和长文字换行。不要在测试中使用证件、人脸、住址等敏感原图。

前端静态文件发布时还要提升`frontend/web/service-worker.js`中的缓存版本，避免已安装页面继续使用旧资源。

## 常见问题

### 页面显示“能力未配置”是不是报错？

不是。这表示对应能力的开关、依赖或密钥不完整。健康检查会分别说明目标检测、OCR和视觉模型缺少什么。

### 本地Qwen会不会一直占用显存？

不会永久占用。默认一次请求后保留5分钟以加快连续追问，之后Ollama会自动卸载；也可以随时运行`stop_local_vlm.ps1`立即释放。Ollama后台服务本身占用少量内存，3.3GB模型文件会一直保留在硬盘。

### 为什么普通PowerShell里找不到conda？

Anaconda没有为普通PowerShell初始化。初学阶段可以直接使用Anaconda Prompt；不要为了省一步随意修改系统PATH。

### 为什么使用`python -m pip`？

这样可以确认包安装到了当前Python环境，避免把依赖装到其他Python版本。

### 为什么手机打不开电脑上的`127.0.0.1`？

手机里的`127.0.0.1`指手机自己，不是电脑。需要使用电脑在当前局域网中的IP，并确认防火墙和端口允许访问；涉及摄像头和安装时还要使用HTTPS。

### 断网后页面能打开，为什么不能分析？

这是预期行为。PWA只缓存不含隐私数据的页面外壳，分析API、上传图片和结果不缓存，必须连接后端才能分析。
