"""不依赖 AI 的直接收集器。

用各平台官方 API 直接拿结构化数据，不需要 AI 中转站。

数据源：
- Epic Games GraphQL API → 游戏类免费游戏促销
- Steam Store API → 游戏类免费周末/特惠
- GitHub Search API → AI 类免费资源仓库
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

from utils import log, now_bj, safe_text


BJ_TZ = timezone(timedelta(hours=8))

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,en;q=0.7,en-US;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# ============================================================
# Epic Games GraphQL API
# ============================================================

EPIC_GRAPHQL_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"


def collect_epic_free_games() -> list[dict]:
    """从 Epic Games GraphQL API 获取免费游戏促销信息。

    Epic 的 API 直接返回 JSON，包含当前免费和即将免费的游戏。
    """
    activities: list[dict] = []
    try:
        resp = requests.get(EPIC_GRAPHQL_URL, params={"locale": "zh-CN"}, headers=BROWSER_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
        log(f"Epic API: 获取 {len(elements)} 个游戏")

        for e in elements:
            title = e.get("title", "")
            if not title:
                continue

            promos = e.get("promotions")
            if not promos:
                continue

            # 当前促销
            current_offers = promos.get("promotionalOffers", [])
            # 即将促销
            upcoming_offers = promos.get("upcomingPromotionalOffers", [])

            all_offers = []
            for offer_group in current_offers:
                all_offers.extend(offer_group.get("promotionalOffers", []))
            for offer_group in upcoming_offers:
                all_offers.extend(offer_group.get("promotionalOffers", []))

            for offer in all_offers:
                start = offer.get("startDate", "")
                end = offer.get("endDate", "")
                # 解析日期 (格式: 2026-10-19T16:00:00.000Z)
                start_date = start[:10] if start else ""
                end_date = end[:10] if end else ""

                # 构建 URL
                slug = e.get("catalogNs", {}).get("mappings", [{}])[0].get("pageSlug", "") if e.get("catalogNs") else ""
                ns = e.get("catalogNs", {}).get("ns", "") if e.get("catalogNs") else ""
                if slug and ns:
                    url = f"https://store.epicgames.com/zh-CN/p/{slug}"
                else:
                    url = "https://store.epicgames.com/zh-CN/free-games"

                # 判断是否免费（discountSetting 或 price 等于 0）
                is_free = True  # 在 freeGamesPromotions 端点里的都是免费促销

                status = "active"
                if start_date and end_date:
                    today = datetime.now(BJ_TZ).strftime("%Y-%m-%d")
                    if today > end_date:
                        status = "expired"
                    elif today < start_date:
                        status = "upcoming"

                activities.append({
                    "title": f"Epic 免费游戏: {title}",
                    "url": url,
                    "description": f"Epic Games Store 限时免费 | {start_date} ~ {end_date}",
                    "start_date": start_date or datetime.now(BJ_TZ).strftime("%Y-%m-%d"),
                    "end_date": end_date or (datetime.now(BJ_TZ) + timedelta(days=7)).strftime("%Y-%m-%d"),
                    "category": "games",
                    "source": "epic_graphql",
                    "status": status,
                    "discovered_at": now_bj().isoformat(),
                })
                break  # 每个游戏只取一个促销

    except Exception as e:
        log(f"Epic API 失败: {safe_text(e, 100)}", level="ERROR")

    log(f"Epic: 收集到 {len(activities)} 条免费游戏")
    return activities


# ============================================================
# Steam Store API
# ============================================================

STEAM_API_URL = "https://store.steampowered.com/api/featuredcategories"


def collect_steam_free_weekend() -> list[dict]:
    """从 Steam Store API 获取免费周末信息。

    Steam 的 featured categories API 返回特色分类，包含免费周末。
    """
    activities: list[dict] = []
    try:
        resp = requests.get(STEAM_API_URL, params={"l": "schinese"}, headers=BROWSER_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # 查找免费周末
        for cat_id, cat in data.items():
            if not isinstance(cat, dict):
                continue
            name = cat.get("name", "")
            items = cat.get("items", [])

            for item in items:
                item_name = item.get("name", "")
                # 免费周末
                if "免费" in item_name or "free" in item_name.lower():
                    app_id = item.get("id", "")
                    url = f"https://store.steampowered.com/app/{app_id}" if app_id else ""
                    activities.append({
                        "title": f"Steam 免费周末: {item_name}",
                        "url": url,
                        "description": f"Steam Store | 分类: {name}",
                        "start_date": datetime.now(BJ_TZ).strftime("%Y-%m-%d"),
                        "end_date": (datetime.now(BJ_TZ) + timedelta(days=3)).strftime("%Y-%m-%d"),
                        "category": "games",
                        "source": "steam_api",
                        "status": "active",
                        "discovered_at": now_bj().isoformat(),
                    })

        # 也检查 specials 里折扣为 100% 的（完全免费）
        specials = data.get("specials", {}).get("items", [])
        for item in specials:
            discount = item.get("discount_pct", 0)
            if discount >= 100:
                item_name = item.get("name", "")
                app_id = item.get("id", "")
                url = f"https://store.steampowered.com/app/{app_id}" if app_id else ""
                activities.append({
                    "title": f"Steam 限免: {item_name}",
                    "url": url,
                    "description": f"Steam Store | 100% 折扣 | 原价: {item.get('original_price', 0)//100}元",
                    "start_date": datetime.now(BJ_TZ).strftime("%Y-%m-%d"),
                    "end_date": (datetime.now(BJ_TZ) + timedelta(days=7)).strftime("%Y-%m-%d"),
                    "category": "games",
                    "source": "steam_api",
                    "status": "active",
                    "discovered_at": now_bj().isoformat(),
                })

    except Exception as e:
        log(f"Steam API 失败: {safe_text(e, 100)}", level="ERROR")

    log(f"Steam: 收集到 {len(activities)} 条免费游戏")
    return activities


# ============================================================
# GOG embed API → 免费游戏
# ============================================================

GOG_API_URL = "https://embed.gog.com/games/ajax/filtered"


def collect_gog_free_games() -> list[dict]:
    """从 GOG embed API 获取免费游戏。

    GOG 偶尔有限时免费领取活动，这个 API 返回当前免费游戏列表。
    没有活动时返回空列表（正常情况）。
    """
    activities: list[dict] = []
    try:
        resp = requests.get(
            GOG_API_URL,
            params={"price": "free", "hideInstallation": "game"},
            headers=BROWSER_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        products = data.get("products", [])
        for p in products:
            title = p.get("title", "")
            if not title:
                continue
            slug = p.get("slug", "")
            url = f"https://www.gog.com/en/game/{slug}" if slug else "https://www.gog.com"
            activities.append({
                "title": f"GOG 免费: {title}",
                "url": url,
                "description": "GOG 限时免费领取，入库永久保留",
                "start_date": BJ.strftime("%Y-%m-%d"),
                "end_date": (BJ + timedelta(days=7)).strftime("%Y-%m-%d"),
                "category": "games",
                "status": "active",
                "discovered_at": now_bj().isoformat(),
            })
        log(f"GOG API: {len(products)} 个免费游戏")
    except Exception as e:
        log(f"GOG API 失败: {safe_text(e, 100)}", level="ERROR")
    return activities


# ============================================================
# 汇总
# ============================================================

def collect_category(category: str) -> list[dict]:
    """收集一个类别的所有活动。"""
    if category == "games":
        # 游戏类：Epic + Steam + GOG 喜加一
        results = collect_epic_free_games()
        time.sleep(2)
        results.extend(collect_steam_free_weekend())
        time.sleep(2)
        results.extend(collect_gog_free_games())
        return results
    else:
        return []
