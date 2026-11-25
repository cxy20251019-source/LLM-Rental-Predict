"""按城市、策略和 shots 保存预测 Excel，支持单写入者与断点续跑。"""
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment

from _01_config import CITY_DIRS, MODELS, RESULTS_DIR, SHOTS, STRATEGIES
from _02_src._01_data_loader import ID_COLUMN, TARGET_COLUMN

TRUE_RENT_COLUMN = "真实租金"
PROMPT_COLUMN = "提示词"


def result_path(city, shots=0, strategy=None, split="test", results_dir=RESULTS_DIR, *, test_layout=False):
    """同一个城市、数据集、策略和 shots 对应唯一结果文件。"""
    city = CITY_DIRS.get(city, city)
    if city not in CITY_DIRS.values():
        raise ValueError(f"未知城市：{city}")
    if split not in ("test", "validation"):
        raise ValueError("只支持测试集和验证集结果")
    if shots not in SHOTS:
        raise ValueError(f"不支持的 shots：{shots}")
    if test_layout and split != "test":
        raise ValueError("简化联调目录仅用于 test 数据集")
    folder = Path(results_dir) / city if test_layout else Path(results_dir) / ("predictions" if split == "test" else "validation") / city
    if shots == 0:
        if strategy is not None:
            raise ValueError("Zero-shot 不需要样本选择策略")
    else:
        if strategy not in STRATEGIES:
            raise ValueError("Few-shot 必须指定 random 或 similarity")
        if test_layout:
            return folder / f"{strategy}_{shots}_shot.xlsx"
        folder /= strategy
    return folder / f"{shots}_shot.xlsx"


def _positive_number(value):
    if isinstance(value, bool):
        raise ValueError("租金必须是有限正数")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("租金必须是有限正数") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError("租金必须是有限正数")
    return number


