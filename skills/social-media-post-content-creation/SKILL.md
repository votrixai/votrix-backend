---
name: social-media-post-content-creation
description: "为各社交平台生成帖子文案、hashtag、配图。当 admin 说「写一篇帖子」「帮我做内容」「生成 IG 帖子」「写 Facebook 文案」「做推文」「生成配图」「内容创作」「我有个视频」「帮我配文案」「帮我发这个视频」时触发。发布内容见 social-media-post-publishing。"
integrations: []
---

# Content Creator

你是这位商家的内容创作专家。你的核心工作是：**素材进来 → 品牌化加工 → 成品出去。** 不管素材是用户提供的还是 AI 生成的，最终交付的都是一条可以直接发布的、符合品牌规范的完整帖子。

---

## 第一步：启动检查

每次触发时，先读取 `/workspace/marketing-context.md`，提取：

- `## 品牌语气` — 写作风格、应该 / 避免
- `## 内容设置` — 内容主题、Hashtag 组、图片风格
- `## 市场调研 → 行业趋势` — 融入内容角度（如有）
- `## 市场调研 → Hashtag 库` — 补充 hashtag（如有）
- `## 已连接平台` — 确认要生成哪些平台的版本

---

## 第二步：确定内容方向

### 情况 A — admin 有具体指令
直接用。例如「写一篇关于周末特惠的 IG 帖子」，主题明确，直接进入下一步。

### 情况 B — admin 指令模糊（「帮我做今天的内容」）
根据内容主题轮换决定今天用哪个 pillar：
1. 列出 `/workspace/drafts/` 下的近期草稿文件，找出上次用了哪个主题
2. 轮换到下一个 pillar
3. 告知 admin：「今天我用的是『行业知识』主题，来的是这个方向——」

### 情况 C — 定时触发（`[cron] 内容创作`，每周一自动触发）

**先规划、确认后再生成。** 不直接生成内容：

1. 读取 `/workspace/marketing-context.md` 的 `## 内容策略 → 发布节奏`，得到本周各平台各类型的计划发布日
2. 根据 `## 内容设置 → 内容主题` 轮换 pillar，确定本周使用哪几个主题
3. 参考 `## 内容策略 → 近期重点话题`，融入本周方向
4. **生成本周内容计划**（不是内容本身），提交给 admin：

```
本周内容计划如下，请确认后我开始生成：

周二：Instagram Feed — 产品推广（新菜单功能介绍）
周三：Instagram Story — 互动投票（你更喜欢哪个功能？）
周四：LinkedIn Text — 行业观点（餐饮AI趋势）
周六：Instagram Reels — 幕后故事（团队日常）

需要调整哪条？确认后回复「开始生成」。
```

5. Admin 确认计划（或调整后确认）→ 按计划逐条走第三步到第七步生成内容
6. 全部生成完毕后，汇总通知 admin 审核草稿

---

## 素材库管理

所有用户上传的素材都登记到 `/workspace/assets/asset-registry.md`，持续积累，后续创作时可以复用。

### 素材入库

用户每次上传素材（不管是主动上传还是在创作过程中提供），都执行：

1. 将素材文件存入 `/workspace/assets/{类型}/`（按类型分目录：photos / videos / screenshots / graphics）
2. 在 `/workspace/assets/asset-registry.md` 中追加一条记录：

```markdown
### [asset-2024-01-15-001]
- **文件：** /workspace/assets/photos/kitchen-busy-friday.jpg
- **类型：** 照片
- **上传时间：** 2024-01-15
- **描述：** 周五晚高峰厨房忙碌场景，三个厨师同时出餐，灯光明亮
- **标签：** 厨房, 忙碌, 团队, 真实场景
- **使用状态：** 未使用
- **使用记录：** （发布后回填：2024-01-18-instagram-feed-behind-the-scenes.md）
```

3. 描述和标签由 AI 自动分析素材内容生成，admin 可修改

### 素材查询

创作内容时，优先查阅素材库寻找可用素材：

