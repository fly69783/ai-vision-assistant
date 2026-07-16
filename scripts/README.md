# scripts

- `check_environment.py`：检查Python版本、基础依赖、配置文件和可选GPU环境。
- `run_dev.ps1`：在Windows启动开发服务器。
- `run_tests.ps1`：运行Ruff和pytest。

启动和测试脚本会依次寻找：当前已激活的Conda环境、默认位置的`ai-vision`环境、系统可识别的Python。正式执行前仍会检查是不是Python 3.11以及基础依赖是否齐全。

这些脚本只做开发辅助，不下载模型、不修改系统PATH，也不会读取或上传隐私图片。
