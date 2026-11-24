"""读取已划分的三城 Excel 数据，不清洗、不重新划分。"""
from pathlib import Path

import pandas as pd

from config import CITIES, CITY_DIRS, DATA_PATH, SPLITS

ID_COLUMN = "房源编号"
TARGET_COLUMN = "租金"


def load_data(city: str, split: str, path: str | Path = DATA_PATH) -> pd.DataFrame:
    """读取一个城市的指定数据集，保留原有全部字段和行顺序。"""
    # 同时支持 config.py 中的中文城市名和结果目录中的英文名。
    city = {name: cn for cn, name in CITY_DIRS.items()}.get(city, city)
    if city not in CITIES:
        raise ValueError(f"未知城市：{city}，可选城市：{CITIES}")
    if split not in SPLITS:
        raise ValueError(f"未知数据集：{split}，可选：{tuple(SPLITS)}")

    sheet_name = f"{city}_{SPLITS[split]}"
    df = pd.read_excel(path, sheet_name=sheet_name, dtype={ID_COLUMN: str})

    # 只校验，不删除、填充或修改数据。
    missing = {ID_COLUMN, TARGET_COLUMN} - set(df.columns)
    if missing:
        raise ValueError(f"{sheet_name} 缺少必要字段：{missing}")
    if df[ID_COLUMN].isna().any() or df[ID_COLUMN].duplicated().any():
        raise ValueError(f"{sheet_name} 存在空白或重复的房源编号")
    if not pd.api.types.is_numeric_dtype(df[TARGET_COLUMN]) or df[TARGET_COLUMN].isna().any():
        raise ValueError(f"{sheet_name} 存在非数值或空白租金")
    return df


def load_city_data(city: str, path: str | Path = DATA_PATH) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """依次返回同城训练集、验证集、测试集，并检查房源编号不重叠。"""
    train = load_data(city, "train", path)
    validation = load_data(city, "validation", path)
    test = load_data(city, "test", path)
    ids = [set(df[ID_COLUMN]) for df in (train, validation, test)]
    if ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2]:
        raise ValueError(f"{city} 的不同数据集存在重复房源编号")
    return train, validation, test


def split_data(df: pd.DataFrame, feature_columns: list[str]) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """按明确指定的特征列返回 X、真实租金 y、房源 ID，原表不变。"""
    # 不默认使用所有列，避免真实租金及直接关联字段进入 Prompt。
    excluded = {ID_COLUMN, TARGET_COLUMN, "押金_元", "服务费_元", "中介费_元", "页面网址", "租房图片链接"}
    if not feature_columns or excluded.intersection(feature_columns):
        raise ValueError("请明确指定非空的预测特征，不能包含 ID、租金、费用或链接字段")
    return df.loc[:, feature_columns].copy(), df[TARGET_COLUMN].copy(), df[ID_COLUMN].copy()
