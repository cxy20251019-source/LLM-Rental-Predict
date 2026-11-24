"""统一调用 OpenAI-compatible LLM 接口，并解析月租金。"""
import math
import os
import re

from dotenv import load_dotenv
from openai import AsyncOpenAI

from _01_config import ROOT, LLM_TIMEOUT


def create_client(model_config: dict) -> AsyncOpenAI:
    """读取本地密钥，为指定模型创建可复用的异步客户端。"""
    load_dotenv(ROOT / ".env")
    api_key = os.getenv(model_config["api_key_env"], "").strip()
    base_url = os.getenv(model_config["base_url_env"], "").strip()
    if not api_key or not base_url:
        raise ValueError(f"模型 {model_config['name']} 的 API 密钥或 Base URL 未配置")

    # 禁用 SDK 自动重试，后续统一在实验流程中控制重试次数。
    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=LLM_TIMEOUT,
        max_retries=0,
    )


def parse_rent(response: str | None) -> float:
    """只接受正的普通数值，不将单位、解释或失败响应当作预测值。"""
    if response is None:
        raise ValueError("模型未返回文本")
    value = response.strip()
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError("模型输出不符合纯数字格式")
    rent = float(value)
    if not math.isfinite(rent) or rent <= 0:
        raise ValueError("预测租金必须是有限正数")
    return rent


async def predict_rent(client: AsyncOpenAI, model_config: dict, prompt: str) -> float:
    """一条 Prompt 对应一次独立请求，不携带之前的对话历史。"""
    response = await client.chat.completions.create(
        model=model_config["model"],
        messages=[{"role": "user", "content": prompt}],
        **model_config.get("request_options", {}),
    )
    if not response.choices:
        raise ValueError("模型未返回候选结果")
    choice = response.choices[0]
    if choice.finish_reason in ("length", "content_filter"):
        raise ValueError("模型输出未完整生成")
    return parse_rent(choice.message.content)
