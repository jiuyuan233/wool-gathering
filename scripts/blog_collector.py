"""博客聚合收集器：从多个薅羊毛博客/聚合站抓取条目。

设计思路：
- 不自己硬抓云厂商活动页（反爬严重），改为抓别人已做好的聚合博客
- 每个源独立抓取，失败不影响其他源
- 条目用关键词过滤后标准化，与现有收集器结果合并去重
- 开车帖（群发车/线报）自动归 "drive" 分区，开源工具自动归 "open-source" 分区

源清单：
- games:       IsThereAnyDeal（免费游戏聚合）、Reddit FreeGameFindings
- ai:          异次元软件世界、小众软件
- drive:       V2EX cloud / promotions 节点（群发车线报，云优惠讨论自动分流回 ai）
"""
from __future__ import annotations

import html as _html
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

# 薅羊毛价值词：标题必须含任一才算相关（单纯"免费"不够，避免讨论帖误判）
WOOL_VALUE_WORDS = [
    "限免", "喜加一", "代金券", "0元", "白嫖", "免费领", "免费送",
    "赠送", "送 1 万", "送1万", "送1 万", "送 1万", "送万积分", "送积分", "送会员",
    "年卡", "vip", "svip", "会员优惠", "低价优惠", "历史低价", "必入低价",
    "打折", "优惠", "折扣", "8折", "9折", "半价", "特价", "特惠",
    "限时", "周年庆", "双11", "双 11", "618", "大促", "福利",
    "免费试用", "免费体验", "免费额度", "免费提供",
    "免费虚拟机", "免费专业版",
    "free", "giveaway", "100% off", "-100%",
]

# 排除模式：标题匹配则算误判（讨论帖/广告/泛首页标题）
# 注意：开车/发车/上车/线报类标志词不再排除，改由 is_drive_post 识别后归 "drive" 分区
WOOL_EXCLUDE_PATTERNS = [
    r"还能.*吗", r"怎么办", r"如何.*吗", r"请教", r"问一下", r"能不能",
    r"分享免费、小巧", r"周刊",
    r"感兴趣的朋友",
]

# 开车线报识别：群发车/上车/线报类帖子 → 归 "drive" 分区（不要求价值词）
DRIVE_HINTS = ["开车", "发车", "上车", "拼车", "线报", "羊毛群", "薅羊毛", "白嫖群"]

# 开源工具识别：含"开源"或明显是 GitHub 免费工具，且非限时促销
OPEN_SOURCE_HINTS = ["开源", "github 上发现", "在 github 发现", "免费小工具", "工具箱"]

# 购物/打折活动（双11、软件打折、红包等）→ shopping 分区
SHOPPING_HINTS = ["双11", "双 11", "红包", "wps", "vmware", "videoproc",
                  "复旦", "周年庆", "打折好价", "codex"]

# 视频会员优惠（爱奇艺、腾讯视频等）→ video-vip 分区
VIDEO_VIP_HINTS = ["爱奇艺", "腾讯视频"]

# 网盘会员优惠（夸克、百度等）→ netdisk-vip 分区
NETDISK_VIP_HINTS = ["夸克网盘", "百度网盘", "网盘svip", "网盘 svip", "网盘会员"]
OPEN_SOURCE_EXCLUDE = ["限时", "打折", "优惠", "年卡", "vip", "赠送", "周年庆", "半价"]


def fetch(url: str, timeout: int = 20) -> str | None:
    """抓取 URL 返回文本，失败返回 None。429 限流时等 3 秒重试一次。"""
    import time as _time
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                log(f"  429 限流，3 秒后重试 {url[:60]}")
                _time.sleep(3)
                continue
            log(f"  抓取失败 {url[:70]}: HTTP {e.code}", level="WARN")
            return None
        except Exception as e:
            log(f"  抓取失败 {url[:70]}: {e}", level="WARN")
            return None
    return None


def is_wool_related(title: str) -> bool:
    """标题是否与薅羊毛相关：含价值词 + 不匹配排除模式。"""
    # 排除讨论帖/广告/泛标题
    for pat in WOOL_EXCLUDE_PATTERNS:
        if re.search(pat, title):
            return False
    t = title.lower()
    return any(w.lower() in t for w in WOOL_VALUE_WORDS)


def is_open_source(title: str) -> bool:
    """是否开源免费工具（一直免费，非限时优惠）→ 归 open-source 类。"""
    low = title.lower()
    if not any(h in low for h in OPEN_SOURCE_HINTS):
        return False
    # 含限时促销词的不算纯开源工具
    return not any(w in low for w in OPEN_SOURCE_EXCLUDE)


