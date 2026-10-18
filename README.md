# 🐑 薅羊毛情报站

> 全网 AI / 游戏 免费福利活动自动收集，每日由 GitHub Actions + AI 更新。

## 🚀 快速开始

### 1. 配置 AI Secrets

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**，添加三个：

| Secret 名 | 值 | 示例 |
|-----------|-----|------|
| `AI_BASE_URL` | AI 中转站地址（OpenAI 兼容协议） | `https://api.deepseek.com/v1` |
| `AI_API_KEY` | 中转站 API Key | `sk-xxxxxxxx` |
| `AI_MODEL` | 模型名 | `deepseek-chat` |

**推荐免费/低价中转站**（自行搜索"OpenAI 中转站"）：
- DeepSeek 官方：`https://api.deepseek.com/v1` + `deepseek-chat`
- 智谱 BigModel：`https://open.bigmodel.cn/api/paas/v4` + `glm-4-flash`
- 任意 OpenAI 兼容中转站均可

### 2. 启用 GitHub Pages

进入 **Settings → Pages → Build and deployment**：
- Source: **GitHub Actions**
- （workflow 已配置好，无需额外操作）

### 3. 手动触发首次运行

进入 **Actions → Daily Collect → Run workflow**，等运行完成后：
- 仓库主页 `README.md` 会显示活动表格
- Pages 站点（`https://jiuyuan233.github.io/wool-gathering/`）会显示日历视图

之后每天北京时间 09:00 自动运行。

## 📁 仓库结构

```
wool-gathering/
├── .github/workflows/         # Actions：每日收集 + Pages 部署
│   └── daily-collect.yml
├── data/
│   ├── ai/activities.json     # AI 类活动数据（自动生成）
│   ├── games/activities.json  # 游戏类活动数据（自动生成）
│   └── sources.json           # 种子源列表（可手动维护）
├── scripts/                   # Python 收集脚本
│   ├── ai_client.py           # AI 中转站客户端
│   ├── collect.py             # 主入口
│   ├── sources_manager.py     # 种子源抓取
│   ├── dedup.py               # 去重合并
│   ├── calendar_generator.py  # 日历/README 生成
│   └── utils.py
├── docs/                      # GitHub Pages 站点
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js
│   └── data/                  # 前端读取的 JSON
└── README.md                  # 本文件（部分由脚本自动生成）
```

## ➕ 添加新的种子源

编辑 `data/sources.json`，加一条：

```json
{
  "name": "华为云开发者社区",
  "url": "https://developer.huaweicloud.com/...",
  "category": "ai",
  "type": "html",
  "enabled": true,
  "note": "AI 代金券活动页"
}
```

字段说明：
- `category`：`ai` / `games` / `mixed`
- `type`：`html` / `rss` / `api` / `manual`
- `enabled`：`false` 可临时禁用

提交后下次 Action 运行即生效。

## 🔧 工作原理

1. **每日定时**：GitHub Actions 在北京时间每天 09:00 自动运行
2. **种子源抓取**：从 `data/sources.json` 列出的目标网站抓取页面
3. **AI 抽取**：调用 AI 中转站（OpenAI 兼容协议）从页面内容里抽取结构化活动信息
4. **联网搜索补充**：AI 用预设关键词联网搜索，发现种子源之外的新活动
5. **去重合并**：按稳定 ID 去重，保留已有字段，刷新状态
6. **生成产物**：更新 `data/{ai,games}/activities.json` + `docs/data/*.json` + README 表格

## 📊 活动数据结构

每条活动 JSON：

```json
{
  "id": "huaweicloud-ai-200-abc123",
  "title": "华为云 AI 200 代金券",
  "category": "ai",
  "source_url": "https://...",
  "claim_url": "https://...",
  "start_date": "2026-10-18",
  "end_date": "2026-10-25",
  "value": "200 元代金券",
  "requirements": ["实名认证", "新用户"],
  "description": "新用户专享，可叠加免费额度",
  "tags": ["代金券", "华为云", "AI"],
  "discovered_at": "2026-10-18T09:00:00+08:00",
  "last_seen": "2026-10-18",
  "status": "active"
}
```

`status` 由起止日期每天自动重算：`active` / `upcoming` / `ended`。

## 📅 日历视图

GitHub Pages 站点顶部有一个时间轴模块：
- 每个活动一条横条，长度对应持续时间
- 进度条显示当前完成度
- 红色竖线标记"今天"
- 已结束的活动半透明，未开始的活动虚线边框
- 支持按分类、状态筛选

## 🛠 本地调试

```bash
pip install -r scripts/requirements.txt
export AI_BASE_URL="https://api.deepseek.com/v1"
export AI_API_KEY="sk-xxx"
export AI_MODEL="deepseek-chat"
cd scripts && python collect.py
```

## ⚠️ 免责声明

- 本项目仅收集公开活动信息，不参与任何活动分发
- 领取请前往活动官方页面，遵守各平台规则
- AI 抽取的信息可能存在误差，请以活动官方页面为准
- 不对活动的真实性、可用性做任何保证

## 📜 License

MIT
