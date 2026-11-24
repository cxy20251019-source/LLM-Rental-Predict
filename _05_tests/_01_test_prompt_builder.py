"""随机抽取一条带有近地铁标签的房源，打印 Zero-shot Prompt。"""
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

    # 仅筛选明确带有“近地铁”标签的房源。
    mask = data["标签"].astype(str).map(
        lambda tags: "近地铁" in {tag.strip() for tag in tags.split(",")}
    )
    candidates = data.loc[mask]
    if candidates.empty:
        raise ValueError("测试集中没有带近地铁标签的房源")

    # 固定随机种子，抽取一条符合条件的房源。
    row = candidates.sample(n=1, random_state=RANDOM_SEED).iloc[0]
    prompt = build_prompt(row["_city"], row, language="zh")
    print(prompt)


if __name__ == "__main__":
    preview_prompts()
