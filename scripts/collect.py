"""主收集脚本：Action 入口。

流程：
1. 抓所有种子源 → 拼成上下文
2. 调 AI 抽取活动（按分类）
3. AI 联网搜索补充新活动（混合模式）
4. 合并去重 + 刷新状态
5. 写回 data/{ai,games}/activities.json
6. 生成 docs/data/activities.json 供 Pages 前端
7. 生成 README.md 表格视图
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 让 scripts/ 目录内 import 不用改 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_client import AIClient
from calendar_generator import generate_docs_data, generate_readme
from dedup import dedupe_within, merge, normalize_activity
from sources_manager import all_source_context, load_sources
from utils import (
    DATA_DIR,
    log,
    now_bj,
    save_json,
    today_bj,
)


CATEGORIES = ["ai", "games"]

# AI 抽取用的 schema 提示
SCHEMA_HINT = """{
  "activities": [
    {
      "title": "活动标题",
      "source_url": "活动信息页 URL",
      "claim_url": "实际领取/参与 URL（若与 source_url 相同可省略）",
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "value": "可薅到的具体福利，如 200 元代金券 / 30 天会员",
      "requirements": ["领取条件1", "领取条件2"],
      "description": "一句话描述",
      "tags": ["标签1", "标签2"]
    }
  ]
}"""

# 联网搜索关键词（混合模式补充发现）
SEARCH_KEYWORDS = {
    "ai": [
        "AI 代金券 免费领取 2026",
        "大模型 免费额度 新用户",
        "云厂商 AI 算线 免费试用",
        "GPU 免费算力 活动",
    ],
    "games": [
        "游戏 免费领取 限时活动",
        "Epic 免费游戏 本周",
        "Steam 限免 游戏",
        "手游 公测 礼包 免费领",
    ],
}


def extract_from_sources(client: AIClient, context: str) -> dict[str, list[dict]]:
    """从种子源上下文里抽取活动，按分类分桶。"""
    if not context:
        log("种子源上下文为空，跳过抽取")
        return {c: [] for c in CATEGORIES}

    sources = load_sources()
    by_cat: dict[str, list[dict]] = {c: [] for c in CATEGORIES}
    # 把每个源按其 category 单独抽，避免一次塞太多
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

        msgs = [
            {
                "role": "user",
                "content": (
                    f"从下面这个网页内容里抽取所有【{cat} 类】薅羊毛/免费福利活动。"
                    "只抽取真实存在的活动，不要编造。"
                    "如果页面里没有活动，返回 {\"activities\": []}。\n\n"
                    f"网页内容：\n{snippet[:6000]}"
                ),
            }
        ]
        try:
            data = client.chat_json(msgs, schema_hint=SCHEMA_HINT, max_tokens=2500)
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

    依赖中转站支持 search（部分中转站有 web_search 工具）。
    不支持也不影响主流程——种子源抽取已经能产出数据。
    """
    by_cat: dict[str, list[dict]] = {c: [] for c in CATEGORIES}
    for cat, keywords in SEARCH_KEYWORDS.items():
        for kw in keywords:
            msgs = [
                {
                    "role": "user",
                    "content": (
                        f"请联网搜索关键词：{kw}\n"
                        f"找出当前正在进行或即将开始的【{cat} 类】薅羊毛/免费福利活动。"
                        "每个活动必须给出可访问的 source_url。"
                        "如果搜索功能不可用，直接返回 {\"activities\": []}。"
                    ),
                }
            ]
            try:
                data = client.chat_json(msgs, schema_hint=SCHEMA_HINT, max_tokens=2000)
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
    log("阶段 1/5：抓取种子源")
    context = all_source_context()

    # 2. 从种子源抽取
    log("阶段 2/5：AI 抽取种子源活动")
    from_sources = extract_from_sources(client, context)

    # 3. 联网搜索补充
    log("阶段 3/5：AI 联网搜索补充")
    from_search = search_new_activities(client)

    # 4. 合并去重 + 写回
    log("阶段 4/5：合并去重并写回 data/")
    for cat in CATEGORIES:
        new = dedupe_within(from_sources[cat] + from_search[cat])
        old_path = DATA_DIR / cat / "activities.json"
        from utils import load_json
        old = load_json(old_path) or []
        merged = merge(old, new, today)
        save_json(old_path, merged)
        active = sum(1 for a in merged if a["status"] == "active")
        log(f"[{cat}] 合并后共 {len(merged)} 条（active={active}, 新增={len(new)}）")

    # 5. 生成 Pages 数据 + README
    log("阶段 5/5：生成 Pages 数据与 README")
    generate_docs_data()
    generate_readme()

    log("收集完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
