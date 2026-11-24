# 结果目录

正式测试预测路径示例：`predictions/Shanghai/random/5_shot.xlsx`；zero-shot 使用 `predictions/Shanghai/0_shot.xlsx`。验证集结果另存于 `validation/` 下，避免覆盖测试结果。每个 Excel 对应一个城市、策略和 shot 数，包含样本 ID、真实租金、各 LLM 预测租金列。日志与评价指标独立保存。
