"""按不同房源条件抽样，打印 Zero-shot Prompt，便于人工检查。"""
import sys
from pathlib import Path

# 支持直接在 PyCharm 中运行当前文件。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from _01_config import CITIES, DATA_PATH, RANDOM_SEED
from _02_src._01_data_loader import load_data
from _02_src._03_prompt_builder import FACILITIES, build_prompt


def preview_prompts():
    if not DATA_PATH.is_file():
        raise FileNotFoundError("请先运行根目录的 _02_fix_data.py，生成楼层规范后的 Excel。")

    # 合并三个城市的测试集。
    data = pd.concat(
        [load_data(city, "test").assign(_city=city) for city in CITIES],
        ignore_index=True,
    )

    # 与 Prompt 模板使用相同的标签及设施判断规则。
    near_subway = data["标签"].astype(str).map(
        lambda tags: "近地铁" in {tag.strip() for tag in tags.split(",")}
    )
    data["_amenities"] = data["配套设置"].astype(str).map(
        lambda items: tuple(
            name for name in FACILITIES
            if name in {item.strip() for item in items.split(",")}
        )
    )
    data["_amenity_count"] = data["_amenities"].map(len)

    # 每种条件抽取一条真实房源，固定种子以便重复检查。
    selected = []

    def preview(label, candidates):
        if candidates.empty:
            print(f"\n【{label}】没有符合条件的样本。")
            return None

        row = candidates.sample(n=1, random_state=RANDOM_SEED).iloc[0]
        selected.append(row.name)
        print(f"\n{'=' * 60}")
        print(f"【{label}】城市：{row['_city']}")
        print("=" * 60)
        print(build_prompt(row["_city"], row, language="zh"))
        return row

    # 覆盖电梯有无与地铁信息已知、未知的四种组合。
    for elevator in ("有", "无"):
        for has_subway in (True, False):
            label = f"{elevator}电梯 / " + ("近地铁" if has_subway else "地铁暂不清楚")
            candidates = data.loc[
                (data["电梯"] == elevator) & (near_subway == has_subway)
            ]
            preview(label, candidates)

    # 额外抽取设施较少、较多且配置不同的房源，避免重复样本。
    remaining = data.drop(index=selected)
    if not remaining.empty:
        fewer = preview(
            "配套设施较少",
            remaining.loc[remaining["_amenity_count"] == remaining["_amenity_count"].min()],
        )
        remaining = data.drop(index=selected)
        if fewer is not None:
            remaining = remaining.loc[
                remaining["_amenities"].map(lambda items: items != fewer["_amenities"])
            ]
        preview(
            "配套设施较多（配置不同）",
            remaining.loc[remaining["_amenity_count"] == remaining["_amenity_count"].max()],
        )


if __name__ == "__main__":
    preview_prompts()
