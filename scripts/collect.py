"""主收集脚本：Action 入口。

不依赖 AI 中转站，用 Reddit JSON API 直接拿结构化数据。

设计原则：
- 不同板块分时间段请求，不要频繁请求
- 每次只更新一个类别，标注更新时间
- 每天晚上全部整理一下（生成 SVG + README）

用法：
  python collect.py ai         # 只处理 AI 类（含 open-source 分流）= ai-cloud + ai-blog
  python collect.py games      # 只处理游戏类 = games-direct + games-blog
  python collect.py drive      # 只处理开车线报类
  python collect.py ai,drive   # 逗号分隔多模式
  python collect.py finalize   # 只做整理（SVG + README）
  python collect.py all        # 全部处理（默认，手动触发用）

子模式（用于把请求分散到全天，避免集中压免费源网站）：
  python collect.py ai-cloud       # 仅抓云厂商（华为云/阿里云/腾讯云）
  python collect.py ai-blog        # 仅抓博客聚合（ai 板块，含 open-source 分流）
  python collect.py games-direct   # 仅抓 Epic/Steam/GOG 官方 API
  python collect.py games-blog     # 仅抓 ITAD/itch.io/Reddit/ggdeals
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from calendar_generator import generate_docs_data, generate_readme
from blog_collector import collect_blog_activities
from cloud_collector import collect_cloud_activities
from dedup import dedupe_within, merge, normalize_activity
from direct_collector import collect_category as collect_games_category
from svg_calendar import generate_svg
from utils import (
    DATA_DIR,
    load_json,
    log,
    make_id,
    now_bj,
    safe_text,
    save_json,
    today_bj,
)


CATEGORIES = ["ai", "open-source", "drive", "games", "shopping", "video-vip", "netdisk-vip", "game-discount"]


def _guess_category_from_url(url: str) -> tuple[str, str]:
    """根据 URL 关键词判断分类和 type。返回 (category, type)。"""
    u = url.lower()
    if "xiaoheihe" in u:
        return "game-discount", "heybox"
    if any(k in u for k in ["epic", "store.steampowered", "gog.com", "itch.io"]):
        return "games", "html"
    if any(k in u for k in ["huaweicloud", "aliyun", "cloud.tencent", "bce.baidu"]):
        return "ai", "html"
    if "v2ex" in u:
        return "drive", "html"
    if any(k in u for k in ["github", "opensource", "npmjs", "pypi"]):
        return "open-source", "html"
    if any(k in u for k in ["iqiyi", "v.qq", "youku", "mgtv", "bilibili"]):
        return "video-vip", "html"
    if any(k in u for k in ["quark", "pan.baidu", "aliyundrive", "115.com"]):
        return "netdisk-vip", "html"
    if any(k in u for k in ["tmall", "taobao", "jd.com", "suning"]):
        return "shopping", "html"
    if any(k in u for k in ["appinn", "iplaysoft", "landian", "xbeta"]):
        return "ai", "html"
    return "ai", "html"



def _archive_month_of(a: dict) -> str:
    """归档月份键：end_date 优先，其次 start_date / discovered_at，都没有归 unknown。"""
    for key in ("end_date", "start_date"):
        v = a.get(key) or ""
        if re.match(r"^\d{4}-\d{2}", v):
            return v[:7]
    m = re.match(r"^(\d{4}-\d{2})", a.get("discovered_at") or "")
    return m.group(1) if m else "unknown"


def archive_index_path():
    """归档索引文件路径：docs/archive/index.json。"""
    return DATA_DIR.parent / "docs" / "archive" / "index.json"


def archived_ids() -> set:
    """读归档索引，返回已归档活动 id 集合（索引缺失返回空集）。"""
    index = load_json(archive_index_path()) or []
    if not isinstance(index, list):
        return set()
    return {a.get("id", "") for a in index if isinstance(a, dict) and a.get("id")}


def archive_expired() -> int:
    """把过期活动按月归档到 docs/archive/YYYY-MM.md，从 activities.json 移除（AGENT.md 第 20 节）。

    归档索引 docs/archive/index.json 持久保存所有已归档活动（按 id 去重），
    每次运行用索引全量重渲染各月 .md——旧实现只写「本批归档」会把同月文件里
    之前的历史条目覆盖掉，这里必须全量重建。
    """
    from collections import defaultdict
    today = today_bj().isoformat()
    archive_dir = DATA_DIR.parent / "docs" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    index = load_json(archive_index_path()) or []
    if not isinstance(index, list):
        index = []
    index_by_id = {a.get("id", ""): a for a in index if isinstance(a, dict) and a.get("id")}

    archived_count = 0
    for cat in CATEGORIES:
        path = DATA_DIR / cat / "activities.json"
        acts = load_json(path) or []
        kept = []
        for a in acts:
            status = a.get("status", "")
            end = a.get("end_date", "")
            if status == "ended" or (end and end < today):
                if not a.get("id"):
                    a["id"] = make_id(a.get("title", ""), a.get("source_url", ""))
                if a["id"] not in index_by_id:
                    index_by_id[a["id"]] = a
                    archived_count += 1
            else:
                kept.append(a)
        if len(kept) < len(acts):
            save_json(path, kept)

    if not index_by_id:
        log("无过期活动需归档")
        return 0

    # 全量重建索引（按月份分组排序）+ 重渲染各月 .md（防同月文件被覆盖丢历史）
    by_month = defaultdict(list)
    for a in index_by_id.values():
        by_month[_archive_month_of(a)].append(a)

    cat_names = {"ai": "AI/云服务", "open-source": "开源工具", "drive": "开车线报", "games": "游戏喜加一",
                 "shopping": "购物优惠", "video-vip": "视频会员", "netdisk-vip": "网盘会员", "game-discount": "游戏打折"}
    cat_emojis = {"ai": "🤖", "open-source": "🔓", "drive": "🚗", "games": "🎮", "shopping": "🛒",
                  "video-vip": "📺", "netdisk-vip": "💾", "game-discount": "🏷️"}

    new_index = []
    for month in sorted(by_month):
        items = sorted(by_month[month], key=lambda a: a.get("end_date") or a.get("start_date") or "")
        new_index.extend(items)

        archive_path = archive_dir / f"{month}.md"
        title = f"{month[:4]}年{int(month[5:7])}月归档" if re.match(r"^\d{4}-\d{2}$", month) else "未知月份归档"
        by_cat = defaultdict(list)
        for a in items:
            by_cat.setdefault(a.get("category", ""), []).append(a)
        lines = [f"# {title}", "", "> 已过期的活动归档，从主页面移除。", ""]
        for cat in CATEGORIES:
            cat_acts = by_cat.get(cat, [])
            if not cat_acts:
                continue
            lines.append(f"## {cat_emojis.get(cat, '📋')} {cat_names.get(cat, cat)}")
            lines.append("")
            lines.append("| 活动 | 福利 | 时间 | 来源 |")
            lines.append("|------|------|------|------|")
            for a in cat_acts:
                t = a.get("title", "").replace("|", "\\|")
                value = (a.get("value") or "—").replace("|", "\\|")
                start = a.get("start_date") or "?"
                end = a.get("end_date") or "?"
                url = a.get("source_url", "") or a.get("claim_url", "")
                link = f"[链接]({url})" if url else "—"
                lines.append(f"| {t} | {value} | {start} ~ {end} | {link} |")
            lines.append("")
        archive_path.write_text("\n".join(lines), encoding="utf-8")
        log(f"归档 {month}: {len(items)} 条")

    save_json(archive_index_path(), new_index)
    log(f"归档完成: 本次新增 {archived_count} 条，索引共 {len(new_index)} 条")
    return archived_count


def process_pending_urls() -> int:
    """处理 PENDING_URLS.md 里用户提交的网址或自然语言描述。

    支持两种输入：
    1. URL 行（http://...）→ 登记 sources.json → html 源当场抓一次内容入库 /
       heybox 源触发 Playwright 抓取
    2. 自然语言行（如"Qoder每天领100积分 #ai"）→ 用 AI 理解并直接创建活动

    Returns:
        处理的条目数量
    """
    pending_path = DATA_DIR.parent / "PENDING_URLS.md"
    if not pending_path.exists():
        log("PENDING_URLS.md 不存在，跳过")
        return 0

    content = pending_path.read_text(encoding="utf-8")

    # 分割「待处理」和「已处理」区
    if "## 已处理" not in content:
        log("PENDING_URLS.md 格式异常（缺少「已处理」区），跳过")
        return 0

    parts = content.split("## 已处理", 1)
    todo_section = parts[0]
    done_section = "## 已处理" + parts[1]

    # 提取「待处理」区的网址行和自然语言行
    url_pattern = re.compile(r'^(https?://\S+)(?:\s*#\s*(\w[\w-]*))?\s*$')
    urls_to_process = []
    nl_to_process = []
    for line in todo_section.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--") or stripped.startswith(">") or stripped.startswith("#"):
            continue
        m = url_pattern.match(stripped)
        if m:
            urls_to_process.append((m.group(1), m.group(2), stripped))
        else:
            # 非URL的自然语言描述，提取 #分类 注释
            cat_match = re.search(r'#\s*(\w[\w-]*)\s*$', stripped)
            cat_hint = cat_match.group(1) if cat_match else None
            desc = re.sub(r'\s*#\s*\w[\w-]*\s*$', '', stripped).strip()
            if len(desc) > 3:
                nl_to_process.append((desc, cat_hint, stripped))

    if not urls_to_process and not nl_to_process:
        log("PENDING_URLS.md 无待处理内容")
        return 0

    log(f"PENDING_URLS.md: {len(urls_to_process)} 个网址, {len(nl_to_process)} 个自然语言描述")

    # 读取 sources.json
    sources_path = DATA_DIR / "sources.json"
    all_sources = load_json(sources_path) or []
    existing_urls = {s.get("url", "") for s in all_sources}

    today = now_bj().strftime("%Y-%m-%d")
    processed = []
    new_count = 0

    # ── 处理 URL 行 ──
    # 三步：登记到 sources.json（防重复提交）→ html 源当场抓一次内容入库 → heybox 源触发 Playwright 抓取
    # 注意：sources.json 里的 html 源只做登记，不参与日常轮询；日常轮询源清单见 docs/日常更新指南.md
    from urllib.parse import urlparse
    from blog_collector import fetch, parse_blog_articles

    new_urls: list[dict] = []  # {url, category, src_type, name}
    for url, cat_hint, original_line in urls_to_process:
        if cat_hint and cat_hint in CATEGORIES:
            category = cat_hint
            _, src_type = _guess_category_from_url(url)
        else:
            category, src_type = _guess_category_from_url(url)

        if url in existing_urls:
            processed.append(f"- [{today}] {url} → {category}，重复（sources.json 已有），跳过")
            log(f"  {url} → {category}，重复，跳过")
            continue

        domain = urlparse(url).netloc or url
        name = domain.replace("www.", "")[:30]
        all_sources.append({
            "name": name,
            "url": url,
            "category": category,
            "type": src_type,
            "enabled": True,
            "note": f"用户提交 + AI 自动接入（{today}）"
        })
        existing_urls.add(url)
        new_count += 1
        new_urls.append({"url": url, "category": category, "src_type": src_type, "name": name})

    if new_urls:
        save_json(sources_path, all_sources)
        log(f"sources.json: 新增 {new_count} 个源（总计 {len(all_sources)}）")

        for item in new_urls:
            url, category = item["url"], item["category"]
            if item["src_type"] == "heybox":
                # 小黑盒是 SPA，需 Playwright 渲染；当场触发 game-discount 抓取
                # （会读 sources.json 里所有 heybox 源；失败也有每天 15:53 的定时抓取兜底）
                log(f"  {url} → heybox 源，触发 game-discount 抓取...")
                try:
                    process_category("game-discount")
                    processed.append(f"- [{today}] {url} → {category}，已添加到 sources.json 并触发 Playwright 抓取")
                except Exception as e:
                    processed.append(f"- [{today}] {url} → {category}，已登记，抓取失败（{safe_text(e, 80)}），等待每天 15:53 定时抓取")
                continue

            # html 源：当场抓一次页面，通用解析器抽取活动入库
            log(f"  抓取用户提交 URL: {url[:70]}")
            text = fetch(url)
            raw_acts = []
            if text and len(text) > 200:
                try:
                    raw_acts = parse_blog_articles(text, item["name"], category)
                except Exception as e:
                    log(f"  {item['name']} 解析失败: {safe_text(e, 120)}", level="WARN")
            if raw_acts:
                added = _normalize_and_save(raw_acts, category, today_bj())
                if added:
                    processed.append(f"- [{today}] {url} → {category}，抓取到 {added} 条活动已入库")
                else:
                    processed.append(f"- [{today}] {url} → {category}，页面无符合收录规则的新活动")
                log(f"  {url} → 抽取 {len(raw_acts)} 条，入库 {added} 条")
            else:
                processed.append(
                    f"- [{today}] {url} → {category}，已添加到 sources.json；本次未抓到活动"
                    f"（页面可能需 JS 渲染/登录，或无符合收录规则的内容）")
                log(f"  {url} → 未抓到活动")

    # ── 处理自然语言描述（新增逻辑）──
    for desc, cat_hint, original_line in nl_to_process:
        category = cat_hint if cat_hint and cat_hint in CATEGORIES else "ai"
        log(f"  自然语言: {desc[:50]}... → [{category}]")
        try:
            acts = _process_natural_language(desc, category, today)
            if acts:
                act_path = DATA_DIR / category / "activities.json"
                existing_acts = load_json(act_path) or []
                existing_ids = {a.get("id") for a in existing_acts}
                added = 0
                for a in acts:
                    if a.get("id") not in existing_ids:
                        existing_acts.append(a)
                        existing_ids.add(a.get("id"))
                        added += 1
                if added > 0:
                    save_json(act_path, existing_acts)
                    log(f"    AI 创建 {added} 条活动 → data/{category}/activities.json")
                processed.append(f"- [{today}] {desc[:40]}... → {category}，AI 创建 {added} 条活动")
            else:
                processed.append(f"- [{today}] {desc[:40]}... → {category}，AI 未找到活动")
                log(f"    AI 未找到活动")
        except Exception as e:
            processed.append(f"- [{today}] {desc[:40]}... → 处理失败: {safe_text(e, 100)}")
            log(f"    自然语言处理失败: {e}", level="WARN")

    # ── 更新 PENDING_URLS.md ──
    new_todo_lines = []
    for line in todo_section.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("<!--") and not stripped.startswith(">") and not stripped.startswith("#"):
            if url_pattern.match(stripped):
                continue  # 跳过已处理的网址行
            # 跳过已处理的自然语言行
            if any(stripped == nl[2] for nl in nl_to_process):
                continue
        new_todo_lines.append(line)

    done_lines = done_section.rstrip().split("\n")
    insert_idx = len(done_lines)
    for i, line in enumerate(done_lines):
        if "<!--" in line and "AI 自动" in line:
            insert_idx = i
            break
    for p in reversed(processed):
        done_lines.insert(insert_idx, p)

    new_content = "\n".join(new_todo_lines) + "\n" + "\n".join(done_lines)
    pending_path.write_text(new_content, encoding="utf-8")
    log(f"PENDING_URLS.md: 已处理 {len(processed)} 条")

    return len(processed)


def _process_natural_language(desc: str, category: str, today: str) -> list[dict]:
    """用 AI 理解自然语言描述，创建薅羊毛活动。

    用户可能写"Qoder每天领100积分"这种描述，AI 基于描述本身的信息提取
    （聊天 API 无联网能力，不编造；描述信息不足时诚实返回空）。
    """
    try:
        from ai_client import AIClient
        from prompts import SYSTEM_PROMPT
    except ImportError:
        log("  AI 客户端不可用，跳过自然语言处理")
        return []

    ai = AIClient()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""用户在薅羊毛情报站提交了一条自然语言描述：

\"{desc}\"

分类提示：{category}
当前日期：{today}

请基于这段描述本身的信息理解并提取对应的薅羊毛/免费福利活动。
- 你没有联网能力：只根据描述里明确给出的信息提取，不要凭记忆编造活动细节、日期或链接
- 描述信息不足以确定活动细节时，宁可不抽
- 日期格式严格 YYYY-MM-DD，描述里算不出来的留空字符串
- 描述里没有可提取的活动时，返回 {{"activities": []}}

请严格按系统提示的 JSON 格式输出。"""},
    ]

    data = ai.chat_json(messages, max_tokens=2000)
    if not data or "activities" not in data:
        return []

    acts = []
    for a in data["activities"]:
        a["category"] = category
        a.setdefault("source_url", "")
        a.setdefault("claim_url", "")
        a.setdefault("start_date", today)
        a.setdefault("end_date", "")
        a.setdefault("value", "")
        a.setdefault("requirements", [])
        a.setdefault("description", desc[:50])
        a.setdefault("tags", [category])
        a["discovered_at"] = today + "T00:00:00.000000+08:00"
        a["last_seen"] = today
        a["status"] = "active"
        # ID 与全库统一（make_id），否则同一活动从不同入口进来会生成两套 id 导致重复
        a["id"] = make_id(a.get("title", ""), a.get("source_url", ""))
        acts.append(a)

    return acts




