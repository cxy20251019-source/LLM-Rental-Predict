"""离线测试 LLM 数值解析与独立请求，不连接真实 API。"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _01_config import MODELS
from _02_src._04_llm_client import parse_rent, predict_rent


class TestLLMClient(unittest.IsolatedAsyncioTestCase):
    def test_parse_valid_rent(self):
        self.assertEqual(parse_rent(" 3500\n"), 3500.0)
        self.assertEqual(parse_rent("3500.5"), 3500.5)

    def test_parse_invalid_rent(self):
        for value in (None, "", "3500元", "约3500", "3500, 4000", "-1", "0", "NaN"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_rent(value)

    async def test_independent_request(self):
        create = AsyncMock(return_value=SimpleNamespace(choices=[
            SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content="3500"))
        ]))
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        model = {"model": "mock-model", "request_options": {}}
        self.assertEqual(await predict_rent(client, model, "测试提示词"), 3500.0)
        create.assert_awaited_once_with(
            model="mock-model",
            messages=[{"role": "user", "content": "测试提示词"}],
        )

    async def test_all_configured_models(self):
        # 五种配置通过同一客户端函数；不访问网络。
        self.assertEqual(len(MODELS), 5)
        self.assertEqual(len({model["name"] for model in MODELS}), 5)
        for model in MODELS:
            with self.subTest(model=model["name"]):
                create = AsyncMock(return_value=SimpleNamespace(choices=[
                    SimpleNamespace(finish_reason="stop", message=SimpleNamespace(
                        content="3500", reasoning_content="内部推理文本"
                    ))
                ]))
                client = SimpleNamespace(chat=SimpleNamespace(
                    completions=SimpleNamespace(create=create)
                ))
                self.assertEqual(await predict_rent(client, model, "测试提示词"), 3500.0)
                create.assert_awaited_once_with(
                    model=model["model"],
                    messages=[{"role": "user", "content": "测试提示词"}],
                    **model["request_options"],
                )

    async def test_truncated_response(self):
        create = AsyncMock(return_value=SimpleNamespace(choices=[
            SimpleNamespace(finish_reason="length", message=SimpleNamespace(content="35"))
        ]))
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with self.assertRaises(ValueError):
            await predict_rent(client, {"model": "mock-model"}, "测试提示词")


if __name__ == "__main__":
    unittest.main()
