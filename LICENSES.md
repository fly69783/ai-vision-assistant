# 第三方模型、数据和代码登记表

> 当前已接入本地目标检测、本地OCR和一个云端视觉API，尚未建立比赛固定数据集。每增加一个外部资源，都必须先在本表登记并核对本届比赛规则。

| 名称 | 类型 | 版本/日期 | 来源 | 用途 | 许可证/授权 | 是否可用于比赛 | 负责人 |
|---|---|---|---|---|---|---|---|
| FastAPI | 代码库 | 安装时记录 | https://github.com/fastapi/fastapi | Web API框架 | MIT | 待最终核对 | 技术主力 |
| OpenCV Python Headless | 代码库 | 4.13.0.92 | https://github.com/opencv/opencv-python | 图像读取与质量检查 | Apache-2.0 | 待最终核对 | 技术主力 |
| PyTorch / Torchvision | 代码库 | 2.13.0 / 0.28.0 | https://github.com/pytorch/vision | 本地目标检测与CUDA推理 | BSD-3-Clause等，以安装包许可证为准 | 待最终核对 | 技术主力 |
| SSDLite320 MobileNetV3 COCO权重 | 预训练模型 | COCO_V1 | https://docs.pytorch.org/vision/main/models/generated/torchvision.models.detection.ssdlite320_mobilenet_v3_large.html | 常见物品检测、位置框和置信度 | Torchvision权重条款及COCO原图授权需分别核对 | 未确认 | 技术主力 |
| RapidOCR | 代码库 | 3.9.1 | https://github.com/RapidAI/RapidOCR | OCR部署与结果解析 | 工程代码Apache-2.0；项目说明模型版权归百度 | 待核对模型授权后确认 | 技术主力 |
| PP-OCRv6 small模型 | 预训练模型 | RapidOCR 3.9.1内置 | https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/ | 中文和英文文字检测与识别 | 模型版权归百度，具体比赛使用范围待核对 | 未确认 | 技术主力 |
| ONNX Runtime | 代码库 | 1.27.0 | https://github.com/microsoft/onnxruntime | OCR CPU推理 | MIT | 待最终核对 | 技术主力 |
| 智谱GLM-4.5V | 云端模型API | 接入于2026-07-17 | https://docs.bigmodel.cn/cn/guide/models/vlm/glm-4.5v | 场景概述、文字读取回退、物品查找与视觉追问 | 智谱开放平台服务条款，待保存和核对 | 比赛使用尚待按本届规则确认 | 两人共同 |

## 登记要求

1. 记录准确名称、版本、下载地址或API文档地址。
2. 保存许可证原文或官方授权说明。
3. 数据集必须记录采集人、来源、授权和是否含个人信息。
4. 不清楚是否允许使用时，先标记“未确认”，不要进入最终参赛版本。
