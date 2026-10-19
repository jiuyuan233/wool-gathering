"""不依赖 AI 的直接收集器。

用 Reddit JSON API + RSS feed 直接拿结构化数据，
不需要 AI 中转站，不会超时，数据质量更高。

数据源：
- Reddit r/FreeGameFindings, r/FreeGamesOnSteam, r/GameDeals → 游戏类
- Reddit r/MLQuestions, r/MachineLearning → AI 类（找免费额度/GPU 相关帖子）
- IsThereAnyDeal RSS → 游戏类
- HuggingFace spaces RSS → AI 类
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

from utils import log, now_bj, safe_text


# 北京时区
BJ_TZ = timezone(timedelta(hours=8))

# 浏览器请求头（完整伪装）
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,en;q=0.7,en-US;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


# Reddit 子版块配置
REDDIT_SUBREDDITS = {
    "games": [
        "FreeGameFindings",
        "FreeGamesOnSteam",
        "GameDeals",
    ],
    "ai": [
        "MachineLearning",
        "LocalLLaMA",
    ],
}


def fetch_reddit(subreddit: str, limit: int = 25) -> list[dict]:
    """用 Reddit JSON API 获取帖子列表。

    Reddit 的 .json 后缀返回结构化数据，不需要 AI 解析。
    """
    url = f"https://www.reddit.com/r/{subreddit}/.json?limit={limit}"
    try:
        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        children = data.get("data", {}).get("children", [])
        posts = []
        for child in children:
            post = child.get("data", {})
            if not post.get("title"):
                continue
            posts.append(post)
        log(f"Reddit r/{subreddit}: 获取 {len(posts)} 条帖子")
        return posts
    except Exception as e:
        log(f"Reddit r/{subreddit} 失败: {safe_text(e, 100)}", level="ERROR")
        return []


def parse_reddit_post(post: dict, category: str) -> dict | None:
    """从 Reddit 帖子解析出活动信息。

    判断标题/内容是否包含免费活动关键词，
    提取标题、链接、时间等。
    """
    title = post.get("title", "")
    permalink = post.get("permalink", "")
    url = post.get("url", "")
    created_utc = post.get("created_utc", 0)
    score = post.get("score", 0)
    selftext = post.get("selftext", "")
    flair = post.get("link_flair_text", "") or ""

    # 完整链接
    full_url = f"https://www.reddit.com{permalink}" if permalink else url

    # 关键词判断
    title_lower = title.lower()
    combined = f"{title_lower} {flair.lower()} {selftext[:500].lower()}"

    if category == "games":
        # 游戏类：找免费/限免/喜加一
        free_keywords = ["free", "100% off", "限时免费", "限免", "喜加一", "giveaway", "免费领"]
        if not any(kw in combined for kw in free_keywords):
            return None
        # 排除已经过期的（[Expired] 标记）
        if "expired" in title_lower or "[expired]" in title_lower:
            return None
        cat_label = "games"
    else:
        # AI 类：找免费额度/GPU/代金券
        ai_keywords = ["free", "免费", "gpu", "credit", "代金券", "额度", "trial", "试用", "giveaway"]
        if not any(kw in combined for kw in ai_keywords):
            return None
        cat_label = "ai"

    # 解析时间
    try:
        created = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        discovered_at = created.astimezone(BJ_TZ).isoformat()
    except Exception:
        discovered_at = now_bj().isoformat()

    # 尝试从标题提取日期范围（如 [2026-10-19] 或 Oct 19）
    start_date = created.strftime("%Y-%m-%d")
    # 默认 7 天后过期
    end_date = (created + timedelta(days=7)).strftime("%Y-%m-%d")

    # 提取外部链接（非 reddit 自身链接）
    external_url = url if url and "reddit.com" not in url else full_url

    return {
        "title": title[:200],
        "url": external_url,
        "description": f"Reddit r/{post.get('subreddit', '')} | ⬆{score} | {flair}".strip(" |"),
        "start_date": start_date,
        "end_date": end_date,
        "category": cat_label,
        "source": f"reddit/{post.get('subreddit', '')}",
        "status": "active",
        "discovered_at": discovered_at,
    }


def collect_category(category: str) -> list[dict]:
    """收集一个类别的所有活动。"""
    subreddits = REDDIT_SUBREDDITS.get(category, [])
    if not subreddits:
        log(f"[{category}] 无配置的 Reddit 源")
        return []

    all_activities: list[dict] = []
    for sub in subreddits:
        posts = fetch_reddit(sub, limit=25)
        for post in posts:
            post["subreddit"] = sub
            activity = parse_reddit_post(post, category)
            if activity:
                all_activities.append(activity)
        time.sleep(2)  # 间隔 2 秒，避免 Reddit 限流

    log(f"[{category}] Reddit 共收集 {len(all_activities)} 条活动")
    return all_activities
