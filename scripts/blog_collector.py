"""博客聚合收集器：从多个薅羊毛博客/聚合站抓取条目。

设计思路：
- 不自己硬抓云厂商活动页（反爬严重），改为抓别人已做好的聚合博客
- 每个源独立抓取，失败不影响其他源
- 条目用关键词过滤后标准化，与现有收集器结果合并去重

源清单：
- games: IsThereAnyDeal（免费游戏聚合）、Reddit FreeGameFindings/GameDeals
- ai:    异次元软件世界、小众软件、阮一峰周刊、V2EX cloud 节点
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import timedelta

from utils import log, today_bj


# 完整浏览器头（避免被反爬拦截）
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 薅羊毛关键词（标题含任一即相关）
WOOL_KEYWORDS = [
    "免费", "限免", "喜加一", "白嫖", "赠送", "0元", "代金券", "优惠", "打折",
    "福利", "免费领", "免费送", "free", "giveaway", "100% off",
    "voucher", "coupon", "trial", "deal",
]


def fetch(url: str, timeout: int = 20) -> str | None:
    """抓取 URL 返回文本，失败返回 None。"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log(f"  抓取失败 {url[:70]}: {e}", level="WARN")
        return None


def is_wool_related(title: str) -> bool:
    """标题是否与薅羊毛相关。"""
    t = title.lower()
    return any(k.lower() in t for k in WOOL_KEYWORDS)


def _activity(title: str, url: str, source_name: str, category: str, desc: str = "") -> dict:
    """构造标准化条目（兼容 normalize_activity）。"""
    today = today_bj()
    return {
        "title": title.strip()[:200],
        "source_url": url,
        "claim_url": url,
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=7)).isoformat(),
        "value": "",
        "description": desc or f"来源: {source_name}",
        "tags": ["blog", source_name],
        "discovered_at": today.isoformat(),
    }


# ──────────────────────────── 各源解析器 ────────────────────────────

def parse_itad(html: str) -> list[dict]:
    """IsThereAnyDeal 主页：提取 -100% 免费游戏。

    结构: <a href="/game/SLUG/info/">...<img alt="NAME banner">...-100%...
    """
    acts = []
    pairs = re.findall(
        r'href="(/game/([^/]+)/info/)"[^>]*>.*?alt="([^"]+)"',
        html, re.S,
    )
    for href, slug, alt in pairs:
        name = alt.replace(" banner", "").strip()
        if not name or "logo" in name.lower():
            continue
        # 确认这个游戏块含 -100%（免费）
        idx = html.find(f"/game/{slug}/info/")
        block = html[idx:idx + 2000]
        if "-100%" not in block:
            continue
        acts.append(_activity(
            f"{name}（ITAD 免费游戏）",
            f"https://isthereanydeal.com{href}",
            "IsThereAnyDeal", "games",
            f"IsThereAnyDeal 聚合: {name} 当前 100% off",
        ))
    return acts


def parse_blog_articles(html: str, source_name: str, category: str, base_url: str = "") -> list[dict]:
    """通用博客文章列表解析：提取标题+链接，关键词过滤。

    覆盖 WordPress（entry-title）、通用 h2>a、a[title] 三种结构。
    """
    acts = []
    patterns = [
        r'<h2[^>]*class="[^"]*entry-title[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
        r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
        r'<a[^>]*href="([^"]+)"[^>]*title="([^"]+)"[^>]*>',
    ]
    seen: set[str] = set()
    for pat in patterns:
        for url, title in re.findall(pat, html):
            title = title.strip()
            if not title or title in seen:
                continue
            if not is_wool_related(title):
                continue
            if base_url and not url.startswith("http"):
                url = base_url.rstrip("/") + "/" + url.lstrip("/")
            if not url.startswith("http"):
                continue
            seen.add(title)
            acts.append(_activity(title, url, source_name, category))
    return acts


def parse_ruanyifeng(html: str) -> list[dict]:
    """阮一峰博客：提取最新周刊链接作为条目。

    周刊标题不含薅羊毛关键词，但周刊正文里常有免费工具/资源。
    这里只提取最新周刊链接，让用户点进去看。
    """
    acts = []
    # 找 weekly-issue 链接（取最新一篇）
    m = re.search(
        r'href="(https://www\.ruanyifeng\.com/blog/\d+/\d+/weekly-issue-\d+\.html)"[^>]*>([^<]+)</a>',
        html,
    )
    if m:
        url, title = m.group(1), m.group(2).strip()
        acts.append(_activity(
            title,
            url, "阮一峰周刊", "ai",
            "阮一峰科技爱好者周刊，常含免费工具与资源推荐",
        ))
    return acts