def _normalize_and_save(raw_acts: list[dict], default_category: str, today) -> int:
    """规范化 + 按条目实际 category 分流保存。process_category 与 PENDING_URLS 共用的收口。

    Returns:
        实际新增的活动条数（按合并前后文件长度差计算）
    """
    norm_acts = []
    for a in raw_acts:
        # 条目自身 category 优先（如开源工具会被标为 open-source）
        act_cat = a.get("category", default_category)
        norm = normalize_activity(a, act_cat)
        if norm:
            norm_acts.append(norm)

    by_cat: dict[str, list[dict]] = {}
    for a in norm_acts:
        by_cat.setdefault(a["category"], []).append(a)

    # 没有条目时仍要 merge 一次，刷新已有数据的状态
    targets = by_cat if by_cat else {default_category: []}

    added_total = 0
    for cat, acts in targets.items():
        path = DATA_DIR / cat / "activities.json"
        before = len(load_json(path) or [])
        _merge_and_save(cat, acts, today)
        added_total += len(load_json(path) or []) - before
    return added_total


def _merge_and_save(category: str, new_acts: list[dict], today) -> None:
    """规范化 + 去重 + 合并写回单个类别。"""
    old_path = DATA_DIR / category / "activities.json"
    old = load_json(old_path) or []

    # 已归档的活动不再回流：源站还挂着过期帖时会被重新抓到，直接丢弃，
    # 避免「抓回 → 归档」每天在数据里来回震荡
    dead_ids = archived_ids()
    if dead_ids:
        new_acts = [a for a in new_acts if a.get("id") not in dead_ids]

    new_acts = dedupe_within(new_acts)

    # 云厂商活动是长期活动：同 id 条目用新 end_date 刷新旧数据
    if category == "ai":
        new_by_id = {a["id"]: a for a in new_acts}
        for o in old:
            n = new_by_id.get(o.get("id"))
            if n and n.get("end_date"):
                o["end_date"] = n["end_date"]

    merged = merge(old, new_acts, today)
    save_json(old_path, merged)

    active = sum(1 for a in merged if a["status"] == "active")
    log(f"[{category}] 更新完成: 共 {len(merged)} 条（active={active}, 本次新增={len(new_acts)}）")


