"""实验参数集中配置；模型及 API 参数尚待确定。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "三城数据_随机划分.xlsx"
RESULTS_DIR = ROOT / "results"

CITIES = ("北京", "上海", "西安")
CITY_DIRS = {"北京": "Beijing", "上海": "Shanghai", "西安": "Xian"}
SPLITS = {"train": "训练", "validation": "验证", "test": "测试"}
DATASET = "test"
SHOTS = (0, 1, 5, 10, 20)
STRATEGIES = ("random", "similarity")

# 以下为待确认的实验设置；空模型列表防止意外发起付费请求。
MODELS = ()
RANDOM_SEED = 42
CONCURRENCY = 5
MAX_RETRIES = 3
