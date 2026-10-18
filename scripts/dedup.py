"""去重、合并、状态更新。

核心思路：
- 每个活动有稳定 ID（基于标题+source_url 哈希）
- 新抓到的和已有数据按 ID 合并
- 已有字段优先保留（避免 AI 每天抽出来的描述来回变）
- 起止日期一旦确定不轻易改
- 每天根据今天日期刷新 status
"""
from __future__ import annotations

from datetime import date
from typing import Any

from utils import date_to_str, log, make_id, parse_date, status_of


def normalize_activity(raw: dict, category: str) -> dict | None:
    """把 AI 抽出来的原始 dict 规范成统一 schema。"""
    if not raw or not isinstance(raw, dict):
        return None
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    source_url = (raw.get("source_url") or raw.get("url") or "").strip()
    claim_url = (raw.get("claim_url") or source_url).strip()
    start = parse_date(raw.get("start_date"))
    end = parse_date(raw.get("end_date"))
    # 容错：end 早于 start 时交换
    if start and end and end < start:
        start, end = end, start

    aid = raw.get("id") or make_id(title, source_url)
    return {
        "id": aid,
        "title": title,
        "category": category,
        "source_url": source_url,
        "claim_url": claim_url,
        "start_date": date_to_str(start),
        "end_date": date_to_str(end),
        "value": (raw.get("value") or "").strip(),
        "requirements": raw.get("requirements") or [],
        "description": (raw.get("description") or "").strip(),
        "tags": raw.get("tags") or [],
        "discovered_at": (raw.get("discovered_at") or "").strip(),
        "last_seen": "",  # 由 merge 填
        "status": "active",  # 由 refresh_status 填
    }


def merge(old_list: list[dict], new_list: list[dict], today: date) -> list[dict]:
    """合并旧活动和新抓到的活动。

    规则：
    - ID 相同视为同一活动
    - 已有字段（description/value/requirements/tags）若新值为空则保留旧值
    - 起止日期：旧值优先（一旦确定不轻易改），新值仅当旧值为空时采用
    - last_seen 更新为今天
    - status 按日期重算
    """
    by_id = {a["id"]: a for a in old_list}
    for new in new_list:
        nid = new["id"]
        if nid in by_id:
            old = by_id[nid]
            # 字段补全：旧值空时才用新值
            for k in ("description", "value", "source_url", "claim_url", "title"):
                if not old.get(k) and new.get(k):
                    old[k] = new[k]
            for k in ("requirements", "tags"):
                if not old.get(k) and new.get(k):
                    old[k] = new[k]
            # 日期：旧值优先
            for k in ("start_date", "end_date"):
                if not old.get(k) and new.get(k):
                    old[k] = new[k]
        else:
            by_id[nid] = new
        by_id[nid]["last_seen"] = today.isoformat()

    result = list(by_id.values())
    refresh_status(result, today)
    # 排序：active 优先，然后按 end_date 升序
    result.sort(
        key=lambda a: (
            0 if a["status"] == "active" else 1 if a["status"] == "upcoming" else 2,
            a.get("end_date") or "9999-99-99",
        )
    )
    return result


def refresh_status(activities: list[dict], today: date) -> None:
    for a in activities:
        a["status"] = status_of(parse_date(a.get("start_date")), parse_date(a.get("end_date")), today)


def dedupe_within(new_list: list[dict]) -> list[dict]:
    """同一批新抓到的内部去重（按 ID 保留第一个）。"""
    seen = set()
    out = []
    for a in new_list:
        if a["id"] in seen:
            continue
        seen.add(a["id"])
        out.append(a)
    return out