def is_drive_post(title: str) -> bool:
    """是否开车线报帖（群发车/上车/线报）→ 归 drive 分区。"""
    low = title.lower()
    return any(h in low for h in DRIVE_HINTS)


def is_shopping(title: str) -> bool:
    """是否购物/打折活动（双11、软件打折、红包等）→ 归 shopping 分区。"""
    low = title.lower()
    return any(h in low for h in SHOPPING_HINTS)


def is_video_vip(title: str) -> bool:
    """是否视频会员优惠（爱奇艺、腾讯视频等）→ 归 video-vip 分区。"""
    low = title.lower()
    return any(h in low for h in VIDEO_VIP_HINTS)


def is_netdisk_vip(title: str) -> bool:
    """是否网盘会员优惠（夸克、百度等）→ 归 netdisk-vip 分区。"""
    low = title.lower()
    return any(h in low for h in NETDISK_VIP_HINTS)


def _activity(
    title: str, url: str, source_name: str, category: str, desc: str = "",
    end_days: int | None = 7,
) -> dict:
    """构造标准化条目（兼容 normalize_activity）。

    标题统一 html.unescape：RSS/博客数据里的 &amp; 等实体还原成原字符，
    避免 SVG 渲染时被二次转义成 &amp;amp;。

    end_days=None/0 表示无结束时间（长期免费，如开源工具），end_date 置空。
    """
    today = today_bj()
    return {
        "title": _html.unescape(title).strip()[:200],
        "category": category,
        "source_url": url,
        "claim_url": url,
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=end_days)).isoformat() if end_days else "",
        "value": "",
        "description": _html.unescape(desc or f"来源: {source_name}"),
        "tags": ["blog", source_name],
        "discovered_at": today.isoformat(),
    }


# ──────────────────────────── 各源解析器 ────────────────────────────

def parse_itad(html: str) -> list[dict]:
    """IsThereAnyDeal 主页：提取 -100% 免费游戏 + 所属商店。

    ITAD 聚合了 Epic/Steam/GOG/Xbox/PSN/eShop/GMG/Fanatical/Humble 等商店，
    每个游戏块含: /game/slug/ 链接 + banner alt 名 + -100% 价格 + shop 商店名。
    按 class="game" 切块，块内提取四要素。
    """
    acts = []
    # 按 game 块切分（Svelte SSR，class="game svelte-xxx"）
    blocks = re.split(r'class="game\s+svelte-[\w]+"', html)
    seen_slugs: set[str] = set()
    for b in blocks[1:]:  # 第一段是页头
        m = re.search(r'href="/game/([^/]+)/info/"', b)
        if not m:
            continue
        slug = m.group(1)
        if slug in seen_slugs:
            continue
        # 只保留 100% off 的块
        if "-100%" not in b:
            continue
        seen_slugs.add(slug)
        # 游戏名（img alt）
        alt = re.search(r'alt="([^"]+)"', b)
        name = (alt.group(1) if alt else slug).replace(" banner", "").strip()
        if not name or "logo" in name.lower():
            continue
        # 所属商店（class="shop" 后的文本）
        shop_m = re.search(r'class="shop[^"]*"[^>]*>(.{0,150}?)</(?:div|span)>', b, re.S)
        shop = re.sub(r"<[^>]+>", " ", shop_m.group(1)).strip() if shop_m else ""
        # ITAD 特例：站点自己送的游戏
        if slug == "over-the-hill":
            shop = "ITAD"
        display_shop = shop or "ITAD"
        acts.append(_activity(
            f"[{display_shop}] {name}（限免）",
            f"https://isthereanydeal.com/game/{slug}/info/",
            "IsThereAnyDeal", "games",
            f"{display_shop} 100% off 限免: {name}",
        ))
    return acts


