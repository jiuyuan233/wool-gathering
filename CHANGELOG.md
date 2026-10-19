# 更新日志

## 2026-10-18

- 初始版本上线
- 实现：种子源抓取 + AI 抽取 + 联网搜索补充 + 去重合并 + Pages 日历视图
- 内置 12 个种子源（华为云/阿里云/腾讯云/百度云/火山引擎/智谱/Epic/Steam/GOG 等）
- 每天北京时间 09:00 自动运行

## 2026-10-19 22:30 概况汇报

### 数据条目（共 123 条）

| 分类 | 条数 | 说明 |
|------|------|------|
| AI / 云服务 | 38 | 含 15 条新增 AI Agent 厂商免费额度 |
| 开源免费工具 | 12 | 一直免费，不进 SVG 时间轴 |
| 开车线报 | 3 | V2EX 等 |
| 游戏喜加一 | 70 | Epic/Steam/GOG/itch.io |
| 合计 | 123 | SVG 时间轴显示 111 条（排除 12 条开源） |

信息源：51 个

### 自动化调度（6 时段，避开整点）

| 北京时间 | 模式 | 内容 |
|---------|------|------|
| 06:17 | ai-cloud | 云厂商优惠 |
| 09:23 | ai-blog | 博客聚合 |
| 11:41 | drive | V2EX 开车线报 |
| 14:37 | games-direct | Epic/Steam/GOG 官方 API |
| 16:53 | games-blog | ITAD/itch.io/Reddit |
| 20:47 | finalize | 整理 + SVG + README 生成 |

### AI 配置

- 中转站：ChatAnywhere（https://api.chatanywhere.org/v1）
- 模型：deepseek-v3-2
- 密钥：通过 GitHub Secret AI_API_KEY 注入

### 近期提交脉络

- 44aeb13 新增15条AI Agent厂商免费额度羊毛（国内外大厂+创业公司）
- 78cfb38 README 新增「技术框架」段落（技术栈一览表）
- 5b1f4a4 all update 2026-10-19
- f9f278a 收尾更新 README 框架介绍 + AGENT.md AI 配置教程
- b2add9f 社区资源板块扩充至12个仓库，按6个方向分组

### 仓库亮点

- README 顶部含「社区整理的免费资源」板块（12 个仓库按 6 方向分组）
- README 含「技术框架」段落（7 层技术栈一览）
- AGENT.md 14 节维护规范，含 AI 中转站配置与手动触发教程
- SVG 甘特图日历带 textLength 防重叠
- 零部署，纯 GitHub Actions + JSON 存储

### 新增 15 条 AI 羊毛明细

- 国内大厂：阿里百炼、智谱 GLM-4-Flash 永久免费、DeepSeek、腾讯混元、百度千帆、讯飞星火、MiniMax、字节 Coze、360 智脑、月之暗面 Kimi
- 国外：Google Gemini、OpenAI ChatGPT、Cursor
- Agent 产品：华为云 CodeArts、腾讯 WorkBuddy
