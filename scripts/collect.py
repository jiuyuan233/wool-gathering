"""主收集脚本：Action 入口。

流程：
1. 抓所有种子源 → 拼成上下文
2. 调 AI 抽取活动（按分类，用 prompts.py 里的提示词）
3. AI 联网搜索补充新活动（混合模式）
4. 合并去重 + 刷新状态
5. 写回 data/{ai,games}/activities.json
6. 生成 docs/calendar.svg（README 嵌入的日历）
7. 生成 docs/data/*.json（前端数据，可选）
8. 生成 README.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_client import AIClient
from calendar_generator import generate_docs_data, generate_readme
from dedup import dedupe_within, merge, normalize_activity
from prompts import build_extract_messages, build_search_messages
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

# 联网搜索关键词（混合模式补充发现）
# 这些词会交给 AI 让它联网搜，发现种子源之外的新活动
SEARCH_KEYWORDS = {
    "ai": [
        "AI 代金券 免费领取 2026",
        "大模型 免费额度 新用户注册",
        "云厂商 AI 算力 免费试用 活动",
        "GPU 免费算力 活动 2026",
        "华为云 AI 代金券",
        "阿里云 通义千问 免费额度",
        "HuggingFace free inference Spaces",
        "Google AI Studio free Gemini",
        "Groq free tier API",
    ],
    "games": [
        "Epic 免费游戏 本周",
        "Epic Games free games this week",
        "Steam 限免 游戏 本周",
        "Steam 100% off free game",
        "GOG 限时免费 游戏",
        "GOG free game giveaway",
        "Humble Bundle 限时免费",
        "itch.io 限时免费 游戏",
        "Amazon Prime Gaming free games",
        "Ubisoft free game On the House",
        "EA free game giveaway",
        "Reddit free games",
        "喜加一 限时免费 游戏",
        "游戏 限免 喜加一 2026",
        "手游 公测 礼包 免费领",
        "PlayStation 会员免费游戏",
        "Xbox Games with Gold free",
    ],
}


def extract_from_sources(client: AIClient, context: str) -> dict[str, list[dict]]:
    """从种子源上下文里抽取活动，按分类分桶。

    用 prompts.py 里的 system prompt + extract 模板组装 messages，
    这样抽取规则、字段要求、什么算薅羊毛都由 prompts.py 统一控制。
    """
    if not context:
        log("种子源上下文为空，跳过抽取")
        return {c: [] for c in CATEGORIES}

    sources = load_sources()
    by_cat: dict[str, list[dict]] = {c: [] for c in CATEGORIES}
    today_str = today_bj().isoformat()

    for src in sources:
        cat = src.category if src.category in CATEGORIES else None
        if cat is None:
            continue  # mixed 留给搜索阶段
        # 上下文里找对应片段
        marker = f"### 源: {src.name}"
        i = context.find(marker)
        if i < 0:
            continue
        j = context.find("\n---\n", i)
        snippet = context[i : j if j > 0 else len(context)]
        if len(snippet) < 50:
            continue

        # 用 prompts.py 组装 messages（含完整抽取规则）
        msgs = build_extract_messages(
            source_name=src.name,
            source_url=src.url,
            category=cat,
            content=snippet[:6000],
            today=today_str,
        )
        try:
            data = client.chat_json(msgs, max_tokens=2500)
            acts = (data or {}).get("activities", []) if isinstance(data, dict) else []
            for a in acts:
                norm = normalize_activity(a, cat)
                if norm:
                    norm["discovered_at"] = norm["discovered_at"] or now_bj().isoformat()
                    by_cat[cat].append(norm)
            log(f"[{cat}] 从 {src.name} 抽到 {len(acts)} 条")
        except Exception as e:
            log(f"AI 抽取失败 [{src.name}]: {e}", level="ERROR")

    return by_cat


def search_new_activities(client: AIClient) -> dict[str, list[dict]]:
    """混合模式：让 AI 联网搜索补充新活动。

    用 prompts.py 的 search 模板组装 messages。
    依赖中转站支持联网搜索（部分中转站有 web_search 工具）。
    不支持也不影响主流程——种子源抽取已经能产出数据。
    """
    by_cat: dict[str, list[dict]] = {c: [] for c in CATEGORIES}
    today_str = today_bj().isoformat()

    for cat, keywords in SEARCH_KEYWORDS.items():
        for kw in keywords:
            msgs = build_search_messages(keyword=kw, category=cat, today=today_str)
            try:
                data = client.chat_json(msgs, max_tokens=2000)
                acts = (data or {}).get("activities", []) if isinstance(data, dict) else []
                for a in acts:
                    norm = normalize_activity(a, cat)
                    if norm:
                        norm["discovered_at"] = norm["discovered_at"] or now_bj().isoformat()
                        by_cat[cat].append(norm)
                log(f"[{cat}] 联网搜索 '{kw}' 抽到 {len(acts)} 条")
            except Exception as e:
                log(f"联网搜索失败 [{kw}]: {e}", level="ERROR")
    return by_cat


def main() -> int:
    log("=" * 60)
    log("开始每日薅羊毛情报收集")
    log("=" * 60)

    today = today_bj()
    client = AIClient()

    # 1. 抓种子源
    log("阶段 1/6：抓取种子源")
    context = all_source_context()

    # 2. 从种子源抽取
    log("阶段 2/6：AI 抽取种子源活动")
    from_sources = extract_from_sources(client, context)

    # 3. 联网搜索补充
    log("阶段 3/6：AI 联网搜索补充")
    from_search = search_new_activities(client)

    # 4. 合并去重 + 写回
    log("阶段 4/6：合并去重并写回 data/")
    for cat in CATEGORIES:
        new = dedupe_within(from_sources[cat] + from_search[cat])
        old_path = DATA_DIR / cat / "activities.json"
        old = load_json(old_path) or []
        merged = merge(old, new, today)
        save_json(old_path, merged)
        active = sum(1 for a in merged if a["status"] == "active")
        log(f"[{cat}] 合并后共 {len(merged)} 条（active={active}, 新增={len(new)}）")

    # 5. 生成 SVG 日历 + 前端数据
    log("阶段 5/6：生成 SVG 日历与前端数据")
    all_acts = []
    for cat in CATEGORIES:
        all_acts.extend(load_json(DATA_DIR / cat / "activities.json") or [])
    # 先生成 docs_data（会给每条加 progress/days_left 字段，SVG 也要用）
    generate_docs_data()
    # 重新读带 progress 字段的数据给 SVG
    from utils import DOCS_DATA_DIR
    svg_acts = load_json(DOCS_DATA_DIR / "activities.json") or []
    generate_svg(svg_acts)

    # 6. 生成 README（嵌入 SVG）
    log("阶段 6/6：生成 README")
    generate_readme()

    log("收集完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
