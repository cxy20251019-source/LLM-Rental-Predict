"""50 条完全虚构房源的 DeepSeek Zero-shot 联调（会产生 API 费用）。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from openai import APIError, APIStatusError

from _01_config import ROOT, MODELS, FEATURE_COLUMNS
from _02_src._03_prompt_builder import build_prompt
from _02_src._04_llm_client import create_client, predict_rent
from _02_src._05_result_writer import ResultWriter

CSV_PATH = ROOT / "_01_data" / "test_data_50.csv"
TEST_RESULTS_DIR = Path(__file__).resolve().parent / "test_result"


async def generate_test_results():
    """仅调用 DeepSeek，成功一条就写入 Excel，失败留空，下次可续跑。"""
    data = pd.read_csv(CSV_PATH, encoding="utf-8-sig", dtype={"房源编号": str}, keep_default_na=False)
    if len(data) != 50 or not data["房源编号"].str.fullmatch(r"SYNTHETIC-\d{3}").all():
        raise ValueError("联调仅允许 50 条虚构房源（SYNTHETIC 编号）")
    if not data["标题"].str.contains("虚构测试小区", regex=False).all():
        raise ValueError("联调 CSV 必须使用虚构小区")

    model = next(m for m in MODELS if m["api_key_env"] == "DEEPSEEK_API_KEY")
    name = model["name"]

    # 提前构建所有提示词，确保格式正确再发送付费请求。
    prompts = {
        row["房源编号"]: build_prompt("北京", row.loc[list(FEATURE_COLUMNS)], language="zh")
        for _, row in data.iterrows()
    }
    writer = ResultWriter("北京", data, shots=0, results_dir=TEST_RESULTS_DIR, test_layout=True)
    pending = writer.pending_ids(name)
    print(f"DeepSeek: 已保存 {len(data) - len(pending)}/50，待预测 {len(pending)} 条")
    print(f"结果文件：{writer.path}")

    try:
        if not pending:
            return writer.path

        # 每条独立请求；先采用串行联调，不自动重试，避免额外费用。
        async with create_client(model) as client:
            for index, house_id in enumerate(pending, 1):
                try:
                    rent = await predict_rent(client, model, prompts[house_id])
                except APIStatusError as exc:
                    print(f"[{index}/{len(pending)}] {house_id} 请求失败：HTTP {exc.status_code}")
                    # 配置、权限、余额或限流问题：停止，修复后可续跑。
                    if exc.status_code in (400, 401, 402, 403, 404, 429):
                        break
                    continue
                except APIError as exc:
                    print(f"[{index}/{len(pending)}] {house_id} 请求失败：{type(exc).__name__}；停止以便排查")
                    break
                except ValueError as exc:
                    print(f"[{index}/{len(pending)}] {house_id} 输出无效：{exc}")
                    continue

                writer.write_prediction(house_id, name, rent)
                print(f"[{index}/{len(pending)}] {house_id} 预测租金：{rent:g} 元/月")
    finally:
        print(f"本次结束：已保存 {50 - len(writer.pending_ids(name))}/50 条，未完成保持空白。")
        writer.workbook.close()

    return writer.path


if __name__ == "__main__":
    asyncio.run(generate_test_results())