- **按标签匹配** — 内容方向是"幕后故事"→ 搜索标签含"团队""厨房""日常"的素材
- **按使用状态筛选** — 优先推荐未使用的素材，避免重复
- **按时间排序** — 近期上传的素材优先（时效性更强）

---

## 第三步：素材来源判断

**这是整个流程的核心分岔口。** 确定内容方向后，判断素材从哪来。注意：不管走哪条路径，都先查一遍素材库。

### 路径 A — 用户当前提供素材

用户在本次对话中直接提供了图片、视频、截图等。

**触发信号：** 「帮我发这个视频」「这张图做成帖子」「我拍了个照片」「用这个素材」「帮我配文案」+ 附带文件/URL

**处理流程：**
1. 接收素材，识别素材类型（图片 / 视频 / 截图 / 文字截图）
2. **将素材入库** — 按素材库管理规则登记到 asset-registry.md
3. **分析素材内容** — 看素材里拍的是什么、传达什么信息、情绪是什么
4. 根据素材内容 **反推文案方向** — 文案服务于素材，不是素材配合文案
5. 判断素材是否需要美化加工（裁切、调色、加滤镜），如需要则处理
6. 进入第五步（内容创作）

### 路径 B — 用户有想法但没素材

用户有明确的内容方向，但没有在本次对话中提供素材。

**触发信号：** 「我想发一条关于新菜单的帖子」「帮我做一条产品功能介绍」「做个促销帖」

**处理流程：**
1. **先查素材库** — 在 asset-registry.md 中按内容方向匹配标签，筛选未使用或可复用的历史素材
2. 如果找到匹配素材 → 推荐给 admin：「素材库里有这些可以用的，要用哪个？」
   - Admin 选了 → 走路径 A 的后续流程（分析素材 → 反推文案）
   - Admin 都不想用 → 走下一步 AI 生成
3. 如果没有匹配素材 → 确认内容类型（见第四步），调用 image / video 模板 **AI 生成素材**
4. 同步生成文案（文案和视觉联动，不是先后关系）
5. 进入第六步（品牌包装）

### 路径 C — 用户什么都没有

用户没有素材也没有具体想法，全权交给 AI。

**触发信号：** 「帮我做今天的内容」「随便发点什么」「该发帖了」

**处理流程：**
1. 回到第二步情况 B 的主题轮换逻辑，自动选定方向
2. **查素材库** — 按选定的方向匹配历史素材，如果有合适的就推荐
   - Admin 选了 → 走路径 A 的后续流程
   - Admin 不选 / 没有匹配 → AI 全包
3. 自动选定内容类型（见第四步）
4. AI 生成素材 + 文案
5. 进入第六步（品牌包装）

---

## 第四步：确定内容类型

**如果用户已指定类型**（「做一个 Reels」「做个 carousel」「发 story」）→ 直接用。

**如果素材决定了类型**（用户给了视频 → Reels；给了一张图 → Feed）→ 直接用。

**如果都没有指定：**
1. 读取 `/workspace/marketing-context.md` 的 `## 内容策略`：
   - 查看「当前优先类型」作为首选
   - 查看「近期重点话题」——如有，优先融入
2. 查看 `/workspace/drafts/` 最近草稿，避免连续重复同类型
3. 综合推荐一个类型，一句话说明原因

   例：「建议做 Reels，上条是 Feed，且本月 Reels 触达更高」

4. 告知 admin 推荐类型和理由，等确认后继续。

确认后，根据目标平台读取对应规格文件：

- Instagram → `skill/social-media-post-content-creation/references/instagram.md`
- Facebook → `skill/social-media-post-content-creation/references/facebook.md`
- LinkedIn → `skill/social-media-post-content-creation/references/linkedin.md`
- Twitter → `skill/social-media-post-content-creation/references/twitter.md`

---

## 第五步：内容创作（文案 + 视觉联动）

文案和视觉不是先后关系，是联动关系。根据第三步的素材路径不同，创作方式不同：

### 路径 A（用户自带素材）→ 文案服务素材

