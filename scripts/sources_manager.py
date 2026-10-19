"""种子源管理：用户维护的目标网站/频道列表 + 抓取。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from utils import DATA_DIR, log, load_json, save_json, safe_text


SOURCES_FILE = DATA_DIR / "sources.json"


@dataclass
class Source:
    name: str
    url: str
    category: str  # "ai" | "games" | "mixed"
    type: str  # "html" | "rss" | "api" | "manual"
    enabled: bool = True
    note: str = ""
    headers: dict[str, str] | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Source":
        return cls(
            name=d.get("name", ""),
            url=d.get("url", ""),
            category=d.get("category", "mixed"),
            type=d.get("type", "html"),
            enabled=d.get("enabled", True),
            note=d.get("note", ""),
            headers=d.get("headers"),
        )


def load_sources() -> list[Source]:
    data = load_json(SOURCES_FILE) or []
    return [Source.from_dict(s) for s in data if s.get("enabled", True)]


def fetch_source(src: Source, *, timeout: int = 15, max_bytes: int = 200_000) -> str | None:
    """抓取一个源的原始文本（截断防止超大页面爆内存）。"""
    if not src.enabled or not src.url:
        return None
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }
    if src.headers:
        headers.update(src.headers)
    try:
        resp = requests.get(src.url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        text = resp.text[:max_bytes]
        log(f"抓取成功 [{src.category}] {src.name} ({len(text)} 字符)")
        return text
    except Exception as e:
        log(f"抓取失败 [{src.category}] {src.name}: {safe_text(e, 150)}", level="ERROR")
        return None


def all_source_context(max_per_source: int = 4000, max_workers: int = 10) -> str:
    """把所有种子源抓回来拼成一段上下文，喂给 AI 做抽取。

    每个源截断到 max_per_source 字符，避免上下文爆炸。
    并发抓取（max_workers 线程），大幅加速。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    sources = load_sources()
    results: dict[str, str | None] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_src = {pool.submit(fetch_source, src): src for src in sources}
        for future in as_completed(future_to_src):
            src = future_to_src[future]
            try:
                results[src.name] = future.result()
            except Exception:
                results[src.name] = None

    # 按原始顺序拼上下文（保证可重现）
    parts: list[str] = []
    for src in sources:
        text = results.get(src.name)
        if not text:
            continue
        snippet = text[:max_per_source]
        parts.append(
            f"### 源: {src.name} (分类={src.category}, URL={src.url})\n\n{snippet}\n"
        )
    return "\n---\n".join(parts)
