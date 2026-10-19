"""生成 Pages 前端数据 + README 表格视图。

- docs/data/activities.json：前端读取的全量数据
- docs/data/meta.json：生成时间、统计
- README.md：仓库主页表格视图（GitHub 原生 MD 渲染）
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (
    DATA_DIR,
    DOCS_DATA_DIR,
    REPO_ROOT,
    load_json,
    log,
    now_bj,
    parse_date,
    save_json,
    today_bj,
)


CATEGORIES = ["ai", "games"]
CAT_LABEL = {"ai": "AI 类", "games": "游戏类"}
CAT_EMOJI = {"ai": "🤖", "games": "🎮"}  # README 里用，前端不用


def _all_activities() -> list[dict]:
    out = []
    for cat in CATEGORIES:
        data = load_json(DATA_DIR / cat / "activities.json") or []
        out.extend(data)
    return out


def generate_docs_data() -> None:
    """生成前端要读的 JSON。"""
    acts = _all_activities()
    today = today_bj()
    # 给每条加 progress 字段，前端不用再算
    for a in acts:
        s = parse_date(a.get("start_date"))
        e = parse_date(a.get("end_date"))
        if s and e and e >= s:
            total = (e - s).days + 1
            passed = max(0, (today - s).days + 1)
            a["progress_pct"] = round(min(100, max(0, passed / total * 100)), 1)
            a["total_days"] = total
            a["days_left"] = max(0, (e - today).days)
        else:
            a["progress_pct"] = 100 if a["status"] == "active" else 0
            a["total_days"] = None
            a["days_left"] = None

    save_json(DOCS_DATA_DIR / "activities.json", acts)
    import os
    meta = {
        "generated_at": now_bj().isoformat(),
        "today": today.isoformat(),
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "total": len(acts),
        "by_category": {
            cat: {
                "total": sum(1 for a in acts if a["category"] == cat),
                "active": sum(
                    1 for a in acts if a["category"] == cat and a["status"] == "active"
                ),
                "upcoming": sum(
                    1 for a in acts if a["category"] == cat and a["status"] == "upcoming"
                ),
                "ended": sum(
                    1 for a in acts if a["category"] == cat and a["status"] == "ended"
                ),
            }
            for cat in CATEGORIES
        },
    }
    save_json(DOCS_DATA_DIR / "meta.json", meta)
    log(f"已生成 docs/data/activities.json ({len(acts)} 条) 和 meta.json")


def _md_table(acts: list[dict]) -> str:
    if not acts:
        return "_暂无活动_\n"
    lines = [
        "| 状态 | 活动 | 福利 | 时间 | 剩余 | 领取 |",
        "|------|------|------|------|------|------|",
    ]
    status_icon = {"active": "🟢", "upcoming": "🟡", "ended": "⚫"}
    for a in acts:
        icon = status_icon.get(a["status"], "⚪")
        title = a["title"].replace("|", "\\|")
        value = (a.get("value") or "—").replace("|", "\\|")
        start = a.get("start_date") or "?"
        end = a.get("end_date") or "?"
        time_str = f"{start} ~ {end}"
        dl = a.get("days_left")
        left = f"{dl} 天" if dl is not None else "—"
        url = a.get("claim_url") or a.get("source_url") or ""
        link = f"[领取]({url})" if url else "—"
        lines.append(f"| {icon} | {title} | {value} | {time_str} | {left} | {link} |")
    return "\n".join(lines) + "\n"


README_TEMPLATE = REPO_ROOT / "scripts" / "readme_template.md"


def _guess_pages_url() -> str:
    """从环境变量拿仓库名拼 Pages URL。"""
    import os
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"
    return "https://<your-username>.github.io/wool-gathering/"


def generate_readme() -> None:
    """读取 scripts/readme_template.md，替换占位符后写入 README.md。

    模板里用 {{PAGES_URL}} / {{GENERATED_AT}} / {{ACTIVE_COUNT}}
    / {{UPCOMING_COUNT}} / {{TOTAL_COUNT}} / {{SECTIONS}} 标记动态部分。
    这样配置指南等静态内容维护在模板里，不会被脚本逻辑冲掉。
    """
    acts = _all_activities()
    active = [a for a in acts if a["status"] == "active"]
    upcoming = [a for a in acts if a["status"] == "upcoming"]

    sections = []
    for cat in CATEGORIES:
        cat_acts = [a for a in acts if a["category"] == cat]
        sections.append(
            f"### {CAT_EMOJI[cat]} {CAT_LABEL[cat]}\n\n"
            + _md_table(cat_acts)
        )
    body = "\n".join(sections)

    if not README_TEMPLATE.exists():
        log(f"README 模板不存在: {README_TEMPLATE}", level="ERROR")
        return

    template = README_TEMPLATE.read_text(encoding="utf-8")
    pages_url = _guess_pages_url()
    readme = (
        template
        .replace("{{PAGES_URL}}", pages_url)
        .replace("{{GENERATED_AT}}", now_bj().strftime("%Y-%m-%d %H:%M"))
        .replace("{{ACTIVE_COUNT}}", str(len(active)))
        .replace("{{UPCOMING_COUNT}}", str(len(upcoming)))
        .replace("{{TOTAL_COUNT}}", str(len(acts)))
        .replace("{{SECTIONS}}", body)
    )
    (REPO_ROOT / "README.md").write_text(readme, encoding="utf-8")
    log("已生成 README.md")


if __name__ == "__main__":
    generate_docs_data()
    generate_readme()
