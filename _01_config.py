"""实验参数集中配置；模型已配置，正式推理参数尚待确定。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# 正式实验读取楼层规范后的数据；首次运行前执行 _02_fix_data.py。
DATA_PATH = ROOT / "_01_data" / "三城数据_楼层规范.xlsx"
RESULTS_DIR = ROOT / "_04_results"

CITIES = ("北京", "上海", "西安")
CITY_DIRS = {"北京": "Beijing", "上海": "Shanghai", "西安": "Xian"}
SPLITS = {"train": "训练", "validation": "验证", "test": "测试"}
DATASET = "test"
SHOTS = (0, 1, 5, 10, 20)
STRATEGIES = ("random", "similarity")

# 五个模型家族的官方 OpenAI-compatible API 配置。
# 每个模型可单独设置推理参数；暂时保留各厂商默认值，正式实验前统一确认。
# 配置本身不发送请求；本地 .env 中填写密钥和接口地址。
MODELS = (
    {
        "name": "GPT-5.6-Sol",
        "model": "gpt-5.6-sol",
        "api_key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "request_options": {},
    },
    {
        "name": "GLM-5.3-Flash",
        "model": "glm-5.3-flash",
        "api_key_env": "GLM_API_KEY",
        "base_url_env": "GLM_BASE_URL",
        "request_options": {},
    },
    {
        "name": "DeepSeek-V4.1-Flash-1017",
        "model": "deepseek-flash",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "request_options": {},
    },
    {
        "name": "Qwen3.8-Flash",
        "model": "qwen3.8-flash",
        "api_key_env": "QWEN_API_KEY",
        "base_url_env": "QWEN_BASE_URL",
        "request_options": {},
    },
    {
        "name": "Hy4-Flash",
        "model": "hy4-flash",
        "api_key_env": "HUNYUAN_API_KEY",
        "base_url_env": "HUNYUAN_BASE_URL",
        "request_options": {},
    },
)
LLM_TIMEOUT = 60.0  # 单次 API 请求超时（秒）
RANDOM_SEED = 42
CONCURRENCY = 5
MAX_RETRIES = 3

# Prompt 原始字段白名单；增减字段时同步修改 format_property 模板。
FEATURE_COLUMNS = (
    "标题", "房屋类型", "标签", "租赁方式", "面积", "楼层",
    "用电", "用水", "采暖", "朝向", "电梯", "配套设置",
)

# 正式实验统一使用中文；英文仅供后续对照实验按需启用。
PROMPT_LANGUAGE = "zh"
