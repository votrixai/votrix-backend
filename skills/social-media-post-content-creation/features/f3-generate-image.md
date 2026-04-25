# F3 — 文字描述生成图片素材

**适用场景**：商家没有现成照片，只有文字描述，AI 用 Gemini 生成图片素材。

**核心工具**：Gemini `gemini-3.1-flash-image-preview`

**注意**：F3 只生成静态图片。如果需要生成视频，使用 F4。

---

## 步骤 1：收集信息

确认以下信息，缺什么问什么：

- **内容主题**：商家想表达什么，越具体越好
- **目标用途**：单图发布 / Carousel（需要几张）/ 作为 F1 海报的背景
- **目标平台**：决定尺寸
  - Instagram Feed / 小红书：1080×1080 或 1080×1350（4:5）
  - Instagram Story / 抖音 / 微信朋友圈竖版：1080×1920（9:16）
  - LinkedIn / Facebook Wide：1920×1080（16:9）
  - 未指定默认：1080×1080（1:1）
- **品牌规范**：是否有 `/workspace/marketing-context.md`（有则自动读取，没有则询问品牌色 + 行业 + 品牌调性）

---

## 步骤 2：读取品牌规范

从 `marketing-context.md` 提取以下信息：

- `## 品牌语气` → 决定视觉调性（幽默？专业？温情？）
- `## 内容设置 → 图片风格` → 锁定默认风格关键词
- `## 品牌色` → 提取主色、辅色、强调色色值
- `## 行业` → 推导具体场景（餐饮→厨房/柜台，美容→店面/工作台，科技→办公室/屏幕）

**没有 marketing-context.md 时的默认值：**

| 项目 | 默认值 |
|------|--------|
| 品牌调性 | 幽默搞笑 |
| 图片风格 | 写实摄影 |
| 品牌色 | 用户提供，或留空不强制注入 |
| 行业 | 从用户描述的内容主题推断 |

---

## 步骤 3：设计剧本（Carousel 专用，单图跳过）

### 3.1 选叙事弧线

根据内容方向选择弧线结构，**默认使用弧线 A（问题→解决，幽默搞笑写实风格）**：

#### 弧线 A — 问题→解决（默认）

| 张数 | 叙事角色 | 情绪 | 画面方向 |
|------|---------|------|---------|
| 1（封面） | Hook — 抛出问题 | 紧张/共鸣 | 人物 + 行业痛点信号，表情夸张 |
| 2 | Escalate — 问题放大 | 加剧 | 特写痛点细节（手忙脚乱/堆积/混乱） |
| 3 | Peak — 崩溃顶点 | 最高 | 最戏剧化的瞬间 |
| 4 | Turn — 转折出现 | 意外 | 品牌元素/产品/工具入场 |
| 5 | Relief — 问题解决 | 轻松 | 同一场景恢复秩序，人物放松 |
| 6（CTA） | 收尾 — 行动指引 | 信任 | 产品/Logo + 干净背景 |

#### 弧线 B — 教程/步骤

| 张数 | 叙事角色 | 画面方向 |
|------|---------|---------|
| 1（封面） | 成品展示 — 先看结果 | 最终效果的漂亮展示 |
| 2-5 | Step 1-4 — 过程拆解 | 每步一个关键动作，同场景同人物 |
| 6（CTA） | 总结 + 行动指引 | 回到成品 + 品牌信息 |

#### 弧线 C — 对比/排名

| 张数 | 叙事角色 | 画面方向 |
|------|---------|---------|
| 1（封面） | 抛出问题 — "你知道吗？" | 引发好奇的画面 |
| 2-5 | 逐项展示 | 每项一个场景，同构图框架不同内容 |
| 6（CTA） | 结论 + 行动指引 | 胜出项 + 品牌收尾 |

**张数可调整：** 以上按 6 张示例，实际可以是 4-10 张。保持"封面→中间递进→CTA 收尾"的基本结构。

---

### 3.2 锁定 character_anchor（人物锚点）

写一段固定描述，**全系列所有张都原样重复使用**，确保人物外观一致：

```
character_anchor = "[性别] [年龄段] [行业角色], wearing [服装颜色+款式],
[发型], [体型], [其他显著外观特征]"
```

