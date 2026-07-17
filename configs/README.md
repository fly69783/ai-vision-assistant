# configs

这里放**可以公开提交**的非敏感配置，例如图片大小限制、画面质量阈值和融合权重。

- 默认配置：`default.yaml`
- 本地密钥：放在系统环境变量或未提交的`.env`，不要放在本目录。
- 修改阈值后：必须重新运行固定测试集，并在项目计划中记录原因。

当前上传边界：`max_upload_mb`限制压缩文件大小，`max_image_pixels`限制解码后的总像素数，两者用途不同。允许的MIME类型还必须通过真实文件头和OpenCV解码检查；只修改文件扩展名不会绕过校验。

环境变量使用`AI_VISION_`前缀，例如`AI_VISION_MAX_UPLOAD_MB=8`和`AI_VISION_MAX_IMAGE_PIXELS=25000000`。密钥只能写进未提交的`.env`或部署平台密钥管理，不得写进`default.yaml`。

当前AI能力配置：

| 环境变量 | 作用 | 示例 |
|---|---|---|
| `AI_VISION_VISION_ENABLED` | 是否启用视觉Provider | `true` |
| `AI_VISION_ZHIPU_API_KEY` | 智谱API密钥 | 只填在本机，不要提交 |
| `AI_VISION_VISION_MODEL` | 覆盖默认视觉模型 | `glm-4.5v` |
| `AI_VISION_VISION_MAX_TOKENS` | 限制单次输出长度 | `512` |
| `AI_VISION_DETECTOR_ENABLED` | 启用本地SSDLite目标检测 | `true` |
| `AI_VISION_DETECTOR_MIN_CONFIDENCE` | 目标检测最低置信度 | `0.45` |
| `AI_VISION_DETECTOR_MAX_RESULTS` | 每张图最多保留的目标数 | `10` |
| `AI_VISION_OCR_ENABLED` | 启用本地RapidOCR | `true` |
| `AI_VISION_OCR_MIN_CONFIDENCE` | OCR最低置信度 | `0.55` |
| `AI_VISION_OCR_MAX_LINES` | 每张图最多保留的文字行数 | `12` |

修改系统级环境变量后要新开终端。测试夹具会禁用三项真实Provider，不会加载模型、读取真实密钥或调用计费接口。