def process_category(category: str, subset: str = "all") -> int:
    """处理单个类别：直接收集 → 合并保存 → 标注时间。

    subset 控制抓取哪个子集（用于把请求分散到全天，避免集中压免费源网站）：
    - "all"：全部（默认，向后兼容，ai = cloud+blog，games = direct+blog）
    - "cloud"：仅云厂商（仅 ai 有效）
    - "blog"：仅博客聚合
    - "direct"：仅官方 API（仅 games 有效）
    """
    log("=" * 60)
    log(f"开始处理类别: {category}" + (f" (subset={subset})" if subset != "all" else ""))
    log(f"运行时间: {now_bj().isoformat()}")
    log("=" * 60)

    today = today_bj()

    # 1. 收集活动
    log(f"收集 [{category}] 活动 (subset={subset})...")
    raw_acts: list[dict] = []
    if category == "ai":
        # AI 板块 = 云厂商活动 + 博客聚合（博客可能产出 open-source 条目，需分流）
        if subset in ("all", "cloud"):
            raw_acts.extend(collect_cloud_activities(
                old_acts=load_json(DATA_DIR / "ai" / "activities.json") or []
            ))
        if subset in ("all", "blog"):
            raw_acts.extend(collect_blog_activities("ai"))
        # 小黑盒社区帖子（所有子模式都抓，含 ai-cloud）
        from blog_collector import collect_heybox_community
        raw_acts.extend(collect_heybox_community("ai"))
    elif category == "games":
        # 游戏板块 = Epic/Steam/GOG 喜加一 + 博客聚合
        if subset in ("all", "direct"):
            raw_acts.extend(collect_games_category(category))
        if subset in ("all", "blog"):
            raw_acts.extend(collect_blog_activities(category))
        # 小黑盒社区帖子（所有子模式都抓，含 games-direct）
        from blog_collector import collect_heybox_community
        raw_acts.extend(collect_heybox_community("games"))
    elif category == "game-discount":
        # 游戏打折 = 小黑盒分享帖（SPA需Playwright渲染）
        from blog_collector import collect_heybox_discounts, collect_heybox_community
        raw_acts = collect_heybox_discounts()
        # 小黑盒社区帖子（多分区）
        raw_acts.extend(collect_heybox_community(category))
    else:
        # open-source / drive 等其他类别：仅博客聚合 + 小黑盒社区
        # （open-source 由 ai 模式分流触发；drive 模式抓 V2EX，云优惠讨论自动分流回 ai）
        raw_acts = collect_blog_activities(category)
        # 小黑盒社区帖子（多分区）
        from blog_collector import collect_heybox_community
        raw_acts.extend(collect_heybox_community(category))

    # 2-3. 规范化 + 按实际 category 分流保存（与 PENDING_URLS 共用同一收口）
    added = _normalize_and_save(raw_acts, category, today)
    log(f"[{category}] 新增 {added} 条")

    log(f"类别 {category} 处理完成")
    return 0