**构建规则：**
- 从行业推导人物角色（餐饮→厨师/服务员，美容→美容师/顾客，健身→教练/学员）
- 服装颜色尽量使用品牌色
- 描述要足够具体，让不同帧的生成结果能对上同一个人
- **每张 prompt 的主体开头都粘贴这段描述，只改动作部分**

---

### 3.3 告知用户

将剧本表（每张的叙事角色 + 画面方向）简要告知用户，**确认后再继续生成**。

---

## 步骤 4：构建 Prompt

每张图（单图或 Carousel 每张）按六要素公式组装英文 Prompt：

```
[① 主体 Subject] + [② 场景 Setting] + [③ 风格 Style] + [④ 光线 Lighting] + [⑤ 构图 Composition] + [⑥ 氛围+技术 Mood & Technical]
```

---

### ① 主体 Subject

Carousel：`character_anchor`（原样粘贴）+ 本张的具体动作/表情

单图：具体描述主体是谁/什么 + 动作 + 外观细节

- ❌ 弱：a person in a kitchen
- ✅ 强：a fast food cook in a black apron, seen from behind, rapidly assembling takeout orders

---

### ② 场景 Setting

**不预设具体场景，用视觉属性基类 + 行业推导。**

从五个维度选定视觉属性：

| 维度 | 选项 |
|------|------|
| 明暗 | bright / dim / dark |
| 整洁度 | clean & organized / lived-in / raw & cluttered |
| 色彩饱和 | vibrant / neutral / muted / monochrome |
| 空间感 | spacious & open / intimate / tight & compressed |
| 质感 | glossy & modern / matte & natural / textured & industrial |

视觉属性确定后，从行业推导具体场景（餐饮→kitchen counter / pickup window，美容→salon chair / treatment room，健身→gym floor / studio mirror）。

组装格式：
```
Set inside a [明暗] [整洁度] [行业场景] with [质感] surfaces.
[空间感] framing. [色彩饱和] color environment.
[额外环境细节：道具、背景物品等]
```

---

### ③ 风格 Style

从品牌规范读取，默认幽默搞笑写实：

| 帖子类型 | 推荐风格 |
|---------|---------|
| 产品展示 | clean product photography / commercial editorial |
| 知识分享 | clean flat lighting, infographic aesthetic |
| 客户案例 | lifestyle photography, authentic feel |
| 互动投票 | bold graphic style, high contrast |
| 幕后故事 | candid documentary photography |
| 行业梗 | vibrant pop style, exaggerated, playful |
| 公告里程碑 | minimal tech aesthetic, premium |
| 教程轮播 | clean consistent series style |

---

### ④ 光线 Lighting

跟随场景明暗属性，不独立决策：

| 场景明暗 | 光线描述 |
|---------|---------|
| bright | Bright even overhead lighting with soft natural fill. High-key, no harsh shadows. |
| dim | Warm ambient lighting with localized light sources. Soft shadows, intimate feel. |
| dark | Dramatic directional lighting with strong contrast. Moody atmosphere. |

品牌调性为"明亮/活力/友好" → 不用 moody, dramatic shadows, desaturated  
品牌调性为"高端/奢华" → 不用 flat lighting, overexposed, neon

---

### ⑤ 构图 Composition

**永远标注文字留白位置**：`leave clean space in [位置] for text overlay`

按帖子类型选构图模板：

| 帖子类型 | 文字留白位置 | 镜头建议 |
|---------|------------|---------|
| 痛点共鸣 | upper 35% | 低角度, 35mm, 浅景深 |
| 产品展示 | left side 或 upper 30% | 中景, 50mm |
| 知识分享 | upper 40% | 正面, 平视 |
| 客户案例 | 人物对侧 30-40% | 50mm, 自然 |
| 互动投票 | 中间分隔带 | 对称, 平视 |
| 行业梗 | top 或 bottom 25% | close-up, 正面 |
| 公告里程碑 | 中央大面积 | 居中 |

---

### ⑥ 氛围 + 技术 Mood & Technical

**品牌色 60/30/10 注入：**
- 主色 → `color palette predominantly [主色] tones`
- 辅色 → `with [辅色] accents in the environment`
- 强调色 → `one pop of [强调色] from [具体物品]`

