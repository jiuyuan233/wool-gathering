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
        from blog_collector import collect_heybox_discounts
        raw_acts = collect_heybox_discounts()
    else:
        # open-source / drive 等其他类别：仅博客聚合
        # （open-source 由 ai 模式分流触发；drive 模式抓 V2EX，云优惠讨论自动分流回 ai）
        raw_acts = collect_blog_activities(category)

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