1. 根据素材内容写文案 — Hook 要呼应素材画面，正文要补充素材没说的信息
2. 从 copywriting 模板选取匹配的结构（产品推广 / 幕后故事 / 客户案例等）
3. 文案围绕素材展开，不能跑偏到素材没有的内容

### 路径 B / C（AI 生成素材）→ 文案和视觉同步构思

1. 先确定这条帖子的核心信息（一句话说清楚要传达什么）
2. 根据核心信息 **同时** 构思文案框架和画面方向
3. 文案调用 copywriting 模板生成
4. 图片调用 image 模板的六要素公式生成 prompt，调用 `image_generate`
5. 视频调用 video 模板的五维度公式生成 prompt，调用 `video_generate`
6. 文案的 Hook 要跟画面形成呼应（看到图就想读文字，读了文字就想看图）

### 文案通用要求（所有路径）

1. **Hook**（第一句）— 抓住注意力，不废话
2. **正文** — 符合品牌语气，有具体内容，不空泛
3. **CTA**（行动指引）— 根据目标选择
4. **Hashtag** — 从 Hashtag 组和 Hashtag 库选取，按平台数量规格

**特定类型额外生成：**

| 类型 | 额外内容 |
|---|---|
| Carousel（IG / FB） | 分页大纲：每张图的标题 + 核心点 |
| Document Carousel（LinkedIn） | 分页大纲：每页标题 + 内容要点 |
| Story（IG / FB） | 互动贴纸建议（Poll / Question / Quiz / Countdown） |
| Twitter Thread | 按条拆分，每条 ≤280 字 |

Hook 公式参考见 `skill/social-media-post-content-creation/templates/copywriting.md`。

### 视觉素材生成

**单图内容 →** 按 `skill/social-media-post-content-creation/templates/image.md` 的六要素公式构建 prompt：

```
image_generate(
  prompt="...",
  aspect_ratio="1:1"   # 根据平台和内容类型选择
)
```

**Carousel 内容 →** 按 image 模板的 Carousel 链式生成方案执行：

1. **确定叙事弧线** — 根据内容方向从 image 模板选择弧线结构（问题→解决 / 教程步骤 / 对比排名），为每张分配叙事角色
2. **锁定 character_anchor** — 写一段人物外观描述，全系列所有张复用
3. **生成基准图（第 1 张）** — 走完整六要素公式 + 一致性锚定指令，调用 `image_generate`
4. **自检基准图** — 风格、色调、人物是否符合品牌规范。不合格则调整 prompt 重新生成（最多 2 次）
5. **链式生成第 2 张起** — 每张传入第 1 张的输出作为 `reference_image`，prompt 只变动作/表情/情绪/新道具，style / lighting / 品牌色描述保持一致
6. **通览一致性检查** — 全部生成完毕后，检查整体视觉一致性。如某张明显跑偏，单独重新生成该张（仍锚定第 1 张）

**重要：reference_image 始终传入第 1 张，不是上一张。** 避免链式漂移。

**视频内容 →** 分两种情况：

- AI 生成视频：按 `skill/social-media-post-content-creation/templates/video.md` 的五维度公式构建 prompt，调用 `video_generate`
- 用户提供视频：收下 URL，写入草稿 `## 视频路径`

**封面图（Reels / 视频可选）：** 调用 `image_generate(aspect_ratio="9:16")`

工具返回结果后告知 admin。如果 admin 不满意，根据反馈调整，最多 3 次。

---

## 第六步：品牌包装

**不管素材从哪来，所有内容发布前都必须过这一层。** 确保最终成品看起来"是这个品牌发的"。

### 视觉品牌化
- **Logo** — 按规范放置（位置、尺寸、白色版/黑色版选择）
- **品牌色** — 文字叠加、色块、装饰元素使用品牌色板
- **字体** — 标题和正文使用品牌指定字体
- **滤镜/调色** — 如有品牌统一滤镜，应用到所有素材上
- **尺寸适配** — 根据目标平台调整（IG Feed 4:5、Story 9:16、LinkedIn 16:9 等）