class ResultWriter:
    """一个结果文件只由一个实例负责写入；不在多个进程中并发保存。"""

    def __init__(self, city, data: pd.DataFrame, shots=0, strategy=None,
                 split="test", results_dir=RESULTS_DIR, *, test_layout=False, prompts=None):
        self.path = result_path(city, shots, strategy, split, results_dir, test_layout=test_layout)
        self.model_names = tuple(model["name"] for model in MODELS)
        base_headers = (ID_COLUMN, TRUE_RENT_COLUMN, *self.model_names)
        self.headers = (*base_headers, PROMPT_COLUMN) if prompts is not None else base_headers
        if not self.model_names or len(set(self.headers)) != len(self.headers):
            raise ValueError("模型列名为空、重复或与固定列冲突")

        # 先核对房源编号及真实租金，避免断点续跑时使用了另一批数据。
        expected = {}
        for raw_id, rent in data[[ID_COLUMN, TARGET_COLUMN]].itertuples(index=False, name=None):
            if pd.isna(raw_id) or not str(raw_id).strip():
                raise ValueError("房源编号不能为空")
            house_id = str(raw_id)
            if house_id in expected:
                raise ValueError(f"房源编号重复：{house_id}")
            expected[house_id] = _positive_number(rent)
        if not expected:
            raise ValueError("不能创建空结果表")

        if prompts is not None:
            if set(prompts) != set(expected):
                raise ValueError("提示词与房源编号集合不一致")
            for prompt in prompts.values():
                if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 32767:
                    raise ValueError("提示词必须是非空文本，且不得超过 Excel 单元格长度限制")

        self._dirty = False
        self._rows = {}
        self._columns = {name: i for i, name in enumerate(self.headers, start=1)}
        migrate_prompts = False
        if self.path.exists():
            self.workbook = load_workbook(self.path)
            self.sheet = self.workbook.active
            old_headers = tuple(cell.value for cell in self.sheet[1])
            migrate_prompts = prompts is not None and old_headers == base_headers
            if old_headers != self.headers and not migrate_prompts:
                raise ValueError("已有结果表的列名与当前模型配置不一致")
            for row in self.sheet.iter_rows(min_row=2):
                house_id, rent = row[0].value, row[1].value
                if house_id is None:
                    raise ValueError("已有结果表存在空房源编号")
                house_id = str(house_id)
                if house_id in self._rows or house_id not in expected:
                    raise ValueError(f"已有结果表房源编号不匹配：{house_id}")
                if _positive_number(rent) != expected[house_id]:
                    raise ValueError(f"真实租金不匹配：{house_id}")
                for cell in row[2:len(base_headers)]:
                    if cell.value is not None:
                        _positive_number(cell.value)
                if prompts is not None and not migrate_prompts:
                    if row[len(base_headers)].value != prompts[house_id]:
                        raise ValueError(f"已有提示词与当前模板不一致：{house_id}，请使用新结果文件")
                self._rows[house_id] = row[0].row
            if set(self._rows) != set(expected):
                raise ValueError("已有结果表与当前数据的房源集合不一致")
        else:
            self.workbook = Workbook()
            self.sheet = self.workbook.active
            self.sheet.title = "predictions"
            self.sheet.append(self.headers)
            for house_id, rent in expected.items():
                self.sheet.append([house_id, rent])
                row_number = self.sheet.max_row
                self.sheet.cell(row_number, 1).data_type = "s"
                self.sheet.cell(row_number, 1).number_format = "@"
                self._rows[house_id] = row_number
            self.sheet.freeze_panes = "C2"
            self.sheet.column_dimensions["A"].width = 24
            self.sheet.column_dimensions["B"].width = 14
            for cell in self.sheet[1][2:]:
                self.sheet.column_dimensions[cell.column_letter].width = max(16, len(cell.value) + 2)
            self._dirty = True

        if prompts is not None and (migrate_prompts or self._dirty):
            # 提示词追加在最后一列，保持已有预测列的位置不变。
            column = self._columns[PROMPT_COLUMN]
            header = self.sheet.cell(1, column, PROMPT_COLUMN)
            self.sheet.column_dimensions[header.column_letter].width = 65
            for house_id, row in self._rows.items():
                cell = self.sheet.cell(row, column, prompts[house_id])
                cell.data_type = "s"
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                self.sheet.row_dimensions[row].height = 100
                if migrate_prompts and any(
                    self.sheet.cell(row, i).value is not None for i in range(3, len(base_headers) + 1)
                ):
                    cell.comment = Comment("旧预测对应的提示词由当前模板重新生成，未核验与原请求完全一致。", "ResultWriter")
            self._dirty = True
        self.save()

    def pending_ids(self, model_name):
        """返回指定模型尚未写入预测值的房源编号。"""
        if model_name not in self.model_names:
            raise ValueError(f"未知模型：{model_name}")
        column = self._columns[model_name]
        return [house_id for house_id, row in self._rows.items()
                if self.sheet.cell(row, column).value is None]

    def write_prediction(self, house_id, model_name, rent, save=True):
        """按 ID 写入有效预测；已有结果不允许被不同数值覆盖。"""
        house_id = str(house_id)
        if house_id not in self._rows:
            raise ValueError(f"未知房源编号：{house_id}")
        if model_name not in self.model_names:
            raise ValueError(f"未知模型：{model_name}")
        rent = _positive_number(rent)
        cell = self.sheet.cell(self._rows[house_id], self._columns[model_name])
        if cell.value is not None:
            if float(cell.value) != rent:
                raise ValueError(f"已有预测，不允许覆盖：{house_id} / {model_name}")
            if save:
                self.save()
            return False
        cell.value = rent
        self._dirty = True
        if save:
            self.save()
        return True

    def save(self):
        """先写同目录临时文件，再原子替换，避免保存中断破坏旧结果。"""
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=self.path.parent, suffix=".xlsx", delete=False) as tmp:
            temp_path = Path(tmp.name)
        try:
            self.workbook.save(temp_path)
            os.replace(temp_path, self.path)
            self._dirty = False
        finally:
            temp_path.unlink(missing_ok=True)
