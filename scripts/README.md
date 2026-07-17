# scripts

- `check_environment.py`：检查Python版本、基础依赖、配置文件和可选GPU环境。
- `check_local_ai.py`：加载并检查SSDLite与RapidOCR本地模型。
- `install_local_ai.ps1`：安装OCR依赖、缓存本地模型并保存能力开关。
- `run_fixed_evaluation.py`：检查40场景图片清单，调用正式API并生成训练前基线结果。
- `run_dev.ps1`：在Windows启动开发服务器。
- `run_tests.ps1`：运行Ruff和pytest。

启动和测试脚本会依次寻找：当前已激活的Conda环境、默认位置的`ai-vision`环境、系统可识别的Python。正式执行前仍会检查是不是Python 3.11以及基础依赖是否齐全。

这些脚本只做开发和评测辅助，不修改系统PATH。`install_local_ai.ps1`和`check_local_ai.py`会下载或加载官方模型权重；`run_fixed_evaluation.py`只读取清单中由团队明确登记的本地图片，并将它们发送到用户指定的项目API地址。不要把未授权或含隐私的图片加入清单。