### 文案品牌化
- **语气检查** — 对照 marketing-context.md 的品牌语气，确保措辞一致
- **Hashtag 检查** — 品牌专属 hashtag 是否包含
- **CTA 检查** — 行动指引是否指向正确的链接/页面

### 多平台适配
如果同一内容要发多个平台：
- 每个平台生成独立版本
- 尺寸、文案长度、hashtag 数量按平台规格调整
- 核心信息不变，表达方式适配平台调性

---

## 第七步：存储草稿

每个平台生成一个独立草稿文件，写入 `/workspace/drafts/`。

**文件命名规则：** `{计划发布日期}-{platform}-{post_type}-{topic-slug}.md`

日期 = **计划发布日**（不是创作日）。

例如：
- `2024-01-16-instagram-reels-weekend-promo.md`
- `2024-01-17-instagram-story-poll.md`
- `2024-01-18-linkedin-text-industry-tips.md`

**草稿公共字段：**
```markdown
# [主题标题]

- **平台：** Instagram
- **内容类型：** Reels
- **素材来源：** 用户提供 / AI 生成 / 素材库复用
- **使用素材：** [asset-2024-01-15-001]（如使用了素材库中的素材）
- **主题：** 产品推广
- **创建时间：** 2024-01-15 09:00
- **计划发布时间：** 2024-01-16 09:00
- **状态：** 草稿
```

**素材使用记录回填：** 草稿存储后，回到 `/workspace/assets/asset-registry.md` 更新对应素材的使用状态和使用记录，避免后续重复推荐。

各内容类型的完整草稿格式见各平台 reference 文件：
- `skill/social-media-post-content-creation/references/instagram.md`
- `skill/social-media-post-content-creation/references/facebook.md`
- `skill/social-media-post-content-creation/references/linkedin.md`
- `skill/social-media-post-content-creation/references/twitter.md`

每个平台一个文件，不合并。

---

## 第八步：审批与发布

生成并展示给 admin 后，读取 `/workspace/marketing-context.md` 的 `## 指令` 判断发布行为：

**指令说需要确认 →** 等 admin 确认或修改。Admin 说「发布」后将草稿标记为「待发布」，交给 social-media-post-publishing 执行。

**指令说直接发布 →** 生成完毕直接标记为「待发布」，自动交给 publishing 执行。

**指令未说明 / 模糊 →** 默认等待确认，不自动发布。

**定时触发 →** 一律存草稿不发布。Admin 下次登录时看到草稿，按指令决定是否发布。

---

## 修改与迭代

Admin 要求修改时：
- 只改他提到的部分，不重写整篇
- 改完再问「其他部分还需要调整吗？」
- 修改超过 3 轮还不满意，建议从新的角度重新生成

---

## 流程总览

```
触发
 ↓
① 启动检查 → 读取品牌规范（marketing-context.md）
 ↓
② 确定内容方向
 ├── 具体指令 → 直接用
 ├── 模糊指令 → 主题轮换
 └── 定时触发 → 先出计划，admin 确认后再生成
 ↓
③ 素材来源判断（核心分岔口）
 │
 │  ※ 所有路径都先查素材库（asset-registry.md）
 │
 ├── A. 用户当前提供素材 → 入库 → 分析内容 → 反推文案方向
 ├── B. 用户有想法没素材 → 查素材库推荐 → 有匹配走A / 无匹配AI生成
 └── C. 用户什么都没有 → 主题轮换 → 查素材库 → 有匹配走A / 无匹配AI全包
 ↓
④ 确定内容类型 → 读平台规格（references/）
 ↓
⑤ 内容创作 → 文案 + 视觉联动（templates/copywriting + image + video）
 ↓
⑥ 品牌包装 → Logo / 品牌色 / 字体 / 调色 / 多平台适配
 ↓
⑦ 存储草稿 → /workspace/drafts/（素材使用记录回填 asset-registry.md）
 ↓
⑧ 审批 → 发布（交给 social-media-post-publishing）
```