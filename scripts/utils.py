"""通用工具函数：时间处理、ID 生成、JSON 读写、日志。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
    BJ_TZ = ZoneInfo("Asia/Shanghai")
except Exception:  # 兜底（Windows 旧版本）
    import pytz
    BJ_TZ = pytz.timezone("Asia/Shanghai")


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"
DOCS_DATA_DIR = DOCS_DIR / "data"


def log(msg: str, *, level: str = "INFO") -> None:
    """带时间戳的日志，直接打到 stdout，Action 里能直接看到。"""
    ts = now_bj().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)
    if level == "ERROR":
        # 不 raise，让上层决定是否终止
        pass


def now_bj() -> datetime:
    """当前北京时间（带时区）。"""
    return datetime.now(BJ_TZ)


def today_bj() -> date:
    """当前北京时间日期。"""
    return now_bj().date()


def parse_date(s: str | None) -> date | None:
    """宽松解析日期字符串，支持 YYYY-MM-DD / YYYY/MM/DD / YYYY年MM月DD日。"""
    if not s:
        return None
    s = s.strip()
    patterns = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%Y年%m月%d日", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
    ]
    for p in patterns:
        try:
            return datetime.strptime(s, p).date()
        except ValueError:
            continue
    m = re.search(r"(\d{4})\D(\d{1,2})\D(\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def date_to_str(d: date | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


def make_id(*parts: str) -> str:
    """根据若干字段生成稳定短 ID（用于去重）。"""
    raw = "|".join(str(p) for p in parts if p).lower()
    h = hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]
    # 保留可读前缀
    prefix = re.sub(r"[^a-z0-9]+", "-", str(parts[0] or "item").lower())[:30].strip("-")
    return f"{prefix}-{h}"


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_json(path: Path, data: Any, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=False),
        encoding="utf-8",
    )


def is_long_term(a: dict, today: date | None = None, threshold_days: int = 90) -> bool:
    """判断是否长期免费活动。

    判定标准：无 end_date（永久免费）或 end_date 距今超过 threshold_days 天（默认 90 天 ≈ 3 个月）。
    长期活动归到「长期免费」分区，不显示在 SVG 当月时间轴里。
    """
    today = today or today_bj()
    ed = a.get("end_date")
    if not ed:
        return True
    end = parse_date(ed)
    if end is None:
        return True
    return (end - today).days > threshold_days


def status_of(start: date | None, end: date | None, today: date | None = None) -> str:
    """根据起止日期计算活动状态。"""
    today = today or today_bj()
    if end and today > end:
        return "ended"
    if start and today < start:
        return "upcoming"
    return "active"


def env(key: str, default: str | None = None, required: bool = False) -> str:
    v = os.environ.get(key, default)
    if required and not v:
        log(f"环境变量 {key} 未设置，无法继续", level="ERROR")
        sys.exit(1)
    return v or ""


def safe_text(s: Any, max_len: int = 500) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s
