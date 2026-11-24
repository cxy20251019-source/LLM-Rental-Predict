"""按论文 4.1–4.3 构建英文提示词，支持 zero-shot 和 few-shot。"""
import re
from collections.abc import Iterable, Mapping

from _01_config import CITY_DIRS, FEATURE_COLUMNS

DIRECTIONS = {
    "东": "east", "南": "south", "西": "west", "北": "north",
    "东南": "southeast", "东北": "northeast", "西南": "southwest", "西北": "northwest",
}
FACILITIES = {
    "洗衣机": "washing machine", "空调": "air conditioner", "衣柜": "wardrobe",
    "电视": "TV", "冰箱": "refrigerator", "热水器": "water heater",
    "床": "bed", "天然气": "natural gas",
}
FLOORS = {"地下室": "basement", "低楼层": "low floor", "中楼层": "middle floor", "高楼层": "high floor"}


def format_property(row: Mapping) -> str:
    """只读取白名单字段，将一条房源转换为英文描述（不含租金）。"""
    data = {key: str(row[key]) for key in FEATURE_COLUMNS}
    # 从标题提取小区；保留中文专名，缺失时不猜测。
    match = re.search(r"·\s*(.+?)\s+\d+(?:室|居室)", data["标题"])
    community = match.group(1) if match else "not specified"
    area = re.fullmatch(r"(\d+(?:\.\d+)?)\s*㎡", data["面积"])
    floor = re.fullmatch(r"(地下室|低楼层|中楼层|高楼层)/([1-9]\d*)层", data["楼层"])
    if not area or not floor:
        raise ValueError("面积或楼层格式不正确，请先运行 _02_fix_data.py")

    layout = re.fullmatch(r"(\d+)室(\d+)厅(\d+)卫", data["房屋类型"])
    shared_layout = re.fullmatch(r"(\d+)居室", data["房屋类型"])
    if layout:
        bedrooms, livingrooms, bathrooms = layout.groups()
        layout_text = f"{bedrooms} bedroom(s), {livingrooms} living room(s), and {bathrooms} bathroom(s)"
    elif shared_layout:
        layout_text = f"{shared_layout.group(1)} bedrooms in the dwelling; living room and bathroom counts not specified"
    else:
        raise ValueError(f"未知户型：{data['房屋类型']}")

    tags = {tag.strip() for tag in data["标签"].split(",")}
    amenities = {item.strip() for item in data["配套设置"].split(",")}
    listed = [english for chinese, english in FACILITIES.items() if chinese in amenities]
    rental_type = {"整租": "entire-unit rental", "合租": "shared rental"}[data["租赁方式"]]
    heating = {"集中供暖": "central heating", "自采暖": "individual heating"}[data["采暖"]]
    electricity = {"民电": "residential electricity"}[data["用电"]]
    orientation = ", ".join(DIRECTIONS[item] for item in data["朝向"].split())
    elevator = {"有": "has an elevator", "无": "has no elevator"}[data["电梯"]]
    decoration = "well-decorated" if "精装" in tags else "not specified"
    subway = "near a subway station" if "近地铁" in tags else "not specified"
    balcony = "private balcony indicated" if "独立阳台" in tags else "not specified"

    return (
        f"The rental property is located in {community}. "
        f"The listed area is {area.group(1)} square meters. "
        f"It is on a {FLOORS[floor.group(1)]} of a {floor.group(2)}-floor building. "
        f"The rental type is {rental_type}, with a layout of {layout_text}. "
        f"Decoration: {decoration}. It has {electricity} and {heating}. "
        f"The orientation is {orientation}, and the building {elevator}. "
        f"Subway proximity: {subway}. Balcony: {balcony}. "
        f"Listed amenities: {', '.join(listed) if listed else 'none of the tracked amenities listed'}."
    )


def build_prompt(city: str, property_data: Mapping, examples: Iterable[Mapping] | None = None) -> str:
    """构建完整提示词；examples=None 为 zero-shot，否则为 few-shot。"""
    city_name = CITY_DIRS.get(city, city)
    if city_name not in CITY_DIRS.values():
        raise ValueError(f"未知城市：{city}")
    parts = [
        f"Predict the monthly rent in {city_name}, China, in CNY, based on the property attributes. "
        "Return only one numerical rent value, without units or explanations."
    ]
    if examples is not None:
        for i, example in enumerate(examples, start=1):
            parts.append(f"Example {i}: {format_property(example)} True monthly rent: {example['租金']} CNY.")
    parts.append(f"Property to predict: {format_property(property_data)}")
    return "\n\n".join(parts)
