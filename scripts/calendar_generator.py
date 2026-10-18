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
    meta = {
        "generated_at": now_bj().isoformat(),
        "today": today.isoformat(),
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


def generate_readme() -> None:
    """生成 README.md（保留首尾固定段，中间表格动态生成）。"""
    acts = _all_activities()
    today = today_bj()
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

    readme = f"""# 🐑 薅羊毛情报站

> 全网 AI / 游戏 免费福利活动自动收集，每日由 GitHub Actions + AI 更新。
> 顶部日历视图见 **[GitHub Pages 主页]({{PAGES_URL}})**。

## 📊 今日概况

- 更新时间：{now_bj().strftime("%Y-%m-%d %H:%M")} 北京时间
- 进行中活动：**{len(active)}** 个 ｜ 即将开始：**{len(upcoming)}** 个 ｜ 历史收录：**{len(acts)}** 个

## 📅 活动日历（进度条视图）

完整可视化日历请访问：**{PAGES_URL_PLACEHOLDER}**

下面是 Markdown 表格速览（GitHub 原生渲染）：

## 🗂 分类活动

{body}

## 🔧 工作原理

1. **每日定时**：GitHub Actions 在北京时间每天 09:00 自动运行
2. **种子源抓取**：从 `data/sources.json` 列出的目标网站抓取页面
3. **AI 抽取**：调用 AI 中转站（OpenAI 兼容协议）从页面内容里抽取结构化活动信息
4. **联网搜索补充**：AI 用预设关键词联网搜索，发现种子源之外的新活动
5. **去重合并**：按稳定 ID 去重，保留已有字段，刷新状态
6. **生成产物**：更新 `data/{{ai,games}}/activities.json` + `docs/data/*.json` + 本 README

## 📁 仓库结构

```
wool-gathering/
├── .github/workflows/      # Actions：每日收集 + Pages 部署
├── data/
│   ├── ai/activities.json  # AI 类活动数据
│   ├── games/activities.json  # 游戏类活动数据
│   └── sources.json        # 种子源列表（可手动维护）
├── scripts/                # Python 收集脚本
├── docs/                   # GitHub Pages 站点（日历视图）
└── README.md               # 本文件（自动生成）
```

## ➕ 添加新的种子源

编辑 `data/sources.json`，加一条：

```json
{{
  "name": "华为云开发者社区",
  "url": "https://developer.huaweicloud.com/...",
  "category": "ai",
  "type": "html",
  "enabled": true,
  "note": "AI 代金券活动页"
}}
```

`category` 可选 `ai` / `games` / `mixed`。提交后下次 Action 运行即生效。

## 🔑 配置 Secrets

在仓库 Settings → Secrets and variables → Actions 添加：

| Secret | 说明 |
|--------|------|
| `AI_BASE_URL` | AI 中转站地址（OpenAI 兼容），如 `https://api.deepseek.com/v1` |
| `AI_API_KEY` | 中转站 API Key |
| `AI_MODEL` | 模型名，如 `deepseek-chat` |

## 📜 License

MIT
"""
    # 替换 Pages URL 占位
    pages_url = _guess_pages_url()
    readme = readme.replace("{PAGES_URL}", pages_url).replace(PAGES_URL_PLACEHOLDER, pages_url)
    (REPO_ROOT / "README.md").write_text(readme, encoding="utf-8")
    log("已生成 README.md")


PAGES_URL_PLACEHOLDER = "__PAGES_URL__"


def _guess_pages_url() -> str:
    """从环境变量拿仓库名拼 Pages URL。"""
    import os
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"
    return "https://<your-username>.github.io/wool-gathering/"


if __name__ == "__main__":
    generate_docs_data()
    generate_readme()
