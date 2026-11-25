"""使用模拟房源及预测值测试 Excel 写入，不请求任何 API。"""
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from openpyxl import load_workbook

from _01_config import MODELS
from _02_src._05_result_writer import ResultWriter, result_path


@contextmanager
def load_workbook_context(path):
    workbook = load_workbook(path, read_only=True)
    try:
        yield workbook.active
    finally:
        workbook.close()


class TestResultWriter(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = pd.DataFrame({"房源编号": ["001", "002", "003"], "租金": [2500, 3500, 4500]})
        self.model = next(model["name"] for model in MODELS if model["api_key_env"] == "DEEPSEEK_API_KEY")

    def writer(self, data=None, **kwargs):
        return ResultWriter("北京", self.data if data is None else data,
                            results_dir=self.root, **kwargs)

    def test_paths(self):
        self.assertEqual(result_path("北京", results_dir=self.root),
                         self.root / "predictions/Beijing/0_shot.xlsx")
        self.assertEqual(result_path("Shanghai", 5, "random", results_dir=self.root),
                         self.root / "predictions/Shanghai/random/5_shot.xlsx")
        self.assertEqual(result_path("西安", 10, "similarity", "validation", self.root),
                         self.root / "validation/Xian/similarity/10_shot.xlsx")
        with self.assertRaises(ValueError):
            result_path("北京", 5)

    def test_flat_test_layout(self):
        self.assertEqual(result_path("北京", results_dir=self.root, test_layout=True),
                         self.root / "Beijing/0_shot.xlsx")
        self.assertEqual(result_path("北京", 5, "random", results_dir=self.root, test_layout=True),
                         self.root / "Beijing/random_5_shot.xlsx")
        self.assertEqual(result_path("北京", 5, "similarity", results_dir=self.root, test_layout=True),
                         self.root / "Beijing/similarity_5_shot.xlsx")
        writer = self.writer(test_layout=True)
        self.assertEqual(writer.path, self.root / "Beijing/0_shot.xlsx")
        writer.write_prediction("001", self.model, 2600)
        resumed = self.writer(test_layout=True)
        self.assertEqual(resumed.pending_ids(self.model), ["002", "003"])

    def test_write_and_resume(self):
        writer = self.writer()
        self.assertEqual(writer.pending_ids(self.model), ["001", "002", "003"])
        writer.write_prediction("003", self.model, 4600)
        writer.write_prediction("001", self.model, 2600)
        # 重新读取文件，即使输入数据顺序改变，也按房源 ID 对齐。
        resumed = self.writer(self.data.iloc[::-1])
        self.assertEqual(resumed.pending_ids(self.model), ["002"])
        self.assertFalse(resumed.write_prediction("001", self.model, 2600))
        with self.assertRaises(ValueError):
            resumed.write_prediction("001", self.model, 9999)
        with load_workbook_context(writer.path) as sheet:
            rows = list(sheet.values)
        col = rows[0].index(self.model)
        self.assertEqual(len(rows[0]), 2 + len(MODELS))
        self.assertEqual(rows[1][0], "001")
        self.assertEqual(rows[1][col], 2600)
        self.assertIsNone(rows[2][col])
        self.assertEqual(rows[3][col], 4600)
        self.assertTrue(all(rows[1][i] is None for i in range(2, len(rows[0])) if i != col))

    def test_batch_and_invalid_data(self):
        writer = self.writer()
        writer.write_prediction("002", self.model, 3300, save=False)
        self.assertIn("002", self.writer().pending_ids(self.model))
        writer.save()
        self.assertNotIn("002", self.writer().pending_ids(self.model))
        for value in (None, 0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                writer.write_prediction("001", self.model, value)
        with self.assertRaises(ValueError):
            writer.write_prediction("missing", self.model, 100)
        with self.assertRaises(ValueError):
            writer.write_prediction("001", "missing-model", 100)
        with self.assertRaises(ValueError):
            self.writer(self.data.assign(租金=[1, 2, 3]))
        with self.assertRaises(ValueError):
            self.writer(self.data.iloc[:2])

    def test_atomic_save_failure(self):
        writer = self.writer()
        with patch("_02_src._05_result_writer.os.replace", side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                writer.write_prediction("001", self.model, 2600)
        self.assertIn("001", self.writer().pending_ids(self.model))
        writer.save()
        self.assertNotIn("001", self.writer().pending_ids(self.model))


if __name__ == "__main__":
    unittest.main(verbosity=2)
