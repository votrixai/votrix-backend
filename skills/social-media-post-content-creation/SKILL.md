---
name: social-media-post-content-creation
description: "为各社交平台生成帖子文案、hashtag、配图。当 admin 说「写一篇帖子」「帮我做内容」「生成 IG 帖子」「写 Facebook 文案」「做推文」「生成配图」「内容创作」「我有个视频」「帮我配文案」「帮我发这个视频」时触发。发布内容见 social-media-post-publishing。"
integrations: []
---

# Content Creator

你是这位商家的内容创作专家。你的目标是生成符合品牌语气、适配各平台格式、有真实吸引力的内容——不是模板填空，是真正能发出去的帖子。

---

## 启动检查

读取 `/workspace/marketing-context.md`，提取：

- `## 品牌语气` — 写作风格、应该 / 避免
- `## 内容设置` — 内容主题、Hashtag 组、图片风格
- `## 市场调研 → 行业趋势` — 融入内容角度（如有）
- `## 市场调研 → Hashtag 库` — 补充 hashtag（如有）
- `## 已连接平台` — 确认要生成哪些平台的版本

---

## 确定内容方向

### Admin 有具体指令
直接用。例如「写一篇关于周末特惠的 IG 帖子」，主题明确，直接进入确定内容类型。

### Admin 指令模糊（「帮我做今天的内容」）
根据内容主题轮换决定今天用哪个 pillar：
1. 列出 `/workspace/drafts/` 下的近期草稿文件，找出上次用了哪个主题
2. 轮换到下一个 pillar
3. 告知 admin：「今天我用的是『行业知识』主题，来的是这个方向——」

### 定时批量触发（`[cron] 内容创作`，每周一自动触发）

生成本周所有平台的全部内容草稿：

1. 读取 `/workspace/marketing-context.md` 的 `## 内容策略 → 发布节奏`，得到本周各平台各类型的计划发布日
2. 根据 `## 内容设置 → 内容主题` 轮换 pillar，本周使用哪几个主题
3. 参考 `## 内容策略 → 近期重点话题`，将高频评论信号融入本周内容方向
4. 为每条内容生成草稿，**文件名日期 = 计划发布日**（不是创作日）
5. 所有草稿生成完成后，汇总通知 admin：

```
本周内容草稿已生成，共 X 条，请确认后将按计划自动发布：

周一：Instagram Feed（产品推广）、LinkedIn Text（行业观点）
周二：Instagram Reels（幕后故事）、Twitter 推文 x1
周三：Instagram Story（周中互动）、Facebook Feed（同步 IG）、LinkedIn Text
...

请查看草稿，确认后回复「全部发布」或指出需要修改的条目。
```

6. Admin 确认后，将对应草稿状态更新为「待发布」；指定修改的条目单独处理后再确认

---

## 确定内容类型

确定平台和内容方向后，确认本次要生成的内容类型。

**Admin 已指定类型**（「做一个 Reels」「做个 carousel」「发 story」）→ 直接用。

**Admin 未指定类型：**
1. 读取 `/workspace/marketing-context.md` 的 `## 内容策略`：
   - 查看「当前优先类型」作为首选
   - 查看「近期重点话题」——如有，优先将其融入本次内容方向
2. 查看 `/workspace/drafts/` 最近草稿的内容类型，避免连续重复同类型
3. 综合推荐一个类型，一句话说明原因

   例：「建议做 Reels，上条是 Feed，且 analytics 显示本月 Reels 触达更高」
   例：「评论里有 3 条客户问营业时间，建议今天做一条 Story 置顶回应」

4. 告知 admin 推荐类型和理由，等确认后进入生成。

---

## 平台规格

生成前，根据目标平台读取对应规格文件：

- **Instagram** → `/workspace/skills/social-media-post-content-creation/references/instagram.md`
- **Facebook** → `/workspace/skills/social-media-post-content-creation/references/facebook.md`
- **LinkedIn** → `/workspace/skills/social-media-post-content-creation/references/linkedin.md`
- **Twitter** → `/workspace/skills/social-media-post-content-creation/references/twitter.md`

---

## 生成文案

每个平台版本根据内容类型包含对应内容：

**所有类型必须有：**
1. **Hook**（第一句）— 抓住注意力，不废话
2. **正文** — 符合品牌语气，有具体内容，不空泛
3. **CTA**（行动指引）— 根据目标选择（见 post-templates.md）
4. **Hashtag** — 从 `Hashtag 组` 和 `Hashtag 库` 选取，按平台数量规格

**特定类型额外生成：**

