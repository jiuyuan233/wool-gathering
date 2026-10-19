"""主收集脚本：Action 入口。

不依赖 AI 中转站，用 Reddit JSON API 直接拿结构化数据。

设计原则：
- 不同板块分时间段请求，不要频繁请求
- 每次只更新一个类别，标注更新时间
- 每天晚上全部整理一下（生成 SVG + README）

用法：
  python collect.py ai       # 只处理 AI 类
  python collect.py games    # 只处理游戏类
  python collect.py finalize # 只做整理（SVG + README）
  python collect.py all      # 全部处理（默认，手动触发用）
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from calendar_generator import generate_docs_data, generate_readme
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


CATEGORIES = ["ai", "games"]


def process_category(category: str) -> int:
    """处理单个类别：直接收集 → 合并保存 → 标注时间。"""
    log("=" * 60)
    log(f"开始处理类别: {category}")
    log(f"运行时间: {now_bj().isoformat()}")
    log("=" * 60)

    today = today_bj()

    # 1. 收集活动
    log(f"收集 [{category}] 活动...")
    if category == "ai":
        # AI 板块 = 云厂商活动（代金券/免费试用/学生优惠）
        raw_acts = collect_cloud_activities()
    else:
        # 游戏板块 = Epic/Steam/GOG 喜加一
        raw_acts = collect_games_category(category)

    # 2. 规范化（生成 id 等字段）+ 去重 + 合并写回
    new_acts = []
    for a in raw_acts:
        norm = normalize_activity(a, category)
        if norm:
            new_acts.append(norm)
    new_acts = dedupe_within(new_acts)
    old_path = DATA_DIR / category / "activities.json"
    old = load_json(old_path) or []
    merged = merge(old, new_acts, today)
    save_json(old_path, merged)

    active = sum(1 for a in merged if a["status"] == "active")
    log(f"[{category}] 更新完成: 共 {len(merged)} 条（active={active}, 本次新增={len(new_acts)}）")
    log(f"[{category}] 更新时间: {now_bj().isoformat()}")
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


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "ai":
        return process_category("ai")
    elif mode == "games":
        return process_category("games")
    elif mode == "finalize":
        return finalize()
    elif mode == "all":
        for cat in CATEGORIES:
            process_category(cat)
            time.sleep(3)
        return finalize()
    else:
        log(f"未知模式: {mode}，可用: ai / games / finalize / all")
        return 1


if __name__ == "__main__":
    sys.exit(main())
