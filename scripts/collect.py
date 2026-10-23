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
    now_bj,
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



def archive_expired() -> int:
    """把过期活动按月归档到 docs/archive/YYYY-MM.md，从 activities.json 移除。"""
    from datetime import date
    from collections import defaultdict
    today = date.today().isoformat()
    archive_dir = DATA_DIR.parent / "docs" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    by_month = defaultdict(list)
    archived_count = 0
    for cat in CATEGORIES:
        path = DATA_DIR / cat / "activities.json"
        acts = load_json(path) or []
        kept = []
        for a in acts:
            status = a.get("status", "")
            end = a.get("end_date", "")
            if status == "ended" or (end and end < today):
                month = (end or a.get("start_date", "") or "unknown")[:7]
                by_month[month].append((cat, a))
                archived_count += 1
            else:
                kept.append(a)
        if len(kept) < len(acts):
            save_json(path, kept)
    if archived_count == 0:
        log("无过期活动需归档")
        return 0
    cat_names = {"ai":"AI/云服务","open-source":"开源工具","drive":"开车线报","games":"游戏喜加一","shopping":"购物优惠","video-vip":"视频会员","netdisk-vip":"网盘会员","game-discount":"游戏打折"}
    cat_emojis = {"ai":"🤖","open-source":"🔓","drive":"🚗","games":"🎮","shopping":"🛒","video-vip":"📺","netdisk-vip":"💾","game-discount":"🏷️"}
    for month, items in sorted(by_month.items()):
        archive_path = archive_dir / f"{month}.md"
        by_cat = defaultdict(list)
        for cat, act in items:
            by_cat[cat].append(act)
        lines = [f"# {month[:4]}年{int(month[5:7])}月归档", "", "> 已过期的活动归档，从主页面移除。", ""]
        for cat in CATEGORIES:
            cat_acts = by_cat.get(cat, [])
            if not cat_acts:
                continue
            lines.append(f"## {cat_emojis.get(cat,'📋')} {cat_names.get(cat,cat)}")
            lines.append("")
            lines.append("| 活动 | 福利 | 时间 | 来源 |")
            lines.append("|------|------|------|------|")
            for a in cat_acts:
                title = a.get("title", "").replace("|", "\|")
                value = (a.get("value") or "—").replace("|", "\|")
                start = a.get("start_date", "?")
                end = a.get("end_date", "?")
                url = a.get("source_url", "") or a.get("claim_url", "")
                link = f"[链接]({url})" if url else "—"
                lines.append(f"| {title} | {value} | {start} ~ {end} | {link} |")
            lines.append("")
        archive_path.write_text("\n".join(lines), encoding="utf-8")
        log(f"归档 {month}: {len(items)} 条")
    log(f"归档完成: 共 {archived_count} 条")
    return archived_count


