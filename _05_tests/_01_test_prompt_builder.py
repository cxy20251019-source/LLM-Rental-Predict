"""随机抽取五条房源，打印 Zero-shot Prompt，便于人工检查。"""
import sys
from pathlib import Path

# 支持直接在 PyCharm 中运行当前文件。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from _01_config import CITIES, DATA_PATH, RANDOM_SEED
from _02_src._01_data_loader import load_data
from _02_src._03_prompt_builder import build_prompt


def preview_prompts():
    # 合并三城测试集，并保留每条房源所属城市。
    if not DATA_PATH.is_file():
        raise FileNotFoundError("请先运行根目录的 _02_fix_data.py，生成楼层规范后的 Excel。")

    data = pd.concat(
        [load_data(city, "test").assign(_city=city) for city in CITIES],
        ignore_index=True,
    )

    # 固定随机种子，方便重复检查同一批房源。
    samples = data.sample(n=5, random_state=RANDOM_SEED)

    for i, (_, row) in enumerate(samples.iterrows(), start=1):
        prompt = build_prompt(row["_city"], row, language="zh")
        print(f"\n{'=' * 60}")
        print(f"Prompt {i}/5 | 城市：{row['_city']}")
        print("=" * 60)
        print(prompt)


if __name__ == "__main__":
    preview_prompts()
