# 测试

后续测试数据读取、样本选择、Prompt 泄露检查、输出解析、Excel 对齐与断点续跑。默认使用模拟 API，避免产生费用。

## DeepSeek 真实 API 联调（会产生费用）

`_01_data/test_data_50.csv` 来源于北京验证集，使用 Python random.Random(42) 随机不放回抽取 50 条，保留 Prompt 所需 12 个原始字段、房源编号和真实租金，楼层按项目规则规范。运行 `python _05_tests/_04_generate_test_results.py`，使用本地 `.env` 的 DeepSeek 配置，每条独立 Zero-shot 请求，首次最多 50 次请求，不自动重试。成功结果写入 `_05_tests/test_result/predictions/Beijing/0_shot.xlsx`，其他模型列空白。重复运行仅处理尚未成功的房源。真实租金仅用于结果表，不发送给模型。
