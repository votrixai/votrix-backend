---
name: poster-design
description: >
  完整海报设计流程。从零开始设计可直接发布的宣传海报（单张或 Carousel 组图）：情境读取、叙事规划、文案创作、海报 prompt 构建、直接图片生成、质量复查。
  适用于商家需要专门设计海报的场景——新品上架、活动促销、品牌宣传、节日推广等。
integrations: []
---

# 海报设计

## 步骤 1 — 情境读取

按优先级读取所有可用上下文，能推断的直接推断，不询问：

1. `/workspace/marketing-context.md` — 品牌名、行业、调性、品牌构图风格、目标受众、色彩系统
2. 用户消息 — 提取：海报主题、目标受众信号、必须出现的文字

直接确定：
- **模式**：单张海报 or Carousel 组图（从用户消息或平台推断）
- **宣传目的**：说服谁做什么
- **目标受众**：他们的审美习惯和决策心理
- **发布尺寸**：单张从平台推断，推断不出默认 1024×1024；Carousel 固定 896×1120px（4:5）
- **宽高比**：单张从尺寸推断（1024×1024 → `1:1`，1792×1024 → `16:9`，1024×1792 → `9:16`）；Carousel 固定 `4:5`

唯一需要追问的情况：主题完全缺失，无法判断这张海报在宣传什么。

---

## 步骤 1.5 — Carousel 叙事规划（仅 Carousel 时执行）

根据宣传目的选定叙事模式，规划每张的叙事角色。

**节奏**：每套 Carousel 固定遵循 Hook → Content → CTA。

| 位置 | 角色 |
|------|------|
| 第 1 张 | Hook — 用大胆标题或反直觉主张抢停滑动 |
| 第 2–N 张 | Content — 每张只讲一个点，绝不例外 |
| 末张 | CTA — 引导收藏、关注或点击 |

**叙事模式选择**：

```
目的：推广具体产品
  └─ 用幽默种草类，首选「产品救场」
     └─ 检查本次对话已用过的模式，跳过重复，按顺序轮换：
        产品救场 → 避雷种草 → 错误打开方式 → 产品拟人自白 → 夸张测评

目的：品牌宣传 / 内容教育
  └─ 用通用内容类，按目标选：
       收藏率     → 步骤教程、对比盘点
       信任建立   → 数据+评价、问题→解决
       直接行动   → 问题→解决
```

**幽默种草类**：

| 模式 | 一句话说明 | 节奏 |
|------|-----------|------|
| 产品救场 | 先展示痛点，产品来拯救 | 共鸣痛点 → 升级恶化 → 产品登场 → 前后对比 → CTA |
| 避雷种草 | "千万别买"逆向心理——越劝越想要 | 警告封面 → 列出"缺点"（实为卖点）→ 反转推荐 → 购买CTA |
| 错误打开方式 | 展示错误用法，再揭示正确体验 | "别这样做" → 错误后果 → 正确用法 → 满意对比 → CTA |
| 产品拟人自白 | 产品第一人称"抱怨"被低估 | "没人知道我能…" → 逐张功能揭秘 → 用户惊喜反应 → CTA |
| 夸张测评 | 夸张放大产品效果制造喜感 | 离谱承诺封面 → 逐项测试 → 戏剧反应 → 诚实结论 → CTA |

**通用内容类**：

| 模式 | 一句话说明 | 节奏 |
|------|-----------|------|
| 步骤教程 | 每张一步，滑完即学会 | 问题 → 步骤1 → 步骤2 → 步骤3 → 收藏CTA |
| 对比盘点 | 每张一个选项并排展示 | 封面 → A → B → C → 推荐 |
| 问题→解决 | 先戳痛点再给解法 | 痛点 → 根因 → 解决方案 → 行动CTA |
| 数据+评价 | 数字、截图、用户反馈建立信任 | 数据封面 → 证据 → 用户证言 → 尝试CTA |

输出规划表：

| 张 | 叙事角色 | 一句话主题方向 |
|----|----------|--------------|
| 1 | Hook | ... |
| 2–N | 单点内容 | 每张只讲一件事 |
| 末张 | CTA | 行动指引 |

**告知用户每张叙事角色和主题方向，等待确认后再继续。**

---