def process_pending_urls() -> int:
    """处理 PENDING_URLS.md 里用户提交的网址。

    读取「待处理」区的网址，添加到 data/sources.json，
    然后把已处理的移到「已处理」区并附上结果。

    Returns:
        处理的网址数量
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

    # 提取「待处理」区的网址行
    url_pattern = re.compile(r'^(https?://\S+)(?:\s*#\s*(\w[\w-]*))?\s*$')
    urls_to_process = []
    for line in todo_section.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--") or stripped.startswith(">") or stripped.startswith("#"):
            continue
        m = url_pattern.match(stripped)
        if m:
            urls_to_process.append((m.group(1), m.group(2), stripped))

    if not urls_to_process:
        log("PENDING_URLS.md 无待处理网址")
        return 0

    log(f"PENDING_URLS.md: 发现 {len(urls_to_process)} 个待处理网址")

    # 读取 sources.json
    sources_path = DATA_DIR / "sources.json"
    all_sources = load_json(sources_path) or []
    existing_urls = {s.get("url", "") for s in all_sources}

    today = now_bj().strftime("%Y-%m-%d")
    processed = []
    new_count = 0

    from urllib.parse import urlparse
    for url, cat_hint, original_line in urls_to_process:
        # 判断分类：用户注释优先
        if cat_hint and cat_hint in CATEGORIES:
            category = cat_hint
            _, src_type = _guess_category_from_url(url)
        else:
            category, src_type = _guess_category_from_url(url)

        # 去重
        if url in existing_urls:
            processed.append(f"- [{today}] {url} → {category}，重复（sources.json 已有），跳过")
            log(f"  {url} → {category}，重复，跳过")
            continue

        # 推断 name
        domain = urlparse(url).netloc or url
        name = domain.replace("www.", "")[:30]

        # 添加到 sources
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
        processed.append(f"- [{today}] {url} → {category}，已添加到 sources.json")
        log(f"  {url} → {category}（{src_type}），已添加")

    # 保存 sources.json
    if new_count > 0:
        save_json(sources_path, all_sources)
        log(f"sources.json: 新增 {new_count} 个源（总计 {len(all_sources)}）")

        # 抓取新源内容（让用户提交的URL进日历）
        cats_to_fetch = set()
        for url2, cat_hint2, _ in urls_to_process:
            if url2 in existing_urls and cat_hint2 and cat_hint2 in CATEGORIES:
                cats_to_fetch.add(cat_hint2)
            elif url2 in existing_urls:
                cat2, _ = _guess_category_from_url(url2)
                cats_to_fetch.add(cat2)
        for cat in cats_to_fetch:
            log(f"  抓取 [{cat}] 新源内容...")
            try:
                process_category(cat)
            except Exception as e:
                log(f"  抓取 [{cat}] 失败: {e}", level="WARN")

    # 更新 PENDING_URLS.md：删除已处理行，在已处理区追加结果
    new_todo_lines = []
    for line in todo_section.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("<!--") and not stripped.startswith(">") and not stripped.startswith("#"):
            if url_pattern.match(stripped):
                continue  # 跳过已处理的网址行
        new_todo_lines.append(line)

    # 在已处理区的注释行前插入结果
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
    log(f"PENDING_URLS.md: 已处理 {len(processed)} 个网址，{new_count} 个新增源")

    return len(processed)



def _merge_and_save(category: str, new_acts: list[dict], today) -> None:
    """规范化 + 去重 + 合并写回单个类别。"""
    old_path = DATA_DIR / category / "activities.json"
    old = load_json(old_path) or []

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
    elif category == "games":
        # 游戏板块 = Epic/Steam/GOG 喜加一 + 博客聚合
        if subset in ("all", "direct"):
            raw_acts.extend(collect_games_category(category))
        if subset in ("all", "blog"):
            raw_acts.extend(collect_blog_activities(category))
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

    # 2. 规范化（生成 id 等字段）
    norm_acts = []
    for a in raw_acts:
        # 条目自身 category 优先（开源工具会被标为 open-source）
        act_cat = a.get("category", category)
        norm = normalize_activity(a, act_cat)
        if norm:
            norm_acts.append(norm)

    # 3. 按实际 category 分流保存
    by_cat: dict[str, list[dict]] = {}
    for a in norm_acts:
        by_cat.setdefault(a["category"], []).append(a)

    if not by_cat:
        # 没有条目，仍要 merge 保存以刷新状态
        _merge_and_save(category, [], today)
    elif len(by_cat) == 1 and list(by_cat)[0] == category:
        _merge_and_save(category, list(by_cat.values())[0], today)
    else:
        # 多类别分流（如 ai 模式产出 ai + open-source）
        for cat, acts in by_cat.items():
            _merge_and_save(cat, acts, today)

    log(f"类别 {category} 处理完成")
    return 0


def finalize() -> int:
    """整理阶段：生成 SVG 日历 + 前端数据 + README。"""
    log("=" * 60)
    log("开始每日整理")
    log(f"运行时间: {now_bj().isoformat()}")
    log("=" * 60)

    # 处理 PENDING_URLS.md 里用户提交的网址（自动接入新源）
    log("检查 PENDING_URLS.md...")
    process_pending_urls()

    # 统计各类别数据
    for cat in CATEGORIES:
        data = load_json(DATA_DIR / cat / "activities.json") or []
        active = sum(1 for a in data if a["status"] == "active")
        log(f"[{cat}] 当前共 {len(data)} 条（active={active}）")

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
