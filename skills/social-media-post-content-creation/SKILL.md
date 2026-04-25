---
name: social-media-post-content-creation
description: >
  社交媒体内容创作。有两种触发场景：
  (1) [cron] 内容共创 — 每周定时触发，AI 独立起草本周内容计划，呈现给 admin 审批，确认后收集素材、逐条生成海报/视频；
  (2) admin 临时要求 — 做海报、做视频、生成素材、发帖等临时内容创作需求。
  默认输出格式：海报（设计好的图片）。Reels 类内容需用户提供视频素材。
integrations: []
---

# Social Media Content Creation

## 触发判断

收到消息后先判断场景，进入对应阶段：

- `[cron] 内容共创` → **第一阶段**：独立起草本周内容计划
- 用户发来图片 / 视频素材，或说「这是素材」「这是本周的图」→ **第三阶段**：直接生成内容
- 用户临时要求（「帮我做个海报」「帮我做条 Reels」）→ 跳到对应功能（F1 / F2 / F3 / F4）按需执行

---

## 第一阶段：独立起草内容计划（cron 触发）

### 1. 读取品牌背景

读取 `/workspace/marketing-context.md`，了解：
- 品牌名称、行业、风格调性
- 已连接平台及各平台发布节奏
- 内容方向（Pillars）

### 2. 起草本周计划

根据本周日期 + 内容策略，为每条待发内容起草条目：

| 字段 | 说明 |
|---|---|
| 日期 | 计划发布日 |
| 平台 | Instagram / LinkedIn / Twitter 等 |
| 内容类型 | Carousel / 单图海报 / Reels / Story / 文字 |
| 主题 | 这条内容讲什么，一句话 |
| 文案角度 | Hook 方向（数字冲击 / 场景代入 / 直接价值） |
| 素材需求 | `需要你提供图片` / `需要你提供视频` / `AI 生成` |

**内容类型判断规则：**

| 场景 | 选择 |
|---|---|
| 多个产品 / 多卖点 / 步骤教程 / 前后对比 | Carousel |
| 单个强视觉 / 简单公告 / 节日海报 | 单图海报 |
| 幕后故事 / 制作过程 / 有视频素材 | Reels（标记：需用户提供视频） |
| 快速互动 / 限时优惠 / 轻量内容 | Story |
| 行业观点 / 知识输出（LinkedIn 为主） | 文字 or Carousel |

**不确定时默认 Carousel**——互动率最高，灵活性最强。

### 3. 进入第二阶段

---

## 第二阶段：共创会话（admin review）

用对话语气逐条过一遍，不要表格罗列，像顾问汇报一样：

> 「这是我为本周准备的内容计划，一共 X 条——
>
> 周一 Instagram Carousel：[主题]，打算从 [文案角度] 切入。这条我可以自己生成。
>
> 周三 Instagram Reels：[主题]。这条需要你拍一段 [XX 秒左右的 XX 内容] 发给我。
>
> 周五 LinkedIn：[主题]，纯文字，不需要素材。
>
> ...
>
> 整体方向有没有要调整的？确认后我们逐条来做。」

Admin 可以：
- 改主题、换类型
- 删掉某条
- 补充说明（「这周有个新品上架，加一条」）

**确认后**：告知 admin 哪些帖子需要他提供素材，请他准备好后发过来，AI 同时开始生成不需要素材的内容。

---

## 第三阶段：内容生成（素材到位后逐条执行）

**默认输出格式：海报**（设计好的图片，可直接发布）。

根据每条内容的类型和素材情况，路由到对应功能：

| 内容类型 | 素材情况 | 执行管道 |
|---|---|---|
| 单图海报 / Carousel | 用户提供了图片 | `f1-generate-poster.md`（直接做海报） |
| 单图海报 / Carousel | 无图，AI 生成 | `f3-generate-image.md` 生成背景图 → 自动衔接 `f1-generate-poster.md` 叠文字排版 |
| Reels / 短视频 | 用户提供了视频 | `f2-edit-video.md` |
| 叙事视频 | 用户提供图片 + 剧本思路 | `f4-generate-video.md` |
| 文字帖（LinkedIn / Twitter） | 不需要图片 | 直接生成文案，无需图片步骤 |

**F3 → F1 管道说明：** F3 生成的图片是背景素材，不是最终输出。生成后立即进入 F1，以该图片为底图，叠加文字、品牌包装、排版设计，输出完整海报。F3 步骤 1 的「目标用途」填写「作为 F1 海报的背景」。

**品牌视觉检查（生成前）：**

- `/workspace/brand-style/poster-philosophy.md` 存在 → 读取并沿用，保持品牌一致
- 不存在 → F1 / F3 执行过程中自动推导并写入，后续复用

**每条内容生成完毕后，按以下步骤展示给用户审阅：**

**第一步：用 `download_file` 获取每张图片的 file_id**

```
download_file({ file_path: "/mnt/session/outputs/poster_cover.png" })
→ 返回 { file_id: "abc123", filename: "poster_cover.png", ... }
```

Carousel 有几张图就调几次，记下每张的 `file_id`。

**第二步：调 `show_post_preview` 展示预览卡片（直接传路径，无需先调 `download_file`）**

```json
{
  "platform": "instagram",
  "content_type": "carousel",
  "theme": "主题一句话",
  "caption": "完整文案",
  "hashtags": ["tag1", "tag2"],
  "slides": [
    { "file_id": "abc123", "label": "封面", "slide_number": 1 },
    { "file_id": "def456", "label": "第2张", "slide_number": 2 }
  ]
}
```

- 单图海报：`slides` 只有一项，`content_type` 填 `"single"`
- 文字帖：`slides` 为空数组，`content_type` 填 `"text"`

**第三步：等用户说「ok」或提出修改意见，确认后再存草稿、生成下一条**

**逐条执行，每条确认后再做下一条，不等全部做完再保存。**

---

## 第四阶段：存储草稿

每条内容生成完毕后，保存到 `/workspace/drafts/`：

文件名格式：`{YYYY-MM-DD}-{platform}-{type}-{slug}.md`

**支持平台（不能漏）：**

| 平台 | 可发内容类型 | 草稿 platform 字段值 |
|---|---|---|
| Instagram | Carousel / 单图海报 / Reels / Story | `instagram` |
| Facebook | Feed（与 IG 同步）/ 单图 | `facebook` |
| LinkedIn | Text Post / Carousel（Document） | `linkedin` |
| Twitter | 推文 / Thread | `twitter` |

每条草稿必须包含：
- `平台`：上表中的字段值
- `内容类型`：Carousel / 单图海报 / Reels / Story / Text / Thread 等
- `状态`：`待发布`
- `计划发布日`：YYYY-MM-DD
- 生成的媒体文件路径或 URL（文字帖可为空）
- 文案（caption）与 Hashtags

草稿存好后，发布由每天 09:00 的 `[cron] 内容发布` 按日期自动扫描处理，无需在此确认。
