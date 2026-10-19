# 🐑 薅羊毛情报站

> 全网 **AI / 游戏** 免费福利活动自动收集 · 每日由 GitHub Actions + AI 更新

---

## 🔗 社区整理的免费资源

> 社区维护的免费资源聚合项目，按方向分类，可作为日常薅羊毛的补充信息源。

### AI / LLM 免费 API

| 项目 | 简介 |
|------|------|
| [AIPMAndy/FreeToken](https://github.com/AIPMAndy/FreeToken) | 收集各类免费 AI API Token 获取方法 |
| [mnfst/awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis) ⭐10.6k | 永久免费 LLM API 列表 |
| [open-free-llm-api/awesome-freellm-apis](https://github.com/open-free-llm-api/awesome-freellm-apis) ⭐4.4k | 134+ 免费 LLM API & AI API Key，40+ 厂商 |
| [guihuashaoxiang/FreeLLM-API-KeyHub](https://github.com/guihuashaoxiang/FreeLLM-API-KeyHub) | 🇨🇳 国内免费大语言模型 API 资源与接入指南 |

### 云服务 / SaaS 免费层

| 项目 | 简介 |
|------|------|
| [ripienaar/free-for-dev](https://github.com/ripienaar/free-for-dev) ⭐139.8k | SaaS/PaaS/IaaS 免费层列表 |
| [255kb/stack-on-a-budget](https://github.com/255kb/stack-on-a-budget) ⭐12.5k | 对开发者预算友好的免费层服务集合 |

### 开发者创业信用额度

| 项目 | 简介 |
|------|------|
| [dakshshah96/awesome-startup-credits](https://github.com/dakshshah96/awesome-startup-credits) ⭐3k | 创业公司免费/折扣计划合集 |
| [t3-sh/cloudcredits.io](https://github.com/t3-sh/cloudcredits.io) | 云/SaaS/工具的免费信用额度与折扣列表 |

### 游戏免费聚合

| 项目 | 简介 |
|------|------|
| [eikowagenknecht/lootscraper](https://github.com/eikowagenknecht/lootscraper) ⭐320 | 免费 game/loot offers 的 RSS feeds（Steam/Epic/GOG/itchio） |
| [DoSpamu/free-games-claimer](https://github.com/DoSpamu/free-games-claimer) | 自动领取 Epic/Prime/GOG/Steam 免费游戏 |

### 自托管开源软件

| 项目 | 简介 |
|------|------|
| [awesome-selfhosted/awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) ⭐328k | 可自托管的免费网络服务与 Web 应用列表 |

### ChatGPT API 工具

| 项目 | 简介 |
|------|------|
| [reorx/awesome-chatgpt-api](https://github.com/reorx/awesome-chatgpt-api) ⭐6.4k | 使用 ChatGPT API 的应用与工具合集 |

---

## 📅 活动时间轴

![活动日历](docs/calendar.svg)

> 每条横条 = 一个活动的持续时间 ｜ 红色虚线 = 今天 ｜ 白色进度填充 = 当前完成度
> ｜ 半透明 = 已结束 ｜ 虚线边框 = 未开始 ｜ 🟢进行中 🟡未开始 ⚫已结束

---

## 📊 今日概况

- 更新时间：**{{GENERATED_AT}}** 北京时间
- 进行中：**{{ACTIVE_COUNT}}** 个 ｜ 即将开始：**{{UPCOMING_COUNT}}** 个 ｜ 历史收录：**{{TOTAL_COUNT}}** 个

---

## 🗂 分类活动

{{SECTIONS}}

---

## 🚀 快速开始（2 步跑通）

### 第 1 步：配置 AI API Key Secret

workflow 已默认配置 ChatAnywhere 中转站 + `deepseek-v3-2` 弱模型（在 `.github/workflows/daily-collect.yml` 的 env 里），**只需配 1 个 Secret**：

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**：
- Name：`AI_API_KEY`
- Value：你的 ChatAnywhere API Key（形如 `sk-xxxxxxxx`，去 [chatanywhere](https://chatanywhere.top) 注册免费领取）

> ChatAnywhere 免费版：每周 50000 点 + 每天 100 次请求，用 `deepseek-v3-2` 弱模型省额度，每次跑约调 AI 30-50 次基本够。

**想换其他中转站？** 编辑 workflow 的 env 改 `AI_BASE_URL` / `AI_MODEL`（任意 OpenAI 协议兼容的都行）：

| 中转站 | `AI_BASE_URL` | `AI_MODEL` | 说明 |
|--------|---------------|------------|------|
| ChatAnywhere（默认） | `https://api.chatanywhere.org/v1` | `deepseek-v3-2` | 免费版每周 50000 点 |
| DeepSeek 官方 | `https://api.deepseek.com/v1` | `deepseek-chat` | 便宜、中文好、有 function calling |
| 智谱 BigModel | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | 免费额度大 |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` | 阿里云百炼 |

> 框架不绑定具体厂商，任意 OpenAI 协议兼容的中转站都能用。

### 第 2 步：手动触发首次运行

进入 **Actions → Daily Collect → Run workflow** → 等绿勾出现（约 2-5 分钟）

完成后：
- 本 README 顶部的 **活动时间轴** SVG 会自动更新（你正在看的就是）
- 下方分类表格会列出所有活动
- `data/{ai,games}/activities.json` 是结构化原始数据

之后每天分 **6 个时段** 自动运行（分散全天、避开整点，减轻免费源网站压力），无需干预：

| 北京时间 | 模式 | 做什么 |
|---------|------|-------|
| 06:17 | `ai-cloud` | 云厂商活动（华为云/阿里云/腾讯云） |
| 09:23 | `ai-blog` | 博客聚合（AI 板块，含开源工具分流） |
| 11:41 | `drive` | V2EX 开车线报 |
| 14:37 | `games-direct` | Epic/Steam/GOG 官方 API |
| 16:53 | `games-blog` | ITAD/itch.io/Reddit/ggdeals |
| 20:47 | `finalize` | 整理：生成 SVG 日历 + 前端 JSON + README |

> ℹ️ 本仓库**不依赖 GitHub Pages**，日历直接以 SVG 图片形式嵌在 README 里渲染，任何账号都能用。

---

## 🍴 Fork 后如何使用（完整指南）

本仓库完全 fork 友好，fork 后按以下步骤配置即可独立运行，**不需要修改任何代码**。

### 1. Fork 仓库

点击本仓库右上角 **Fork** 按钮，复制到你自己的账号下。

### 2. 启用 Actions（关键，fork 后默认禁用）

进入你 fork 后的仓库 → **Actions** 标签页 → 会看到提示 "Workflows aren't being run on this forked repository" → 点击 **"I understand my workflows, enable them"** 按钮。

> ⚠️ 不启用这一步，定时任务永远不会跑。

### 3. 配置 AI_API_KEY Secret

进入你 fork 仓库的 **Settings → Secrets and variables → Actions → New repository secret**，添加：
- Name：`AI_API_KEY`
- Value：你的 ChatAnywhere API Key（去 [chatanywhere](https://chatanywhere.top) 注册免费领）

> fork 的仓库 secrets 不会从上游继承，必须自己配。workflow 的 `AI_BASE_URL` / `AI_MODEL` 已默认配好 ChatAnywhere + `deepseek-v3-2`，想换其他中转站再改 workflow env。

### 4. （可选）调整定时时间

fork 后 workflow 的 cron 默认和上游一样（6 个时段分散全天，避开整点）。建议把每个 cron 的分钟数整体加一个偏移量（如 +5），避免和上游同时跑：

编辑 `.github/workflows/daily-collect.yml`，6 个 cron 表达式形如 `17 22 * * *`（= UTC 22:17 = 北京 06:17）。北京时间 = UTC + 8。改分钟数即可错峰，如 `22 22 * * *`（延后 5 分钟）。

### 5. 手动触发首次运行

**Actions → Daily Collect → Run workflow** → 等绿勾。

### 6. 查看结果

运行成功后，直接看你 fork 仓库的 **README.md**——顶部的活动时间轴 SVG 和分类表格都会自动更新。不需要任何额外部署。

### 7. （可选）同步上游更新

上游有更新时，在你 fork 仓库首页会显示 **"Sync fork"** 按钮，点击即可同步。同步后你的自定义改动（如 `sources.json`、cron 时间）会保留。

### 8. （可选）自定义你的种子源

编辑 `data/sources.json`，加你想监控的网站：
```json
{
  "name": "某个活动页",
  "url": "https://example.com/promo",
  "category": "ai",
  "type": "html",
  "enabled": true,
  "note": "备注"
}
```
`category` 可选 `ai` / `games` / `mixed`。提交后下次运行自动生效。

---

## 🧱 技术框架

| 层 | 技术 | 说明 |
|----|------|------|
| 语言 | Python 3 | 所有收集 / 生成脚本，纯标准库 + `requests` |
| CI/CD | GitHub Actions | 6 时段 cron 定时触发，零服务器，免费额度足够 |
| AI | OpenAI 兼容中转站 | 默认 ChatAnywhere + `deepseek-v3-2` 弱模型，可换 DeepSeek / 智谱 / 通义 |
| 数据存储 | JSON 文件 | `data/*/activities.json`，无数据库，git 即版本控制 |
| 去重 | 稳定 ID（标题+URL 哈希） | 旧值优先合并，防止覆盖已确认字段 |
| 可视化 | SVG 甘特图 | `docs/calendar.svg`，零前端依赖，README 直接 `<img>` 渲染 |
| 部署 | 零部署 | 不依赖 GitHub Pages / Vercel，README 嵌 SVG 即是展示位 |

**设计理念**：全链路零外部服务依赖（除 AI 中转站外），GitHub 仓库本身即数据库 + CI + 展示位。fork 后配一个 Secret 就能跑。

---

## 🔧 工作原理

```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐
│ 种子源抓取   │ → │  AI 抽取活动  │ → │  去重合并    │ → │  生成产物    │
│ sources.json│   │ (中转站 API) │   │ (稳定 ID)   │   │ SVG+README  │
└─────────────┘   └──────────────┘   └─────────────┘   └──────────────┘
                         ↑
                  ┌──────────────┐
                  │ AI 联网搜索  │  混合模式补充
                  └──────────────┘
                         ↓
         四大分类：ai / open-source / drive / games
```

1. **每日 6 时段定时**：GitHub Actions 分六个时段分散全天运行（避开整点，减轻免费源网站压力），北京时间 06:17 / 09:23 / 11:41 / 14:37 / 16:53 / 20:47，分别跑 `ai-cloud` / `ai-blog` / `drive` / `games-direct` / `games-blog` / `finalize` 六个子模式
2. **种子源抓取**：从 `data/sources.json` 列出的目标网站抓取页面文本（内置 51 个源，全部启用——Action runner 在海外，可访问 Steam/Reddit/HuggingFace/Google AI Studio 等国内墙的网站）
3. **AI 抽取**：用 `scripts/prompts.py` 里写好的教程式提示词，调 OpenAI 兼容中转站，从页面内容里抽取结构化活动信息。**特别关注游戏「喜加一」**（Epic/Steam/GOG 免费游戏，用户最爱）
4. **四大分类分流**：抓到的活动按规则归入 `ai`（云服务/AI 优惠）/ `open-source`（一直免费的开源工具）/ `drive`（开车线报）/ `games`（游戏喜加一）四个类别
5. **联网搜索补充**：AI 用预设关键词联网搜索，发现种子源之外的新活动（混合模式）
6. **去重合并**：按稳定 ID（标题 + URL 哈希）去重，已有字段优先保留（旧值优先，防止覆盖已确认数据），按日期重算 status
7. **生成产物**（`finalize` 阶段）：
   - 更新 `data/{ai,open-source,drive,games}/activities.json`（原始数据）
   - 生成 `docs/calendar.svg`（README 顶部嵌入的甘特图日历，开源工具不进时间轴）
   - 生成 `docs/data/{activities,meta}.json`（结构化数据，可选用于自建前端）
   - 重写 `README.md`（嵌入 SVG + 分类表格）
8. **自动提交**：bot 身份 commit & push 回仓库

---

## 📁 仓库结构

```
wool-gathering/
├── AGENT.md                       # 维护规范（给 AI 或人看的操作交接文档，14 节）
├── .github/workflows/
│   └── daily-collect.yml          # Actions：六时段定时任务 + 自动提交
├── data/                          # 原始数据（脚本写，人别手改）
│   ├── ai/activities.json         # AI/云服务优惠（自动生成）
│   ├── open-source/activities.json# 开源免费工具（长期免费，end_date 空）
│   ├── drive/activities.json      # 开车线报（自动生成）
│   ├── games/activities.json      # 游戏喜加一（自动生成）
│   └── sources.json               # 种子源列表（51 个源，全部启用，可手改）
├── scripts/                       # Python 收集脚本
│   ├── ai_client.py               # AI 中转站客户端（OpenAI 兼容）
│   ├── collect.py                 # 主入口（Action 调用，支持子模式）
│   ├── prompts.py                 # AI 提示词（抽取规则、喜加一识别、字段要求）
│   ├── ai_guide.md                # AI 使用教程（人可读完整文档）
│   ├── cloud_collector.py         # 云厂商抓取（华为云/阿里云/腾讯云/腾讯 WorkBuddy）
│   ├── blog_collector.py          # 博客/V2EX/Reddit/ITAD/itch.io 抓取 + 分类规则
│   ├── direct_collector.py        # Epic/Steam/GOG 官方 API 抓取
│   ├── dedup.py                   # 去重合并 + 状态刷新
│   ├── svg_calendar.py            # SVG 甘特图日历生成（含文字防重叠）
│   ├── calendar_generator.py      # 前端数据 + README 生成（含车型子分类）
│   ├── readme_template.md         # README 模板
│   ├── utils.py                   # 工具函数
│   └── requirements.txt
├── docs/                          # 生成产物目录
│   ├── calendar.svg               # README 嵌入的日历（自动生成）
│   ├── GAME_PLATFORMS.md          # 游戏平台介绍（当前启用 + 可扩展源）
│   └── data/                      # 结构化 JSON（可选用于自建前端）
└── README.md                      # 本文件（由脚本自动刷新）
```

---

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

`status` 由起止日期每天自动重算：`active`（进行中）/ `upcoming`（未开始）/ `ended`（已结束）。

---

## 📅 日历视图说明

README 顶部的 `docs/calendar.svg` 是一个甘特图时间轴：

- 每个活动一条**横条**，长度对应活动持续时间
- 横条上的**白色进度填充**表示当前完成度
- **红色虚线**标记"今天"位置
- **半透明**横条 = 已结束
- **虚线边框** = 未开始
- 左侧带状态图标：🟢进行中 🟡未开始 ⚫已结束
- 横条上显示"剩 N 天"
- 底部图例说明各颜色含义

这样一眼就能看出哪些活动在并行进行、各自还剩多久，避免好几天都重复关注同一个活动。

---

## 🧠 AI 提示词

收集信息的 AI 提示词写在 `scripts/prompts.py`，明确定义了：

- **什么算薅羊毛活动**（8 类算 / 8 类不算）
- **特别关注游戏喜加一**（Epic/Steam/GOG 免费游戏，含字段填写规范）
- **必须抽取的字段及格式**（title/url/日期/价值/条件等）
- **日期自然语言换算表**（"即日起"→今天、"至月底"→当月最后一天等）
- **边界情况处理**（登录页/错误页/空页面/JS 空壳 → 返回空数组）
- **常见错误及避免方法**（8 条）
- **完整示例**（喜加一/代金券/免费额度）
- **输出格式**（严格 JSON）

完整的人可读教程见 **[scripts/ai_guide.md](scripts/ai_guide.md)**，包含 10 个章节 + 4 个完整示例。

想调整抽取规则（比如放宽/收紧什么算薅羊毛），直接改 `prompts.py` 或 `ai_guide.md` 即可，不用动其他代码。

---

## 🛠 自定义

### 添加种子源

编辑 `data/sources.json`，加一条：

```json
{
  "name": "活动页名称",
  "url": "https://example.com/promo",
  "category": "ai",
  "type": "html",
  "enabled": true,
  "note": "备注"
}
```

字段说明：
- `category`：`ai` / `games` / `mixed`
- `type`：`html` / `rss` / `api` / `manual`
- `enabled`：`false` 可临时禁用

### 调整联网搜索关键词

编辑 `scripts/collect.py` 里的 `SEARCH_KEYWORDS` 字典。

### 调整 AI 抽取规则

编辑 `scripts/prompts.py` 里的 `SYSTEM_PROMPT`。

### 修改运行时间

编辑 `.github/workflows/daily-collect.yml` 的 6 个 cron 表达式（UTC 时间，北京时间 = UTC + 8）：

```yaml
schedule:
  - cron: "17 22 * * *"   # 06:17 北京 → ai-cloud（云厂商）
  - cron: "23 1 * * *"    # 09:23 北京 → ai-blog（博客聚合）
  - cron: "41 3 * * *"    # 11:41 北京 → drive（V2EX 开车线报）
  - cron: "37 6 * * *"    # 14:37 北京 → games-direct（Epic/Steam/GOG）
  - cron: "53 8 * * *"    # 16:53 北京 → games-blog（ITAD/itch.io/Reddit）
  - cron: "47 12 * * *"   # 20:47 北京 → finalize（整理：SVG + README）
```

> 6 个时段分散全天、避开整点，减轻免费源网站压力。改分钟数即可错峰。

---

## 💻 本地调试

```bash
git clone https://github.com/<你的用户名>/wool-gathering.git
cd wool-gathering
pip install -r scripts/requirements.txt

export AI_BASE_URL="https://api.chatanywhere.org/v1"
export AI_API_KEY="sk-xxx"
export AI_MODEL="deepseek-v3-2"
export GITHUB_REPOSITORY="<你的用户名>/wool-gathering"

cd scripts && python collect.py
```

跑完后 `data/`、`docs/calendar.svg`、`README.md` 都会更新。

---

## ❓ 常见问题

**Q: Action 跑了但没收集到任何活动？**
A: 检查 Actions 日志，常见原因：① Secrets 没配或配错；② 中转站不支持联网搜索（不影响种子源抽取，但搜索补充会空）；③ 种子源页面结构变了导致 AI 抽不到——可在 `sources.json` 里换 URL 或暂时 `enabled: false`。

**Q: README 顶部的日历 SVG 不显示？**
A: SVG 是 Action 生成后 commit 进仓库的。确认 Actions 跑成功过一次，且 `docs/calendar.svg` 文件存在。GitHub 渲染 README 里的 SVG 图片有时有几分钟缓存延迟，刷新一下即可。

**Q: fork 后 Actions 不跑？**
A: fork 默认禁用 Actions，需要到 Actions 页点 "I understand my workflows, enable them"。

**Q: 想改成私有仓库？**
A: 可以。本方案不依赖 GitHub Pages，私有仓库也能正常跑 Action + 在 README 渲染 SVG。

**Q: 每天跑会不会消耗很多 AI 额度？**
A: 6 个时段加起来每次约调 AI 30-50 次（51 个种子源抽取 + 联网搜索补充），用 ChatAnywhere 免费版（每周 50000 点 + 每天 100 次请求）或 DeepSeek/智谱免费额度基本够，单次成本约几分钱。

**Q: 想要更炫的可视化页面？**
A: `docs/data/activities.json` 已经生成好了，可以自己写个 HTML 读它部署到任意静态托管（GitHub Pages / Vercel / Cloudflare Pages 都行）。本仓库的 `docs/index.html` 也保留着之前的完整前端，可按需启用。

---

## ⚠️ 免责声明

- 本项目仅**收集公开活动信息**，不参与任何活动分发
- 领取请前往活动官方页面，遵守各平台规则
- AI 抽取的信息可能存在误差，请以活动官方页面为准
- 不对活动的真实性、可用性做任何保证
- 请勿用于商业转售或批量囤积违反平台规则的行为

---

## 📜 License

MIT — 随意 fork、修改、商用，但请保留原作者署名。
