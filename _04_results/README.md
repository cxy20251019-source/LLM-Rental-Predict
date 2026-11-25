# 结果目录

正式测试预测路径示例：`predictions/Shanghai/random/5_shot.xlsx`；zero-shot 使用 `predictions/Shanghai/0_shot.xlsx`。验证集结果另存于 `validation/` 下，避免覆盖测试结果。每个 Excel 对应一个城市、策略和 shot 数，包含样本 ID、真实租金、各 LLM 预测租金列。日志与评价指标独立保存。

## 保存与续跑

`ResultWriter(city, data, shots=0, strategy=None, split="test")` 创建或读取结果表。验证集与测试集独立；同一条件下只创建一张 Excel，列为 `房源编号`、`真实租金` 和配置中的全部模型名称。

- `pending_ids(model_name)` 返回当前未写入预测的房源编号。
- `write_prediction(house_id, model_name, rent)` 按编号保存一条有效预测，默认立即保存。
- 批量运行可使用 `save=False` 暂存，再定期调用 `save()`；未保存的内存结果无法在重启后恢复。
- 一个文件只允许一个写入者；打开 Excel 时可能因文件锁无法保存。失败预测保持空白，已有不同预测值不允许覆盖。
- 已有文件会核对列名、房源集合与真实租金；修改模型列表、Prompt、参数或语言时不要混用旧结果。本阶段只使用中文，未来语言对照需要单独的结果目录。
