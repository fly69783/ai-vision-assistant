# 如何接入一个真实AI能力

下面以目标检测为例，只说明结构，不指定最终模型。

## 第一步：先登记来源

在根目录`LICENSES.md`记录模型名称、版本、下载地址、许可证和比赛是否允许使用。

## 第二步：实现统一接口

在`core/providers/`新增文件，例如`detector_xxx.py`，继承`AnalysisProvider`：

```python
class DetectorProvider(AnalysisProvider):
    name = ProviderName.DETECTOR

    @property
    def configured(self) -> bool:
        return self.model is not None

    async def analyze(self, image, context) -> ProviderResult:
        # 1. 调用模型
        # 2. 把框、类别和置信度转成 Evidence
        # 3. 返回 ProviderResult
        ...
```

不要让适配器直接生成最终播报长文。适配器只负责返回结构化证据。

## 第三步：替换默认占位器

修改`build_default_registry`的装配代码，把对应`UnavailableProvider`换成真实适配器。模型加载应只发生一次，不要每个请求重新加载。

## 第四步：增加测试

- 单元测试：输入固定图片，检查输出字段和错误处理。
- 基线测试：记录成功率、误报、漏报和耗时。
- 异常测试：模型文件丢失、显存不足、超时和断网。

## 第五步：更新文档

只有真实代码和测试证据齐全后，才能把README中的状态从“未配置”改为“已接入”。