def finalize() -> int:
    """整理阶段：归档过期活动 + 生成 SVG 日历 + 前端数据 + README。"""
    log("=" * 60)
    log("开始每日整理")
    log(f"运行时间: {now_bj().isoformat()}")
    log("=" * 60)

    # 处理 PENDING_URLS.md 里用户提交的网址（自动接入新源）
    log("检查 PENDING_URLS.md...")
    process_pending_urls()

    # 刷新所有活动的 status（根据当前日期重算，避免过期 status 导致 SVG 虚线不变实线）
    from dedup import refresh_status
    for cat in CATEGORIES:
        path = DATA_DIR / cat / "activities.json"
        data = load_json(path) or []
        refresh_status(data, today_bj())
        save_json(path, data)
        active = sum(1 for a in data if a["status"] == "active")
        log(f"[{cat}] 当前共 {len(data)} 条（active={active}）")

    # 过期活动归档（AGENT.md 第 20 节）：必须在生成 README/SVG/前端数据之前执行，
    # 保证已结束活动从所有产物里消失（README 只看进行中和即将开始的）
    log("归档过期活动...")
    archive_expired()

    # 生成前端数据
    log("生成前端数据...")
    generate_docs_data()

    # 生成 SVG 日历
    log("生成 SVG 日历...")
    from utils import DOCS_DATA_DIR
    svg_acts = load_json(DOCS_DATA_DIR / "activities.json") or []
    generate_svg(svg_acts)

    # 生成 README
    log("生成 README...")
    generate_readme()

    log("整理完成")
    return 0


# 子模式映射：把细粒度子模式映射到 (类别, subset)，用于把请求分散到全天
SUBMODE_MAP = {
    "ai-cloud": ("ai", "cloud"),           # 仅抓云厂商
    "ai-blog": ("ai", "blog"),             # 仅抓博客（ai 板块）
    "games-direct": ("games", "direct"),   # 仅抓 Epic/Steam/GOG 官方 API
    "games-blog": ("games", "blog"),       # 仅抓 ITAD/itch.io/Reddit
}


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "all":
        for cat in CATEGORIES:
            process_category(cat)
            time.sleep(3)
        return finalize()

    # 支持逗号分隔多模式（如 ai,drive / ai-cloud,games-direct）
    for m in [x.strip() for x in mode.split(",") if x.strip()]:
        if m == "finalize":
            rc = finalize()
        elif m in SUBMODE_MAP:
            cat, subset = SUBMODE_MAP[m]
            rc = process_category(cat, subset)
        elif m in CATEGORIES:
            rc = process_category(m)
        else:
            log(f"未知模式: {m}，可用: ai / ai-cloud / ai-blog / open-source / drive / "
                f"games / games-direct / games-blog / finalize / all")
            return 1
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
