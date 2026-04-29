---
name: social-media-post-content-creation
description: >
  社交媒体内容创作。规划未来几次发布的内容，确认素材需求，生成图片/视频/文案，呈现给用户审阅，存入草稿待定时发布。
  触发场景：(1) [cron] 每周定时起草内容计划；(2) 用户临时要求生成内容。
integrations: []
---

# Social Media Content Creation

## 触发判断

- `[cron] 内容共创` → **阶段 1**：起草本周内容计划
- 用户发来素材（图片 / 视频）或说「这是素材」→ **阶段 3**：直接创作
- 用户临时要求（「帮我做个海报」「帮我做几张图」）→ **阶段 3**：直接创作

---

## 阶段 1 — 内容计划

读取 `/workspace/marketing-context.md`，了解品牌名称、行业、调性、已连接平台、发布节奏、内容方向。

根据已连接平台，读取对应 reference 文件了解尺寸规格、Caption 限制、Hashtag 数量及周内容配比：
`/mnt/skills/social-media-post-content-creation/references/{platform}.md`

根据本周日期为每条待发内容起草条目：

| 字段 | 说明 |
|------|------|
| 日期 | 计划发布日 |
| 平台 | Instagram / LinkedIn / Twitter 等 |
| 内容类型 | 单图海报 / Carousel / Reels / Story（仅 Instagram）|
| 主题 | 这条内容讲什么，一句话 |
| 素材需求 | AI 生成 / 需用户提供图片 / 需用户提供视频 |

**内容类型判断：**

| 场景 | 类型 |
|------|------|
| 多产品 / 多卖点 / 步骤教程 / 前后对比 | Carousel |
| 单个强视觉 / 简单公告 / 节日海报 | 单图海报 |
| 幕后故事 / 制作过程 / 有视频素材 | Reels |
| 快速互动 / 限时优惠（仅 Instagram） | Story |

不确定选哪种类型时，参照对应平台 reference 文件中的周配比，补足当周比例较低的类型。

**跨平台素材复用：**
同周如多平台发同主题内容，合并为一个素材任务，在计划表"素材需求"里注明复用关系：
- 1:1 图片 → Instagram 单图 / Facebook Feed Post / LinkedIn Image Post 三平台通用
- 9:16 视频 → Instagram Reels + Facebook Reels 直接跨发，无需重新生成

---

## 阶段 2 — 素材清单

将所有条目的素材需求拆分为两类：

- **AI 自动生成**：直接进入阶段 3
- **需用户提供**：列出清单，说明每条需要什么（几秒视频 / 产品图 / 场景图），等素材到位后进入阶段 3

以对话语气呈现计划和清单，**等待 admin 明确确认后才能继续**。除非 admin 之前已明确说明「每次直接生成，不用确认」，否则禁止跳过此步骤直接进入阶段 3。

---

## 阶段 3 — 素材创作

所有可生成的内容并行创作，根据内容类型路由。已标注「复用 [平台] 素材」的条目跳过生成，直接引用已生成的文件路径：

| 内容类型 | 路由 |
|---------|------|
| 单图海报 | `poster-design` skill |
| Carousel 海报 | 先读 `/mnt/skills/social-media-post-content-creation/features/carousel.md` 规划叙事结构，再用 `poster-design` skill 逐张设计 |
| 纯图片 / Carousel 组图（不叠文字） | `/mnt/skills/social-media-post-content-creation/features/generate-image.md` |
| 视频 | `/mnt/skills/social-media-post-content-creation/features/generate-video.md` |

---

## 阶段 4 — Post 组装

每条素材生成后配套写：

- **Caption**：补充素材没有呈现的信息（背景故事 / 使用体验 / 为什么选择），结尾引导行动
- **Hashtags**：按平台要求（Instagram 10–15 个 / Facebook & LinkedIn 3–5 个 / Twitter 1–2 个），覆盖大众标签 + 垂直标签 + 地理 / 品牌标签

---

## 阶段 5 — 用户审阅

所有内容生成完毕后，调用 `show_post_preview` 一次性呈现全部 post：

```
show_post_preview({
  slides: [{ path: "/mnt/session/outputs/{filename}", label: "封面" }],
  caption: "完整文案",
  hashtags: ["tag1", "tag2"]
})
```

- 单图：slides 一项
- Carousel：slides 按张顺序传入
- 纯文字帖：slides 为空数组

用户整体确认后进入阶段 6。对某条有修改意见则单独重做该条，重新呈现。

---

## 阶段 6 — 存档

每条确认后写入 `/workspace/drafts/`：

文件名：`{YYYY-MM-DD}-{platform}-{type}-{slug}.md`

每条草稿包含：

| 字段 | 说明 |
|------|------|
| 平台 | `instagram` / `facebook` / `linkedin` / `twitter` |
| 内容类型 | Carousel / 单图海报 / Reels / Story（仅 Instagram）|
| 状态 | `待发布` |
| 计划发布日 | YYYY-MM-DD |
| 媒体文件路径 | 生成的图片 / 视频路径（文字帖可为空） |
| Caption | 完整文案 |
| Hashtags | 标签列表 |

草稿存好后由每天 09:00 的 `[cron] 内容发布` 按日期自动扫描发布。