def _pretty_slug(slug: str) -> str:
    """URL slug 美化: offrecord-episode-1 -> Offrecord Episode 1"""
    words = slug.replace("_", "-").split("-")
    out = []
    for w in words:
        if w.isdigit():
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def parse_itchio(html: str) -> list[dict]:
    """itch.io 限时免费页。

    itch.io 是服务端渲染，game_cell 块含作者子域链接 + 标题。
    标题优先级: a.title 文本 > data-title > title 属性 > alt > slug 美化。
    """
    acts = []
    seen: set[str] = set()
    blocks = re.split(r'class="game_cell', html)
    candidates = []
    for b in blocks[1:]:
        link = re.search(r'href="(https://[\w.-]+\.itch\.io/[\w-]+)"', b)
        if not link:
            continue
        url = link.group(1)
        slug = url.rsplit("/", 1)[-1]
        # 标题多级回退
        t = (
            re.search(r'<a[^>]*class="[^"]*\btitle\b[^"]*"[^>]*>([^<]+)</a>', b)
            or re.search(r'data-title="([^"]+)"', b)
            or re.search(r'title="([^"]+)"', b)
            or re.search(r'alt="([^"]+)"', b)
        )
        name = (t.group(1).strip() if t else "") or _pretty_slug(slug)
        candidates.append((name, url))
    # 兜底：无 game_cell 结构时扫全页
    if not candidates:
        for m in re.finditer(r'href="(https://[\w.-]+\.itch\.io/[\w-]+)"[^>]*data-title="([^"]+)"', html):
            candidates.append((m.group(2).strip(), m.group(1)))
    for name, url in candidates:
        if url in seen:
            continue
        seen.add(url)
        acts.append(_activity(
            f"[itch.io] {name}（限免）",
            url, "itch.io", "games",
            f"itch.io 限时免费: {name}",
        ))
    return acts


def parse_ggdeals(html: str) -> list[dict]:
    """GG.deals 免费游戏新闻页：提取免费游戏报道链接。"""
    acts = []
    seen: set[str] = set()
    # 新闻列表条目: <a href="/news/xxx"> 或 article 标题
    for m in re.finditer(r'<a[^>]+href="(/news/[^"]+)"[^>]*>([^<]{10,150})</a>', html):
        url, title = f"https://gg.deals{m.group(1)}", m.group(2).strip()
        if url in seen or not is_wool_related(title):
            continue
        seen.add(url)
        acts.append(_activity(
            f"{title}（GG.deals）",
            url, "GG.deals", "games",
            f"GG.deals 免费游戏报道: {title}",
        ))
    return acts


