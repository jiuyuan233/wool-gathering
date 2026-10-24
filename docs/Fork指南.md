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

