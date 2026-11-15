## 🍴 Fork 后如何使用（完整指南）

本仓库完全 fork 友好，fork 后按以下步骤配置即可独立运行，**不需要修改任何代码**。

### 1. Fork 仓库

点击本仓库右上角 **Fork** 按钮，复制到你自己的账号下。

### 2. 启用 Actions（关键，fork 后默认禁用）

进入你 fork 后的仓库 → **Actions** 标签页 → 会看到提示 "Workflows aren't being run on this
forked repository" → 点击 **"I understand my workflows, enable them"** 按钮。

> ⚠️ 不启用这一步，定时任务永远不会跑。

### 3. 配置 AI Secrets（2 个）

进入 **Settings → Secrets and variables → Actions → New repository secret**：

| Secret 名 | Value | 必填 |
|-----------|-------|------|
| `AI_API_KEY` | ChatAnywhere API Key（去 [chatanywhere](https://chatanywhere.top) 免费领） | ✅ |
| `AI_FALLBACK_API_KEY` | SiliconFlow API Key（备用，主力挂了自动切换） | 可选 |

> fork 的仓库 secrets 不会从上游继承，必须自己配。只配第 1 个也能跑。

### 4. （可选）调整定时时间

workflow 的 cron 默认和上游一样（6 个时段分散全天，避开整点）。建议把每个 cron 的分钟数
整体加一个偏移量（如 +5），避免和上游同一时刻跑。

编辑 `.github/workflows/daily-collect.yml`，cron 形如 `17 21 * * *`（= UTC 21:17 = 北京 05:17），
北京时间 = UTC + 8。改分钟数即可错峰，如 `22 21 * * *`（延后 5 分钟）。

### 5. 手动触发首次运行

**Actions → Daily Collect → Run workflow** → Mode 留 `all` → 等绿勾（约 5-20 分钟）。

### 6. 查看结果

运行成功后，直接看你 fork 仓库的 **README.md**——顶部的活动时间轴 SVG、今日概况、
分类表格都会自动更新。过期活动自动归档到 `docs/archive/`。不需要任何额外部署。

### 7. （可选）提交想监控的网址

编辑 `PENDING_URLS.md`，在「待处理」区写一行 URL（可加 `# 分类` 注释）：

```markdown
https://example.com/some-deal # ai
```

下次 finalize（每天 18:47）会自动登记、当场抓取内容并把结果记录到「已处理」区。
注意：单次提交只会抓一次快照；想让某网站**每天被查**，按 [自定义](自定义.md)
把它加进日常轮询源（`blog_collector.SOURCES` 等）。

### 8. （可选）同步上游更新

上游有更新时，在你 fork 仓库首页会显示 **"Sync fork"** 按钮，点击即可同步。
同步后你的自定义改动（如 cron 时间、Secrets）会保留。

---