def parse_blog_articles(html: str, source_name: str, category: str, base_url: str = "") -> list[dict]:
    """通用博客文章列表解析：提取标题+链接，关键词过滤 + 开源分流。

    覆盖 WordPress（entry-title）、通用 h2>a、a[title] 三种结构。
    开源工具（is_open_source）自动归 "open-source" 类别。
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
            # 开源工具单独识别（不要求价值词）；其他要求薅羊毛价值词
            is_oss = is_open_source(title)
            if not is_oss and not is_wool_related(title):
                continue
            if base_url and not url.startswith("http"):
                url = base_url.rstrip("/") + "/" + url.lstrip("/")
            if not url.startswith("http"):
                continue
            seen.add(title)
            # 分类分流：开源 → 购物 → 视频会员 → 网盘会员 → 默认
            if is_oss:
                actual_cat = "open-source"
                end_days_val = None
            elif is_shopping(title):
                actual_cat = "shopping"
                end_days_val = 7
            elif is_video_vip(title):
                actual_cat = "video-vip"
                end_days_val = 7
            elif is_netdisk_vip(title):
                actual_cat = "netdisk-vip"
                end_days_val = 7
            else:
                actual_cat = category
                end_days_val = 7
            acts.append(_activity(title, url, source_name, actual_cat,
                                  end_days=end_days_val))
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


def parse_rss(xml_text: str, source_name: str, category: str, filter_wool: bool = True) -> list[dict]:
    """通用 RSS/Atom 解析器。

    支持 RSS 2.0 (<item><title><link><description>) 和
    Atom (<entry><title><link href><content>)。
    """
    acts = []
    # Atom <entry>
    entries = re.findall(r"<entry[^>]*>(.*?)</entry>", xml_text, re.S)
    for e in entries:
        title = re.search(r"<title[^>]*>(.*?)</title>", e, re.S)
        link = re.search(r'<link[^>]*href="([^"]+)"', e)
        if not title or not link:
            continue
        t = re.sub(r"<[^>]+>", "", title.group(1)).strip()
        u = link.group(1).strip()
        if not t or not u:
            continue
        if filter_wool and not is_wool_related(t):
            continue
        acts.append(_activity(
            f"{t}（{source_name}）",
            u, source_name, category,
        ))
    # RSS 2.0 <item>
    items = re.findall(r"<item[^>]*>(.*?)</item>", xml_text, re.S)
    for it in items:
        title = re.search(r"<title[^>]*>(.*?)</title>", it, re.S)
        link = re.search(r"<link[^>]*>(.*?)</link>", it, re.S)
        if not title or not link:
            continue
        t = re.sub(r"<[^>]+>", "", title.group(1)).strip()
        u = re.sub(r"<[^>]+>", "", link.group(1)).strip()
        if not t or not u:
            continue
        if filter_wool and not is_wool_related(t):
            continue
        acts.append(_activity(
            f"{t}（{source_name}）",
            u, source_name, category,
        ))
    return acts


def parse_v2ex_cloud(json_text: str) -> list[dict]:
    """V2EX cloud 节点 JSON: 开车帖归 drive，云优惠讨论归 ai。"""
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
        if is_drive_post(title):
            # 开车线报帖 → drive 分区（不要求价值词）
            cat = "drive"
        elif is_wool_related(title):
            cat = "ai"
        else:
            continue
        acts.append(_activity(
            title,
            f"https://www.v2ex.com/t/{tid}",
            "V2EX-cloud", cat,
        ))
    return acts


def parse_v2ex_promotions(json_text: str) -> list[dict]:
    """V2EX promotions 节点 JSON: 推广/开车帖 → drive 分区。

    promotions 节点本身全是推广帖，只过滤明显讨论性质的内容，
    开车帖（is_drive_post）与含价值词的推广帖都收录。
    """
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
        # 推广节点：开车帖直接收；非开车帖要求含价值词（过滤纯讨论）
        if not is_drive_post(title) and not is_wool_related(title):
            continue
        acts.append(_activity(
            title,
            f"https://www.v2ex.com/t/{tid}",
            "V2EX-promotions", "drive",
        ))
    return acts


# ──────────────────────────── 源配置 ────────────────────────────

SOURCES: dict[str, list[dict]] = {
    "games": [
        {"name": "IsThereAnyDeal", "url": "https://isthereanydeal.com/",
         "parser": "itad"},
        {"name": "itch.io-限免",
         "urls": [
             "https://itch.io/games/on-sale?price=free",
             "https://itch.io/games/free",
         ],
         "parser": "itchio"},
        {"name": "Reddit-FreeGameFindings",
         "url": "https://www.reddit.com/r/FreeGameFindings/.rss",
         "parser": "reddit_rss"},
    ],
    "ai": [
        {"name": "异次元软件世界", "url": "https://www.iplaysoft.com/",
         "parser": "iplaysoft"},
        {"name": "小众软件", "url": "https://www.appinn.com/",
         "parser": "appinn"},
    ],
    # 开车线报分区：V2EX 群发车等线报帖（V2EX 统一在 drive 步骤抓取，
    # cloud 节点的云优惠讨论会自动分流回 ai 类别）
    "drive": [
        {"name": "V2EX-cloud",
         "url": "https://www.v2ex.com/api/topics/show.json?node_name=cloud",
         "parser": "v2ex_json"},
        {"name": "V2EX-promotions",
         "url": "https://www.v2ex.com/api/topics/show.json?node_name=promotions",
         "parser": "v2ex_promotions"},
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
        parser = src["parser"]
        # 支持多候选 URL：依次尝试直到成功
        urls = src.get("urls") or ([src["url"]] if src.get("url") else [])
        if not urls:
            continue
        text = None
        used_url = ""
        for u in urls:
            log(f"抓取 {name}: {u[:70]}")
            text = fetch(u)
            if text:
                used_url = u
                break
            log(f"  {name} 该 URL 失败，尝试下一个")
        if not text:
            log(f"  {name} 全部 URL 抓取失败，跳过")
            continue
        try:
            if parser == "itad":
                acts = parse_itad(text)
            elif parser == "itchio":
                acts = parse_itchio(text)
            elif parser == "ggdeals":
                acts = parse_ggdeals(text)
            elif parser == "reddit_json":
                acts = parse_reddit_freegames(text, name)
            elif parser == "reddit_rss":
                # Reddit FreeGameFindings 里基本都是免费的，不过滤关键词
                acts = parse_rss(text, name, "games", filter_wool=False)
                # 限制 15 条，避免过多
                acts = acts[:15]
            elif parser == "v2ex_json":
                acts = parse_v2ex_cloud(text)
            elif parser == "v2ex_promotions":
                acts = parse_v2ex_promotions(text)
                # 限制 15 条，避免过多
                acts = acts[:15]
            elif parser == "ruanyifeng":
                acts = parse_ruanyifeng(text)
            else:
                # 通用博客解析
                base = ""
                if "iplaysoft" in used_url:
                    base = "https://www.iplaysoft.com"
                elif "appinn" in used_url:
                    base = "https://www.appinn.com"
                elif "ruanyifeng" in used_url:
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
