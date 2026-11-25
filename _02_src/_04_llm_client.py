"""统一调用 OpenAI-compatible LLM 接口，并解析月租金。"""
import asyncio
import math
import os
import re

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, AsyncOpenAI

from _01_config import ROOT, LLM_TIMEOUT, MAX_RETRIES, RETRY_BASE_DELAY


def create_client(model_config: dict) -> AsyncOpenAI:
    """读取本地密钥，为指定模型创建可复用的异步客户端。"""
    load_dotenv(ROOT / ".env")
    api_key = os.getenv(model_config["api_key_env"], "").strip()
    base_url = os.getenv(model_config["base_url_env"], "").strip()
    if not api_key or not base_url:
        raise ValueError(f"模型 {model_config['name']} 的 API 密钥或 Base URL 未配置")

    # 禁用 SDK 自动重试，由 predict_rent_with_retry 统一控制重试次数。
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


async def predict_rent_with_retry(
    client: AsyncOpenAI, model_config: dict, prompt: str,
    *, max_retries: int = MAX_RETRIES,
) -> float:
    """对临时网络/API错误重试；输出格式错误及永久性错误直接抛出。"""
    if max_retries < 0:
        raise ValueError("重试次数不能为负数")
    for attempt in range(max_retries + 1):
        try:
            return await predict_rent(client, model_config, prompt)
        except (APIConnectionError, APIStatusError) as exc:
            retryable = isinstance(exc, APIConnectionError) or (
                isinstance(exc, APIStatusError)
                and (exc.status_code in (408, 429) or 500 <= exc.status_code < 600)
            )
            if not retryable or attempt == max_retries:
                raise
            delay = RETRY_BASE_DELAY * 2 ** attempt
            # 尊重服务器明确给出的重试间隔（秒）；忽略无效或非数字值。
            if isinstance(exc, APIStatusError):
                try:
                    retry_after = float(exc.response.headers.get("retry-after", "0"))
                    if math.isfinite(retry_after):
                        delay = max(delay, retry_after)
                except (TypeError, ValueError):
                    pass
            reason = f"HTTP {exc.status_code}" if isinstance(exc, APIStatusError) else type(exc).__name__
            print(f"API {reason}，{delay:g} 秒后重试（{attempt + 1}/{max_retries}）", flush=True)
            await asyncio.sleep(delay)