## 步骤 2 — 文案创作

根据宣传目的和确认的叙事结构，写出所有文字内容。

**单张**：
- 主标题
- 副标题（可选）
- 卖点标签（可选，2–4 个）
- 价格（若有）
- CTA 文字

**Carousel**：按叙事规划表逐张写完整文案——
- 每张：大标题 + 说明文字（1–2 行）+ 可选小标签

写完后**呈现给用户确认**，确认后才继续。

---

## 步骤 3 — 锁定视觉参数（全程不变）

在任何生成之前，先锁定以下参数。Carousel 所有张必须使用完全相同的值，不因每张主题不同而调整。

**Style**：始终默认 `photographic`。仅当用户明确指定其他风格名称时才切换（`anime`、`cinematic`、`digital-art` 等）。不接受「插画」「卡通」等笼统描述。

**Mood**：描述整套图的色温与光影氛围——不是每张的情绪，而是让所有张看起来出自同一套视觉语言的底色。例如 `warm amber tones, dramatic contrast` 或 `cool dark tones, premium studio lighting`。从品牌调性和步骤 2 确认的配色推断，锁定后不更改。

**Negative elements**：
- 基础：`watermark, busy background, cluttered, multiple competing subjects, decorative noise`
- 有人物时追加：`extra fingers, extra limbs, fused limbs, disfigured face, extra eyes, distorted face, anatomical distortion, malformed hands`
- ⚠️ 不排除 `text / typography`——poster-complete context 需要模型渲染文字

写下锁定值，后续所有步骤直接复用，不重新决策。

---

## 步骤 4 — 构建完整海报 Prompt

将品牌信息、画面场景、构图布局、配色、文案、排版风格整合为一段英文 prompt。每张单独写 prompt，但场景风格和视觉调性描述保持一致，只有文字内容和叙事重点随叙事角色变化。

按以下顺序组织，写成连续叙述性段落：

**① 海报类型与品牌**：说明这是什么类型的广告海报、面向什么产品/品牌。

**② 画面场景**：什么环境、有无人物、整体氛围，与品牌调性一致，写实全彩。

**③ 构图布局**：明确文字区和画面区的位置关系，例如：
- 左侧大块放文字，右侧为场景
- 顶部 60% 为画面，底部 40% 深色文字区
- 全画面背景 + 底部渐变区承载文字
- 纯深色背景，文字居中

**④ 配色与视觉风格**：背景色调（深/浅/品牌色），整体 premium / minimal / bold 感，光影氛围。

**⑤ 文字内容与排版**：逐一列出所有需要出现的文字，注明每段的视觉权重（大/中/小标题）、颜色（白/深/强调色）、位置。文字颜色必须与背景高对比。

**⑥ 品牌元素**（如有）：Logo 位置、吉祥物。

**⑦ 整体质感**：`High contrast, premium, commercial poster quality, sharp typography, photorealistic photography.`

### 参考格式

```
Create a [vertical/horizontal] advertising poster for [Brand Name]. Scene: [场景描述, realistic full color]. Composition: [文字区和画面区位置关系]. Brand/style: [Modern premium / bold / minimal], [dark/light] background layout. All poster text should be [white/dark] only. Main headline: "[主标题]". Subheadline: "[副标题]". Benefit blocks: "[卖点1]", "[卖点2]", "[卖点3]". CTA: "[CTA文字]". Visual tone: High contrast, premium, clean, commercial poster design, realistic photography with sharp typography.
```

### Carousel 各张差异

每张 prompt 完全独立——场景、构图、文案都可以不同，按叙事角色各自描述：
- Hook 张：强视觉冲击的场景，文案聚焦痛点或悬念，主标题大
- Content 张：配合该点内容的场景，文案只讲一个点，排版清晰
- CTA 张：可以是纯深色背景 + 大字，不需要任何场景图

**不变的只有步骤 3 的锁定值**：style / mood / negative_elements 在所有张完全相同，这是让各张视觉上感觉出自同一套设计的底层保证。

---

## 步骤 5 — 生成海报图片

### 第 1 张（单张海报 / Carousel 第 1 张）

调用 `image_generate`：