**氛围词禁区：**

| 品牌调性 | 适用氛围词 | 禁用氛围词 |
|---------|----------|----------|
| 活力/友好 | busy, energetic, real, bright, clean, lively | moody, dark, gritty, tense |
| 专业/权威 | confident, polished, structured, premium | chaotic, playful, messy |
| 温暖/亲和 | warm, inviting, authentic, cozy, gentle | cold, clinical, stark |
| 高端/奢华 | refined, dramatic, elegant, exclusive | cheap, cluttered, loud |
| 幽默/有趣 | playful, exaggerated, vibrant, surprising | serious, somber, formal |

**固定结尾（每张都加）：**
```
No text, no watermarks, no logos.
High quality, professional photography.
```

---

## 步骤 5：调用 Gemini 生成图片

### 单图

直接调用，传入步骤 4 组装的完整 prompt。

### Carousel（链式生成）

**基准图（第 1 张）：**

正常走六要素，额外加一致性锚定语句：

```
This is slide 1 of [总数] in a visual story sequence.
Establish the character appearance and environment clearly
for visual consistency across the series.
```

**链式图（第 2 张起）：**

```
image_generate(
  prompt="[完整 prompt]",
  reference_image=image_1,   ← 始终传第 1 张，不是上一张
  aspect_ratio="1:1"
)
```

prompt 内容：
- ① Subject：`character_anchor` 原样重复 + 本张新动作/表情
- ② Setting：同一场景 + 本张的变化细节（新道具/物品位置变化）
- ③④ Style / Lighting：与第 1 张完全相同
- ⑤ Composition：本张的构图调整 + 文字留白
- ⑥ Mood & Technical：品牌色相同 + 本张情绪关键词变化

结尾加：
```
Slide [N] of [总数]. Same character and environment as the reference image.
[本张叙事指令：一句话描述情节递进]
```

**reference_image 始终传第 1 张（image_1），不是上一张。** 每张都参考上一张会导致风格逐渐漂移。

---

## 步骤 6：质量复查

每张生成后检查：

| 检查项 | 合格标准 |
|-------|---------|
| 无文字乱码 | 图片中没有任何文字或符号 |
| 主体正确 | 图片内容与剧本描述的动作/场景匹配 |
| 留白充足 | 文字叠加区域干净，背景不杂乱 |
| 风格一致 | Carousel 各张视觉调性统一 |
| 品牌色分布 | 60/30/10 比例大致正确，强调色只有一个 pop |

**不合格处理：**
- 有乱码文字 → 加强 `No text` 约束，重新生成
- 主体错误 → 补充更具体的主体描述，重新生成
- 风格不一致 → 在 prompt 中加入对第 1 张的明确风格描述
- 最多重试 3 次；超过则向用户说明，请求更具体的描述

---

## 步骤 7：生成文案

为图片配套 caption。

**通用原则：**
- Caption 补充图片**没有呈现**的信息（背景故事、使用体验、为什么选择）
- 不重复图片中已有的视觉信息
- 结尾引导行动：私信 / 扫码 / 电话咨询 / 点击链接

**单图文案原则：**
- 避免"滤镜感"太强，加入真实问题或场景引发共鸣
- Caption 重点讲商家想传达的价值，图只是呈现氛围

**Carousel 文案原则：**
- 呼应整体叙事弧线方向（弧线 A → 痛点共鸣收尾；弧线 B → 价值总结；弧线 C → 结论推荐）
- Hook 对应第 1 张封面的情绪

**Hook 参考（选一种）：**
- 数字冲击：`[面积/价格等数字] + 出乎意料的卖点`
- 场景代入：`如果你也在找……`
- 直接价值：`[地点] + [核心卖点] + 现在开放`

**Hashtag**：5–12 个，大众标签 + 垂直标签 + 地理/品类标签

---

## 输出

向用户展示：
1. 生成的图片路径列表（Carousel 按张标注叙事角色）
2. Caption + Hashtags
3. 询问：
   - 满意 → 直接发布
   - 要修改图片 → 告知哪里不满意（颜色/主体/风格），重新生成对应张
   - 要做成海报 → 切换到 F1，用生成的图片作为背景（F1 用沙盒 Python Pillow 处理文字叠加和品牌包装）
