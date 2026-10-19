# 🐑 薅羊毛情报站

> 全网 **AI / 游戏** 免费福利活动自动收集 · 每日由 GitHub Actions + AI 更新

---

## 📅 活动时间轴

![活动日历](docs/calendar.svg)

> 每条横条 = 一个活动的持续时间 ｜ 红色虚线 = 今天 ｜ 白色进度填充 = 当前完成度
> ｜ 半透明 = 已结束 ｜ 虚线边框 = 未开始 ｜ 🟢进行中 🟡未开始 ⚫已结束

---

## 📊 今日概况

- 更新时间：**2026-10-19 08:11** 北京时间
- 进行中：**0** 个 ｜ 即将开始：**0** 个 ｜ 历史收录：**0** 个

---

## 🗂 分类活动

### 🤖 AI 类

_暂无活动_

### 🎮 游戏类

_暂无活动_


---

## 🚀 快速开始（2 步跑通）

### 第 1 步：配置 AI Secrets

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**，添加 3 个：

| Secret 名 | 说明 | 示例值 |
|-----------|------|--------|
| `AI_BASE_URL` | AI 中转站地址（OpenAI 兼容协议） | `https://api.deepseek.com/v1` |
| `AI_API_KEY` | 中转站 API Key | `sk-xxxxxxxx` |
| `AI_MODEL` | 模型名 | `deepseek-chat` |

**推荐的免费 / 低价中转站**（任选一个，自行注册）：

| 中转站 | `AI_BASE_URL` | `AI_MODEL` | 说明 |
|--------|---------------|------------|------|
| DeepSeek 官方 | `https://api.deepseek.com/v1` | `deepseek-chat` | 便宜、中文好、有 function calling |
| 智谱 BigModel | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | 免费额度大 |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` | 阿里云百炼 |
| OpenAI 兼容中转站 | 任意 `.../v1` | 任意 | 搜"OpenAI 中转站" |

> 任意 OpenAI 协议兼容的中转站都能用，框架不绑定具体厂商。

### 第 2 步：手动触发首次运行

进入 **Actions → Daily Collect → Run workflow** → 等绿勾出现（约 2-5 分钟）

完成后：
- 本 README 顶部的 **活动时间轴** SVG 会自动更新（你正在看的就是）
- 下方分类表格会列出所有活动
- `data/{ai,games}/activities.json` 是结构化原始数据

之后每天北京时间 **09:00** 自动运行，无需干预。

> ℹ️ 本仓库**不依赖 GitHub Pages**，日历直接以 SVG 图片形式嵌在 README 里渲染，任何账号都能用。

---

## 🍴 Fork 后如何使用（完整指南）

本仓库完全 fork 友好，fork 后按以下步骤配置即可独立运行，**不需要修改任何代码**。

### 1. Fork 仓库

点击本仓库右上角 **Fork** 按钮，复制到你自己的账号下。

### 2. 启用 Actions（关键，fork 后默认禁用）

进入你 fork 后的仓库 → **Actions** 标签页 → 会看到提示 "Workflows aren't being run on this forked repository" → 点击 **"I understand my workflows, enable them"** 按钮。

> ⚠️ 不启用这一步，定时任务永远不会跑。

### 3. 配置 3 个 Secrets

进入你 fork 仓库的 **Settings → Secrets and variables → Actions → New repository secret**，依次添加：

- `AI_BASE_URL` = 你的中转站地址
- `AI_API_KEY` = 你的 API Key
- `AI_MODEL` = 模型名

（值同上表，fork 的仓库 secrets 不会从上游继承，必须自己配）

### 4. （可选）调整定时时间

fork 后 workflow 的 cron 默认和上游一样（北京时间 09:00）。建议改成错峰时间，避免和上游同时跑：

编辑 `.github/workflows/daily-collect.yml`，把
```yaml
- cron: "0 1 * * *"
```
改成你想要的时间（UTC 时间，北京时间 = UTC + 8）。例如北京时间 10:30 = UTC 02:30：
```yaml
- cron: "30 2 * * *"
```

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
```

1. **每日定时**：GitHub Actions 在北京时间每天 09:00 自动运行（cron `0 1 * * *` UTC）
2. **种子源抓取**：从 `data/sources.json` 列出的目标网站抓取页面文本（内置 51 个源，全部启用——Action runner 在海外，可访问 Steam/Reddit/HuggingFace/Google AI Studio 等国内墙的网站）
3. **AI 抽取**：用 `scripts/prompts.py` 里写好的教程式提示词，调 OpenAI 兼容中转站，从页面内容里抽取结构化活动信息。**特别关注游戏「喜加一」**（Epic/Steam/GOG 免费游戏，用户最爱）
4. **联网搜索补充**：AI 用预设关键词联网搜索，发现种子源之外的新活动（混合模式）
5. **去重合并**：按稳定 ID（标题 + URL 哈希）去重，已有字段优先保留，按日期重算 status
6. **生成产物**：
   - 更新 `data/{ai,games}/activities.json`（原始数据）
   - 生成 `docs/calendar.svg`（README 顶部嵌入的甘特图日历）
   - 生成 `docs/data/{activities,meta}.json`（结构化数据，可选用于自建前端）
   - 重写 `README.md`（嵌入 SVG + 表格速览）
7. **自动提交**：bot 身份 commit & push 回仓库

---

## 📁 仓库结构

```
wool-gathering/
├── .github/workflows/
│   └── daily-collect.yml          # Actions：每日收集 + 自动提交
├── data/
│   ├── ai/activities.json         # AI 类活动数据（自动生成）
│   ├── games/activities.json      # 游戏类活动数据（自动生成）
│   └── sources.json               # 种子源列表（51 个源，全部启用，Action 海外可访问）
├── scripts/                       # Python 收集脚本
│   ├── ai_client.py               # AI 中转站客户端（OpenAI 兼容）
│   ├── collect.py                 # 主入口（Action 调用）
│   ├── prompts.py                 # AI 提示词（教程式，抽取规则、喜加一识别、字段要求）
│   ├── ai_guide.md                # AI 使用教程（人可读完整文档）
│   ├── sources_manager.py         # 种子源抓取
│   ├── dedup.py                   # 去重合并 + 状态刷新
│   ├── svg_calendar.py            # SVG 甘特图日历生成
│   ├── calendar_generator.py      # 前端数据 + README 生成
│   ├── readme_template.md         # README 模板
│   ├── utils.py                   # 工具函数
│   └── requirements.txt
├── docs/                          # 生成产物目录
│   ├── calendar.svg               # README 嵌入的日历（自动生成）
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

编辑 `.github/workflows/daily-collect.yml` 的 cron 表达式（UTC 时间）：

```yaml
schedule:
  - cron: "0 1 * * *"   # UTC 01:00 = 北京时间 09:00
```

---

## 💻 本地调试

```bash
git clone https://github.com/<你的用户名>/wool-gathering.git
cd wool-gathering
pip install -r scripts/requirements.txt

export AI_BASE_URL="https://api.deepseek.com/v1"
export AI_API_KEY="sk-xxx"
export AI_MODEL="deepseek-chat"
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
A: 每次跑大约调用 AI 30-50 次（29 个种子源抽取 + 12 个联网搜索），用 DeepSeek/智谱免费额度基本够，单次成本约几分钱。

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
