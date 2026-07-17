# 训练前固定场景评测指南

## 先说结论

当前不要直接训练模型。项目已经有可运行的SSDLite、RapidOCR和GLM-4.5V，但还没有训练图片、边界框标注或真实准确率基线。正确顺序是：

1. 拍摄并登记40张固定场景图片。
2. 用当前三个模型跑完第一轮基线。
3. 记录漏检、误报、OCR错误、幻觉和耗时。
4. 只对反复失败且比赛必须解决的类别准备额外标注数据。
5. 从预训练模型微调，不从零训练大模型。

## 第一步：准备40张图片

清单已经写在[`test-cases.csv`](./test-cases.csv)，包括：

- 10个环境概述场景。
- 10个文字读取场景。
- 10个物品查找场景。
- 10个低光、过亮、模糊、遮挡等困难场景。

把图片放在本机以下目录：

```text
datasets/fixed-scenes/images/
```

文件名必须与清单一致，例如：

```text
SCENE-001.jpg
TEXT-001.jpg
FIND-001.jpg
HARD-001.jpg
```

`datasets/`已被Git忽略，不会自动上传。只使用团队自摄、获得授权或程序生成的图片，不拍摄可识别人脸、住址、电话号码、屏幕内容和个人文件。拍摄完成后，把清单中的“待拍摄后填写”改成真实来源与授权说明。

## 第二步：检查清单

在项目终端运行：

```powershell
conda activate ai-vision
cd /d D:\ai-vision-assistant
python scripts\run_fixed_evaluation.py --check-only
```

脚本会报告`ready`、`missing_input`、`missing_license`等数量，不会调用AI或产生费用。

## 第三步：运行真实基线

先在第一个终端启动项目：

```powershell
conda activate ai-vision
cd /d D:\ai-vision-assistant
powershell -ExecutionPolicy Bypass -File scripts\run_dev.ps1
```

再打开第二个终端运行：

```powershell
conda activate ai-vision
cd /d D:\ai-vision-assistant
python scripts\run_fixed_evaluation.py
```

结果保存到`output/fixed-evaluation-日期-时间.csv`。该目录也不会上传Git。脚本会自动检查预期状态、关键词和OCR文字；环境概述等主观结果仍需两名队员人工复核。

调试时可以先跑前3条：

```powershell
python scripts\run_fixed_evaluation.py --limit 3
```

## 什么时候才训练

同时满足以下条件再进入微调：

- 40场景基线已经完成，失败不是配置、拍摄质量或提示词造成的。
- 同一比赛关键类别出现稳定漏检，而视觉模型回退仍不能可靠补足。
- 团队能合法收集该类别的额外图片并标注边界框。
- 调试集、验证集和最终测试集能严格分开。

第一轮最值得观察的是当前COCO类别之外的`门`、`扶手`、`台阶/楼梯`和`盲道`。如果确实需要微调，每个自定义类别先以100张以上、不同距离/角度/光照的标注图片作为工程起点；这不是准确率保证。建议按70%训练、15%验证、15%内部测试划分，40张最终固定场景不要混入训练集。

## 训练对象怎么选

| 能力 | 当前建议 |
|---|---|
| 目标检测 | 基线证明自定义类别稳定失败后，再微调预训练轻量检测模型 |
| OCR | 暂不训练；先改善拍摄距离、反光、倾斜和文字排序 |
| GLM-4.5V | 不训练；继续使用API并通过提示词、结构化证据和失败约束优化 |
| 融合与播报 | 通过代码规则和固定场景对照实验优化，不需要训练神经网络 |

训练前必须为每张检测图片提供类别和边界框。[Torchvision官方自定义检测教程](https://docs.pytorch.org/tutorials/intermediate/torchvision_tutorial.html)也要求数据集返回`boxes`和`labels`，然后从预训练模型进行微调。