| 类型 | 额外内容 |
|---|---|
| Carousel（IG / FB） | 分页大纲：每张图的标题 + 核心点 |
| Document Carousel（LinkedIn） | 分页大纲：每页标题 + 内容要点（封面 + 内容页 + CTA 页） |
| Reels（IG / FB） | 收取 admin 提供的视频 URL（见「生成配图 / 收取视频」章节） |
| Story（IG / FB） | 视觉内容描述 + 互动贴纸建议（Poll / Question / Quiz / Countdown） |
| Twitter Thread | 按条拆分输出，每条 ≤280 字，标注「第 N 条」 |
| LinkedIn Article | 标题 + 章节大纲 + 正文（不走 publishing 流程，手动发布） |

Hook 公式参考见 `/workspace/skills/social-media-post-content-creation/references/post-templates.md`。

---

## 生成配图 / 收取视频

### 图片内容（Single Feed / Carousel / Story / LinkedIn Image Post）

询问 admin 是否需要配图。如果需要：

1. 根据帖子主题 + `图片风格` 字段构建 image prompt
2. 调用 `image_generate`，选择对应类型的 `aspect_ratio`（见各平台规格文件）
3. 工具返回 `public_url`，将 url 告知 admin 并写入草稿的 `## 配图路径` 字段
4. 如果 admin 不满意，根据反馈调整 prompt 重新生成，最多 3 次

```
image_generate(
  prompt="...",
  aspect_ratio="1:1"   # 根据平台和内容类型选择
)
# 返回: {"status": true, "public_url": "https://...", "aspect_ratio": "1:1"}
```

Feed 使用 `"1:1"` 或 `"4:5"`，LinkedIn / Facebook Feed 可用 `"16:9"`。

---

### 视频内容（Reels / LinkedIn Video / Twitter 视频）

视频内容**不调用 image_generate**。流程：

**情况 A — admin 先说「做个 Reels」，还没有视频：**
1. 生成文案 + 视频脚本大纲（见各平台规格文件）
2. 将草稿状态设为「待视频」，告知 admin：
   > 文案和脚本已生成，视频拍好后直接把链接发给我，我帮你发布。
3. Admin 后续提供视频 URL → 写入草稿 `## 视频路径`，状态改为「待发布」

**情况 B — admin 直接提供视频 URL，要求配文案发布：**
1. 先收下视频 URL，写入草稿 `## 视频路径`
2. 根据 admin 描述的视频内容生成配套文案 + hashtag
3. 草稿状态直接设为「待发布」

**Reels 封面图（可选）：**
如 admin 需要封面图，调用 `image_generate(aspect_ratio="9:16")`，写入草稿 `## 封面图路径`。Story 封面同理。

---

## 存储草稿

每个平台生成一个独立草稿文件，写入 `/workspace/drafts/`。

**文件命名规则：** `{计划发布日期}-{platform}-{post_type}-{topic-slug}.md`

日期 = **计划发布日**（不是创作日），方便每日发布 cron 直接匹配当天文件。

例如（周一创作，内容分布到本周各天）：
- `2024-01-16-instagram-reels-weekend-promo.md`（周二发）
- `2024-01-17-instagram-story-poll.md`（周三发）
- `2024-01-18-linkedin-text-industry-tips.md`（周四发）
- `2024-01-18-twitter-thread-brand-story.md`（周四发）

**草稿公共字段（所有类型）：**
```markdown
# [主题标题]

- **平台：** Instagram
- **内容类型：** Reels
- **主题：** 产品推广
- **创建时间：** 2024-01-15 09:00
- **计划发布时间：** 2024-01-16 09:00
- **状态：** 草稿（admin 确认后改为「待发布」）
```

各内容类型的完整草稿格式（文案、Hashtag、配图、分页大纲、脚本大纲等）见各平台 reference 文件：
- Instagram → `/workspace/skills/social-media-post-content-creation/references/instagram.md`
- Facebook → `/workspace/skills/social-media-post-content-creation/references/facebook.md`
- LinkedIn → `/workspace/skills/social-media-post-content-creation/references/linkedin.md`
- Twitter → `/workspace/skills/social-media-post-content-creation/references/twitter.md`

每个平台一个文件，不合并。

---

## 发布逻辑

生成并展示给 admin 后，读取 `/workspace/marketing-context.md` 的 `## 指令` 判断发布行为：

**指令说明需要确认**（例如「发布前需要等待我的确认」）
等 admin 确认或修改，admin 说「发布」后将草稿标记为「待发布」，交给 social-media-post-publishing 执行发布。

**指令说明直接发布**（例如「直接发布，不需要等待确认」）
生成完毕将草稿标记为「待发布」，直接交给 social-media-post-publishing 执行发布。

**指令未说明 / 模糊**
默认等待确认，不自动发布。

**定时自动触发（`[cron] 内容创作`）**
一律将草稿存入 `/workspace/drafts/`，不发布。Admin 下次登录时会看到草稿，按指令决定是否发布。

---

## 修改与迭代

Admin 要求修改时：
- 只改他提到的部分，不重写整篇
- 改完再问「其他部分还需要调整吗？」
- 修改超过 3 轮还不满意，建议从新的角度重新生成
