"""按论文 3.2.3 规范楼层字段，保留原始 Excel 及其他数据。"""
import re
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "data" / "三城数据_随机划分.xlsx"
OUTPUT_PATH = ROOT / "data" / "三城数据_楼层规范.xlsx"
FLOOR_CODES = {"地下室": 0, "低楼层": 1, "中楼层": 2, "高楼层": 3}


def normalize_floor(value: str) -> str:
    """统一为类别/总楼层，例如 3/18层 -> 低楼层/18层。"""
    match = re.fullmatch(r"(地下室|低楼层|中楼层|高楼层|-?\d+)/([1-9]\d*)层", str(value).strip())
    if match is None:
        raise ValueError(f"无法识别楼层：{value!r}")
    floor, total = match.groups()
    total = int(total)

    # 原本只有类别的记录无法反推具体楼层，保留已有分类。
    if floor in FLOOR_CODES:
        return f"{floor}/{total}层"

    current = int(floor)
    if current > total:
        raise ValueError(f"当前楼层超过总楼层：{value!r}")
    # 使用整数比较，避免 0.3 和 0.7 的浮点边界问题。
    if current <= 0:
        category = "地下室"
    elif 10 * current <= 3 * total:
        category = "低楼层"
    elif 10 * current < 7 * total:
        category = "中楼层"
    else:
        category = "高楼层"
    return f"{category}/{total}层"


def fix_data(source: str | Path = SOURCE_PATH, output: str | Path = OUTPUT_PATH) -> dict[str, int]:
    """仅修改九张工作表的楼层列，另存新文件，返回每张表的修改数。"""
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("输出路径不能与原始数据路径相同")
    workbook = load_workbook(source)
    changes = {}
    try:
        for sheet in workbook.worksheets:
            headers = [cell.value for cell in sheet[1]]
            if headers.count("楼层") != 1:
                raise ValueError(f"{sheet.title} 缺少唯一的楼层字段")
            column = headers.index("楼层") + 1
            count = 0
            for (cell,) in sheet.iter_rows(min_row=2, min_col=column, max_col=column):
                try:
                    normalized = normalize_floor(cell.value)
                except ValueError as exc:
                    raise ValueError(f"{sheet.title}!{cell.coordinate}: {exc}") from exc
                if cell.value != normalized:
                    cell.value = normalized
                    count += 1
            changes[sheet.title] = count
        output.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(output)
    finally:
        workbook.close()
    return changes


if __name__ == "__main__":
    changes = fix_data()
    for sheet, count in changes.items():
        print(f"{sheet}: 规范 {count} 条")
    print(f"合计规范 {sum(changes.values())} 条；输出文件：{OUTPUT_PATH}")
