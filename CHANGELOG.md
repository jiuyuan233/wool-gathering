## 2026-10-21 修复凌晨运行问题+cron提前+恢复Playwright/PENDING_URLS提交

### 改动

- **cron 时间提前 2 小时**（避免 GitHub Actions cron 延迟导致凌晨运行）：
  - ai-cloud: 06:17→05:17 / ai-blog: 09:23→08:23 / drive: 11:41→10:41
  - games-direct: 14:37→13:37 / games-blog: 16:53→15:53 / finalize: 20:47→18:47
  - finalize 提前到 18:47，即使延迟 5 小时也是 23:47，不会到凌晨
- **恢复 workflow Playwright 安装**（c20b8a8 的修复被后续 commit 回退了）
- **恢复 workflow git add PENDING_URLS.md**（同上）
- **恢复 requirements.txt playwright>=1.40.0**（同上）
- AGENT.md 第 5 节 cron 时间表更新 + 加 cron 延迟说明

# 更新日志

## 2026-10-20 新增游戏打折分区（小黑盒数据源）

- 新增 `game-discount` 分区：Steam 新品节/尖叫节打折汇总（史低/新史低/一折以下）
- 小黑盒（xiaoheihe.cn）作为新数据源：SPA 需 Playwright 渲染，`blog_collector.collect_heybox_discounts()` 处理
- 首条活动：【10.20】Steam新品节打折153款佳作最低3元（40款新史低+86款史低+27款一折以下）
- collect.py/calendar_generator.py/svg_calendar.py: CATEGORIES 加 game-discount，紫色 #8b5cf6
- sources.json: 加小黑盒源（type=heybox），源总数 51→52
- AGENT.md: 七大→八大分类，新增第15.8节小黑盒操作指南
- readme_template.md: 七大→八大分类说明
- 最终分布：AI 30 / 购物 2 / 视频会员 2 / 网盘会员 2 / 开源 13 / 开车 3 / 游戏 70 / 游戏打折 1 = 123 条

## 2026-10-19 游戏中文翻译 + 购物修正

- 购物分区修正：7 条里仅 2 条属购物（双11打折整理+双11红包），其余 5 条归位（WPS/复旦Codex/VideoProc→AI，VMware→open-source，重复复旦Codex删除）
- SHOPPING_HINTS 关键词精简：移除 wps/vmware/videoproc/复旦/codex/周年庆，只保留双11/红包/打折好价
- 游戏喜加一 68 条英文标题附中文翻译（格式 `英文原名 ｜中文译名`），如 `Bad Cheese ｜坏奶酪`、`Castlevania Anniversary Collection ｜恶魔城周年纪念合集`
- AGENT.md 新增第 15.7 节游戏标题中文翻译规则，readme_template.md 更新七大分类说明
- 最终分布：AI 30 / 购物 2 / 视频会员 2 / 网盘会员 2 / 开源 13 / 开车 3 / 游戏 70 = 122 条

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

## 2026-10-19 22:35 长期免费分区 + 当月日历

### 改动

- 新增 `utils.is_long_term()` 函数：判断活动是否长期免费（无 end_date 或 end_date 距今 > 90 天）
- SVG 日历改为只显示当月限时活动：时间范围固定为当月，长期活动不进时间轴
- README 新增「♾️ 长期免费」分区：open-source + end_date 超过 3 个月的活动统一归入此分区
- open-source 不再单独成区，已合并进长期免费分区
- AGENT.md 新增第 4.1 节（当月日历规则）+ 第 15 节（AI 操作指南：手动新增/更新活动信息）

### 效果

- 当月限时活动 103 条显示在 SVG 时间轴
- 长期免费 18 条（12 开源工具 + 6 长期 AI 羊毛）在 README 表格显示，不进时间轴
- 总 123 条 = 限时 105 条 + 长期 18 条

## 2026-10-19 22:45 日历改为时间轴跨度一个月 + 显示全部限时活动

### 改动

- SVG 日历时间轴跨度固定为当月（刻度只显示当月）
- 显示所有有时间限制的活动（有 start_date 和 end_date），不管持续时间多长
- 超过一个月持续时间的活动：横条顶满整个跨度（clamp 到时间轴范围）
- 按分区分组显示：AI / 云服务 → 开车线报 → 游戏喜加一，每个分区有标题行
- 分区内按 end_date 升序排列（快结束的排上面）
- 开源项目（无 end_date）不显示在时间轴
- AGENT.md 第 4.1 节更新为新的日历规则

### 效果

- 有时间限制活动 111 条全部显示在 SVG 时间轴
- 开源工具 12 条不显示（无 end_date）
- 超过一个月的活动 15 条顶满跨度
- 3 个分区标题行：AI（38 条）/ 开车（3 条）/ 游戏（70 条）

## 2026-10-19 23:00 更新所有说明性 md 文档

### 改动

- AGENT.md 第 15 节（AI 操作指南）更新：日历逻辑说明改为"显示全部限时活动+时间轴跨度一个月+超过一个月顶满+按分区分组+快结束排上面"
- AGENT.md 第 15.6 节验证清单更新
- readme_template.md 活动时间轴说明更新（第 55-60 行）
- readme_template.md 日历视图说明更新（第 290-303 行）：新增时间轴跨度、分区、顶满等说明
- README.md 重新生成（反映模板更新）

## 2026-10-20 00:15 新增3个分类：购物/视频会员/网盘会员

### 改动

- 从 ai 分类分出 3 个新分类：shopping（购物优惠）、video-vip（视频会员）、netdisk-vip（网盘会员）
- blog_collector.py 新增 is_shopping/is_video_vip/is_netdisk_vip 分类函数 + 关键词
- parse_blog_articles 分流逻辑更新：开源 → 购物 → 视频会员 → 网盘会员 → 默认
- collect.py / calendar_generator.py / svg_calendar.py 的 CATEGORIES 加新分类
- SVG 日历新增 3 个分区（颜色：购物金色/视频粉色/网盘青色），图例更新
- 数据迁移：ai 38→27 条，shopping 7 条，video-vip 2 条，netdisk-vip 2 条
- AGENT.md 第 2 节从"四大分类"改为"七大分类"，第 15 节加新分类操作说明

### 效果

- SVG 6 个分区：AI（27）/ 购物（7）/ 视频会员（2）/ 网盘会员（2）/ 开车（3）/ 游戏（70）
- 总 123 条不变，分类更清晰