| 参数 | 取值 |
|------|------|
| `prompt` | 步骤 4 构建的第 1 张完整海报 prompt |
| `style` | 步骤 3 锁定值 |
| `mood` | 步骤 3 锁定值 |
| `negative_elements` | 步骤 3 锁定值 |
| `context` | `poster-complete` |
| `aspect_ratio` | 步骤 1 确定的宽高比 |
| `reference_image_urls` | 用户在对话中提供了参考图时传入；否则不传 |

生成后立即进入步骤 6 质检。通过后：
1. 告知用户：确认第 1 张已通过，说明构图和视觉效果
2. 记录第 1 张 URL 为**风格锚 URL**
3. 提取**风格锚描述**——描述实际渲染出来的（不是意图中的）：
   - 色温与调色盘（如 `warm amber highlights, muted shadows`）
   - 光影风格（如 `soft diffused light`, `dramatic side lighting`）
   - 质感与景深（如 `shallow depth of field, slight film grain`）

单张海报到此结束，进入输出步骤。

---

### 第 N 张（Carousel，N ≥ 2）

每张独立完整地调用 `image_generate`，当前张通过质检后才开始下一张。

| 参数 | 取值 |
|------|------|
| `prompt` | 步骤 4 构建的第 N 张完整海报 prompt（该张自己的场景+文案+构图） |
| `style` | 步骤 3 锁定值（不变） |
| `mood` | 步骤 3 锁定值（不变，不因该张叙事角色调整） |
| `composition` | 该张的构图描述 + 追加风格锚描述（保持视觉语言一致） |
| `negative_elements` | 步骤 3 锁定值（不变） |
| `context` | `poster-complete` |
| `aspect_ratio` | 步骤 1 确定的宽高比（不变） |
| `reference_image_urls` | **始终传第 1 张 URL**——不是上一张，永远是第 1 张 |

生成后立即进入步骤 6 质检。通过后告知用户，再生成第 N+1 张。

不合格：调整当前张 prompt 或 composition 重新生成，最多重试 3 次。3 次仍不过 → 说明卡在哪项，继续下一张。

---

## 步骤 6 — 质量复查

每张生成后立即执行，不合格立即重新生成（调整 prompt），最多重试 3 次。

| 检查项 | 合格标准 | 不合格处理 |
|--------|---------|----------|
| 文案完整 | 步骤 2 确认的所有文字都出现在图中 | 在 prompt 中强调缺失的文字，重新生成 |
| 文字清晰 | 标题和正文清晰可读，无乱码、无模糊 | prompt 加入 `crisp sharp legible text` 重新生成 |
| 文字对比度 | 文字与背景之间对比度足够，视觉上清晰 | prompt 调整文字颜色或背景描述 |
| 构图符合 | 文字区域和画面区域位置与预期一致 | 重新描述构图，更明确地指定区域位置 |
| 风格一致 | Carousel 各张视觉风格统一 | 强化 reference 图使用，调整 mood 描述 |
| 无不相关元素 | 无水印、无无关 logo、无杂乱视觉噪点 | prompt 加入 `no watermark, no clutter` |

**解剖检查**——仅当图中含有人物或动物时执行：

| 检查项 | 合格标准 | 不合格处理 |
|--------|---------|----------|
| 肢体数量 | 手臂、腿、耳朵数量正确 | prompt 追加正向修正 + negative_elements 追加对应负向词，重新生成 |
| 手指数量 | 每只人手恰好五根手指 | prompt 加 `anatomically correct hands, five fingers`，negative_elements 加 `extra fingers` |
| 面部结构 | 眼睛、鼻子、嘴巴清晰独立，无重叠或重复 | prompt 加 `natural face structure`，negative_elements 加 `distorted face, extra eyes` |
| 肢体边界 | 无融合、粘连或悬浮的肢体 | prompt 加 `clear limb separation`，negative_elements 加 `fused limbs, floating limbs` |

3 次后仍有问题 → 说明卡在哪项，请求用户进一步指导。

---

## 输出

调用 `show_post_preview` 工具展示海报：
- **单张**：`slides: [{ path: "<生成图URL>", label: "海报" }]`
- **Carousel**：`slides` 按张传入所有 URL，`label` 标注第几张及叙事角色（如"第 1 张 · Hook"）
- `caption`：一句话说明核心设计决策
- `hashtags`：`[]`
