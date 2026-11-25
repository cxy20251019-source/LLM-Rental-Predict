# 测试

默认离线测试使用模拟 API，不产生费用。

## DeepSeek 真实 API 联调（会产生费用）

`_01_data/test_data_50.csv` 包含 50 条独立生成的虚构房源，所有小区、编号、房源属性及租金均为人工构造的测试值，未使用原始 Excel 或真实房源。租金列仅为测试结果表占位标签，不能用作真实预测准确性评价。

运行 `python _05_tests/_04_generate_test_results.py`，使用本地 `.env` 的 DeepSeek 配置，每条独立 Zero-shot 请求，首次最多 50 次请求，不自动重试。成功结果写入 `_05_tests/test_result/Beijing/0_shot.xlsx`，其他模型列空白。重复运行仅处理尚未成功的房源。虚构租金仅用于结果表，不发送给模型。联调结果不得纳入正式实验。
