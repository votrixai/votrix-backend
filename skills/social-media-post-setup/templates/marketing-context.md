# Marketing Context

_所有技能从 `mnt/memory/social-media-manager/marketing-context.md` 读取配置和指令。品牌图片/视频只在此文件中存 **URL**（由 `publish_file` 或 admin 提供的可访问链接），不存沙箱路径。_

---

## 指令

_在此添加针对此账号的特殊规则，agent 会优先遵守。发布行为、互动风格等工作流偏好写在这里，不需要开关配置。_

---

## 品牌资料

- **名称：**
- **行业：**
- **网站：**
- **简介：**
- **地区：**
- **时区：**（如 Asia/Shanghai、America/New_York）
- **目标受众：**
- **主要产品 / 服务：**
- **品牌构图风格：**（排版布局、元素构成、留白比例、图文关系、整体视觉氛围等）
- **品牌风格：**
- **内容氛围 / Mood：**（从素材推断，如高端质感、温暖亲切、专业严肃、活泼趣味；未确认时留空）
- **Logo 描述：**
- **Logo URL：**

---

## 品牌素材

- **Logo：**
  _(每行一个，格式：`URL — 备注`，须为可公开访问的 https 链接，例如：)_
  _`https://…/logo.png — 原彩色版`_
  _`https://…/logo-mono.png — 单色化版（深色背景）`_

- **吉祥物：**
  _(每行一个，格式同上，例如：)_
  _`https://…/mascot.png — 原版`_
  _`https://…/mascot-clean.png — 去背景版`_

---

## 内容策略

_由 setup 初始化，analytics 和 review-monitor 持续更新。_

### 内容方向分配

### 发布节奏

---

## 自定义规则

_Admin 或 AI 均可在此追加规则。例如：特定节假日不发帖、某类产品不做促销、回复评论时避免提及竞品等。_

---

## 工作流

_定时自动化任务。agent 收到 `[cron]` 触发消息时依此执行，无需 admin 在线。_

### 内容创作（批量）
- **启用：** false
- **触发时间：** 每周一 09:00

### 内容发布（每日）
- **启用：** false
- **触发时间：** 每天 09:00

### 评论巡查
- **启用：** false
- **触发间隔：** 每 6 小时

### 数据汇报
- **启用：** false
- **触发时间：** 每周五 18:00
- **报告类型：** 快速总结

---

## 已连接平台

### Facebook
- 启用：false
- 主页名称：
- Page ID：

### Instagram
- 启用：false
- 用户名：
- Account ID：

### Twitter
- 启用：false
- 用户名：
- User ID：

### LinkedIn
- 启用：false
- 公司名称：
- Organization ID：
- Person ID：

---

## 运行状态

_由 cron 任务自动更新，记录各平台上次巡查的位置，避免重复处理。_

### Facebook
- 上次巡查时间：
- 最后处理的 Post ID：

### Instagram
- 上次巡查时间：
- 最后处理的 Post ID：

### Twitter
- 上次巡查时间：
- 最后处理的 Post ID：

### LinkedIn
- 上次巡查时间：
- 最后处理的 Post ID：
