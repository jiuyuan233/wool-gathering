"""主收集脚本：Action 入口。

设计原则（用户要求）：
- 不同板块分时间段请求，不要频繁请求
- 每次只更新一个类别，标注更新时间
- 每天晚上全部整理一下（生成 SVG + README）

用法：
  python collect.py ai       # 只处理 AI 类
  python collect.py games    # 只处理游戏类
  python collect.py finalize # 只做整理（SVG + README）
  python collect.py all      # 全部处理（默认，手动触发用）

每次只处理一个类别，上下文小（< 2000 字），不会超时。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_client import AIClient
from calendar_generator import generate_docs_data, generate_readme
from dedup import dedupe_within, merge, normalize_activity
from prompts import build_extract_messages
from sources_manager import all_source_context, load_sources
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

# 每批处理的源数量（控制上下文大小，避免中转站超时）
BATCH_SIZE = 5
# 每个源截取的字符数
PER_SOURCE_CHARS = 400
# 请求之间的间隔（秒），避免触发中转站限流
REQUEST_INTERVAL = 3


def extract_category_in_batches(
    client: AIClient,
    context: str,
    category: str,
    today_str: str,
) -> list[dict]:
    """分批处理一个类别的所有源，每次只传少量上下文。

    每批 BATCH_SIZE 个源，每源截到 PER_SOURCE_CHARS 字，
    确保上下文 < 2000 字，避免中转站超时。
    每批之间间隔 REQUEST_INTERVAL 秒，避免限流。
    """
    sources = load_sources()
    cat_sources = []
    for src in sources:
        if src.category != category:
            continue
        marker = f"### 源: {src.name}"
        i = context.find(marker)
        if i < 0:
            continue
        j = context.find("\n---\n", i)
        snippet = context[i : j if j > 0 else len(context)]
        if len(snippet) < 50:
            continue
        cat_sources.append((src.name, src.url, snippet[:PER_SOURCE_CHARS]))

    if not cat_sources:
        log(f"[{category}] 无可用源片段，跳过")
        return []

    all_activities: list[dict] = []
    total_batches = (len(cat_sources) + BATCH_SIZE - 1) // BATCH_SIZE
    log(f"[{category}] 共 {len(cat_sources)} 个源，分 {total_batches} 批处理")

    for batch_idx in range(0, len(cat_sources), BATCH_SIZE):
        batch = cat_sources[batch_idx : batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1

        parts = []
        for name, url, snippet in batch:
            parts.append(f"### 源: {name} (URL={url})\n\n{snippet}\n")
        combined = "\n---\n".join(parts)[:2000]

        log(f"[{category}] 第 {batch_num}/{total_batches} 批，{len(batch)} 个源，上下文 {len(combined)} 字")

        msgs = build_extract_messages(
            source_name=f"第{batch_num}批（{len(batch)}个源）",
            source_url="",
            category=category,
            content=combined,
            today=today_str,
        )
        try:
            data = client.chat_json(msgs, max_tokens=1000)
            acts = (data or {}).get("activities", []) if isinstance(data, dict) else []
            for a in acts:
                norm = normalize_activity(a, category)
                if norm:
                    norm["discovered_at"] = norm["discovered_at"] or now_bj().isoformat()
                    all_activities.append(norm)
            log(f"[{category}] 第 {batch_num} 批抽到 {len(acts)} 条")
        except Exception as e:
            log(f"[{category}] 第 {batch_num} 批失败: {e}", level="ERROR")

        if batch_idx + BATCH_SIZE < len(cat_sources):
            time.sleep(REQUEST_INTERVAL)

    return all_activities


def process_category(category: str) -> int:
    """处理单个类别：抓源 → 分批 AI 抽取 → 合并保存 → 标注时间。"""
    log("=" * 60)
    log(f"开始处理类别: {category}")
    log(f"运行时间: {now_bj().isoformat()}")
    log("=" * 60)

    today = today_bj()
    today_str = today.isoformat()
    client = AIClient()

    # 1. 抓种子源
    log("抓取种子源...")
    context = all_source_context()

    # 2. 分批 AI 抽取
    log(f"分批 AI 抽取 [{category}]")
    new_acts = extract_category_in_batches(client, context, category, today_str)

    # 3. 合并去重 + 写回
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
        # 全部处理（手动触发用）
        for cat in CATEGORIES:
            process_category(cat)
            time.sleep(REQUEST_INTERVAL)
        return finalize()
    else:
        log(f"未知模式: {mode}，可用: ai / games / finalize / all")
        return 1


if __name__ == "__main__":
    sys.exit(main())