def parse_reddit_freegames(json_text: str, source_name: str = "Reddit") -> list[dict]:
    """Reddit JSON API: 提取免费游戏帖子。"""
    acts = []
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return acts
    children = data.get("data", {}).get("children", [])
    for c in children:
        d = c.get("data", {})
        title = d.get("title", "")
        url = d.get("url", "")
        if not title or not url:
            continue
        flair = (d.get("link_flair_text") or "").lower()
        if "expired" in flair:
            continue
        acts.append(_activity(
            f"{title}（Reddit 免费）",
            url, source_name, "games",
            f"Reddit 社区投稿: {title}",
        ))
    return acts


def parse_v2ex_cloud(json_text: str) -> list[dict]:
    """V2EX cloud 节点 JSON: 提取云厂商优惠讨论。"""
    acts = []
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return acts
    if not isinstance(data, list):
        return acts
    for t in data:
        title = t.get("title", "")
        tid = t.get("id")
        if not title or not tid:
            continue
        if not is_wool_related(title):
            continue
        acts.append(_activity(
            title,
            f"https://www.v2ex.com/t/{tid}",
            "V2EX-cloud", "ai",
        ))
    return acts


# ──────────────────────────── 源配置 ────────────────────────────

SOURCES: dict[str, list[dict]] = {
    "games": [
        {"name": "IsThereAnyDeal", "url": "https://isthereanydeal.com/",
         "parser": "itad"},
        {"name": "Reddit-FreeGameFindings",
         "url": "https://www.reddit.com/r/FreeGameFindings/new.json?limit=25",
         "parser": "reddit_json"},
        {"name": "Reddit-GameDeals",
         "url": "https://www.reddit.com/r/GameDeals/new.json?limit=25",
         "parser": "reddit_json"},
    ],
    "ai": [
        {"name": "异次元软件世界", "url": "https://www.iplaysoft.com/",
         "parser": "iplaysoft"},
        {"name": "小众软件", "url": "https://www.appinn.com/",
         "parser": "appinn"},
        {"name": "阮一峰周刊", "url": "https://www.ruanyifeng.com/blog/",
         "parser": "ruanyifeng"},
        {"name": "V2EX-cloud",
         "url": "https://www.v2ex.com/api/topics/show.json?node_name=cloud",
         "parser": "v2ex_json"},
    ],
}


# ──────────────────────────── 主入口 ────────────────────────────

def collect_blog_activities(category: str) -> list[dict]:
    """收集指定类别的博客薅羊毛条目。

    Args:
        category: "ai" 或 "games"

    Returns:
        标准化条目列表（未经 normalize_activity 处理的 raw dict）
    """
    log(f"--- 博客聚合器 [{category}] ---")
    sources = SOURCES.get(category, [])
    all_acts: list[dict] = []

    for src in sources:
        name = src["name"]
        url = src["url"]
        parser = src["parser"]
        log(f"抓取 {name}: {url[:70]}")
        text = fetch(url)
        if not text:
            log(f"  {name} 抓取失败，跳过")
            continue
        try:
            if parser == "itad":
                acts = parse_itad(text)
            elif parser == "reddit_json":
                acts = parse_reddit_freegames(text, name)
            elif parser == "v2ex_json":
                acts = parse_v2ex_cloud(text)
            elif parser == "ruanyifeng":
                acts = parse_ruanyifeng(text)
            else:
                # 通用博客解析
                base = ""
                if "iplaysoft" in url:
                    base = "https://www.iplaysoft.com"
                elif "appinn" in url:
                    base = "https://www.appinn.com"
                elif "ruanyifeng" in url:
                    base = "https://www.ruanyifeng.com"
                acts = parse_blog_articles(text, name, category, base)
        except Exception as e:
            log(f"  {name} 解析失败: {e}", level="WARN")
            acts = []
        log(f"  {name}: 提取 {len(acts)} 条")
        all_acts.extend(acts)

    log(f"博客聚合器 [{category}] 共提取 {len(all_acts)} 条")
    return all_acts


if __name__ == "__main__":
    # 本地测试
    import sys
    cat = sys.argv[1] if len(sys.argv) > 1 else "games"
    result = collect_blog_activities(cat)
    print(f"\n=== {cat} 提取 {len(result)} 条 ===")
    for a in result[:10]:
        print(f"  {a['title'][:50]} -> {a['source_url'][:60]}")
