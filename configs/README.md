# configs

这里放**可以公开提交**的非敏感配置，例如图片大小限制、画面质量阈值和融合权重。

- 默认配置：`default.yaml`
- 本地密钥：放在`.env`，不要放在本目录。
- 修改阈值后：必须重新运行固定测试集，并在项目计划中记录原因。

当前上传边界：`max_upload_mb`限制压缩文件大小，`max_image_pixels`限制解码后的总像素数，两者用途不同。允许的MIME类型还必须通过真实文件头和OpenCV解码检查；只修改文件扩展名不会绕过校验。

环境变量使用`AI_VISION_`前缀，例如`AI_VISION_MAX_UPLOAD_MB=8`和`AI_VISION_MAX_IMAGE_PIXELS=25000000`。密钥只能写进未提交的`.env`或部署平台密钥管理，不得写进`default.yaml`。
