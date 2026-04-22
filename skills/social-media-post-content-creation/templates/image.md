# 图片 Prompt 模板

所有 prompt 用英文输出。本模板负责 **AI 生成底图**，底图应为干净的视觉素材，留出文字叠加空间。文字排版、Logo 叠加等成品化操作不在本模板范围内，由 SKILL.md 第六步（品牌包装）处理。

---

## 第一步：读取品牌视觉规范

生成 prompt 前，先从 `/workspace/marketing-context.md` 提取以下信息：

- `## 品牌语气` → 决定视觉调性（幽默？专业？温情？）
- `## 内容设置 → 图片风格` → 锁定默认风格关键词
- `## 品牌色` → 提取主色、辅色、强调色色值
- `## 行业` → 推导具体场景（餐饮→厨房/柜台，美容→店面/工作台，科技→办公室/屏幕）

如果 marketing-context.md 未指定图片风格，使用默认风格（见下方）。

### 默认风格：幽默搞笑

```
vibrant colors, playful composition, exaggerated expressions or props,
warm energetic lighting, fun and lighthearted mood,
high quality, professional photography
```

---

## 第二步：六要素 Prompt 公式

每一张图的 prompt 都按这六个要素写：

```
[① 主体 Subject] + [② 场景 Setting] + [③ 风格 Style] + [④ 光线 Lighting] + [⑤ 构图 Composition] + [⑥ 氛围+技术 Mood & Technical]
```

### ① 主体 Subject — "画面里有什么人/物在做什么"

要求：具体、有动作、有细节

- ❌ 弱：a person in a kitchen
- ✅ 强：a fast food cook in a black apron, seen from behind, rapidly assembling takeout orders

**构建方法：**
1. 从帖子内容方向确定主体是谁/什么（人物？产品？场景？）
2. 加上具体动作（不是站着，是在做某件事）
3. 加上外观细节（穿什么、什么颜色、什么材质）

---

### ② 场景 Setting — "在什么环境里"

**不预设具体场景，用视觉属性基类 + 行业推导。**

#### 视觉属性基类

从以下五个维度选定底层视觉属性，组合出场景的"气质"：

| 维度 | 选项 | 说明 |
|------|------|------|
| **明暗** | bright / dim / dark | 整体亮度。大多数商业内容选 bright |
| **整洁度** | clean & organized / lived-in / raw & cluttered | 空间的秩序感 |
| **色彩饱和** | vibrant / neutral / muted / monochrome | 环境颜色的鲜艳程度 |
| **空间感** | spacious & open / intimate / tight & compressed | 画面呼吸感 |
| **质感** | glossy & modern / matte & natural / textured & industrial | 表面材质感 |

**示例组合：**
- 快餐厨房 → bright + clean & organized + neutral + spacious + glossy & modern
- 精品咖啡 → dim + lived-in + muted + intimate + matte & natural
- 科技公司 → bright + clean & organized + monochrome + spacious + glossy & modern

#### 行业场景推导

视觉属性确定后，根据 marketing-context.md 中的行业信息推导具体场景：

```
行业（marketing-context.md）→ 场景关键词
```

AI 应自行根据行业推导合理场景，不依赖预设列表。例如：
- 餐饮 → kitchen counter / pickup window / dining area / storefront
- 美容 → salon chair / vanity table / treatment room
- 健身 → gym floor / weight rack / studio mirror
- 电商 → product table / shipping station / unboxing setup

#### 场景描述组装

将视觉属性 + 行业场景合并为一段完整描述：

```
Set inside a [明暗] [整洁度] [行业场景] with [质感] surfaces.
[空间感] framing. [色彩饱和] color environment.
[额外环境细节：道具、背景物品、窗户等]
```

**完整示例：**
```
Set inside a bright, clean and organized American fast food kitchen
with glossy stainless steel surfaces. Spacious framing with overhead LED panel lighting.
Neutral color environment. Order tickets hanging on a rail, white to-go containers stacked neatly,
a pickup window in the background showing the front counter area.
```

---

### ③ 风格 Style — "这张图看起来像什么类型的作品"

从 marketing-context.md 的图片风格设定中读取。如未设定，根据帖子类型推荐：

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

**风格关键词库：**

| 风格 | 英文关键词 |
|------|-----------|
| 幽默/搞笑 | vibrant colors, playful composition, exaggerated expression, fun props, warm energetic lighting, lighthearted mood |
| 商业/专业 | corporate clean, minimalist, studio lighting, polished |
| 生活方式 | lifestyle photography, candid moment, natural daylight, warm tones |
| 奢华/高端 | luxury aesthetic, dramatic shadows, dark moody, fine dining |
| 温情/真实 | authentic documentary, natural light, candid, soft pastel tones |
| 活力/年轻 | vibrant colors, dynamic composition, energetic, bright and bold |
| 科技/未来 | tech aesthetic, clean lines, cool tones, digital elements |

---

### ④ 光线 Lighting — "影响最大的单一要素"

光线跟随场景的明暗属性，不独立决策：

| 场景明暗 | 推荐光线描述 |
|---------|------------|
| bright | Bright even overhead lighting with soft natural fill. High-key, no harsh shadows. |
| dim | Warm ambient lighting with localized light sources. Soft shadows, intimate feel. |
| dark | Dramatic directional lighting with strong contrast. Moody atmosphere. |

**额外光源叠加（根据环境）：**
- 有窗户 → 加 `natural daylight spills through the window`
- 有屏幕 → 加 `cool screen glow on face/surface`
- 食物特写 → 加 `warm directional light to enhance texture and steam`
- 产品展示 → 加 `subtle rim light separating subject from background`

**光线禁区（除非品牌明确要求）：**
- 品牌调性为"明亮/活力/友好" → 不用 moody, dramatic shadows, desaturated, muted tones
- 品牌调性为"高端/奢华" → 不用 flat lighting, overexposed, neon

---

### ⑤ 构图 Composition — "镜头怎么摆，画面怎么分"

#### 构图通用原则
- **永远留文字空间** — 标注 `leave clean space in [位置] for text overlay`
- **主体不居中** — 优先三分法则，除非是大字报/公告类帖子
- **前景制造层次** — 前景放一个道具增加深度感

#### 按帖子类型选构图模板

| 帖子类型 | 构图模板 | 文字留白位置 | 镜头建议 |
|---------|---------|------------|---------|
| 痛点共鸣 | 前景道具（锐利）+ 中景人物（主体）+ 背景环境（虚化） | upper 35% | 低角度, 35mm, 浅景深 |
| 产品展示 | 产品居中或偏右，环境提供上下文 | left side 或 upper 30% | 中景, 50mm |
| 知识分享 | 干净背景 + 主体居中，信息图风格 | upper 40% | 正面, 平视 |
| 客户案例 | 人物偏左或偏右，另一侧留白给证言文字 | 人物对侧 30-40% | 50mm, 自然 |
| 互动投票 | 分屏对比，画面对角线或垂直一分为二 | 中间分隔带区域 | 对称, 平视 |
| 行业梗 | 主体居中，夸张表情或动作，简洁背景 | top 或 bottom 25% | close-up, 正面 |
| 公告里程碑 | 居中对称，主体作为焦点，放射状或干净背景 | 中央大面积 | 居中 |
| 教程轮播 | 一致的布局框架，每张换内容不换结构 | 固定位置 header | 统一机位 |

---

### ⑥ 氛围 + 技术 Mood & Technical

#### 品牌色注入规则

从 marketing-context.md 读取品牌色板，按以下规则注入 prompt：

- **主色** → 用于大面积背景或环境色调描述（"color palette predominantly [主色] tones"）
- **辅色** → 用于次要元素（"with [辅色] accents in the environment"）
- **强调色** → 只用于一个视觉焦点（"one pop of [强调色] from [具体物品]"）
- 遵循 **60/30/10 法则** — 不要让三种颜色平均分布

#### 氛围关键词

根据品牌调性选择：

| 品牌调性 | 适用氛围词 | 禁用氛围词 |
|---------|----------|----------|
| 活力/友好 | busy, energetic, real, bright, clean, lively | moody, dark, gritty, tense |
| 专业/权威 | confident, polished, structured, premium | chaotic, playful, messy |
| 温暖/亲和 | warm, inviting, authentic, cozy, gentle | cold, clinical, stark |
| 高端/奢华 | refined, dramatic, elegant, exclusive | cheap, cluttered, loud |
| 幽默/有趣 | playful, exaggerated, vibrant, surprising | serious, somber, formal |

#### 技术参数

所有 prompt 结尾固定加：

```
high quality, professional photography
```

比例按平台和内容类型选择（见下方格式模板）。

---

## 第三步：按内容格式输出

### Single Feed（单图）

**aspect_ratio：** Instagram / Facebook Feed → `"4:5"`；LinkedIn / Facebook Wide → `"16:9"`

```
image_generate(
  prompt="[六要素组装的完整 prompt]",
  aspect_ratio="4:5"
)
```

---

### Carousel（多图系列 — 链式生成）

**aspect_ratio：** 全系列统一 `"1:1"`

Carousel 使用 **叙事弧线 + reference image 链式生成**，让多张图形成连贯故事，同时通过参考图锚定视觉一致性。

---

#### 一、选择叙事弧线

根据内容方向选择弧线结构，每张图承担不同的叙事角色：

##### 弧线 A — 问题→解决（最常用）

| 张数 | 叙事角色 | 情绪 | 画面方向 |
|------|---------|------|---------|
| 1（封面） | Hook — 抛出问题 | 紧张/共鸣 | [人物] + [行业痛点信号]，表情夸张 |
| 2 | Escalate — 问题放大 | 加剧 | 特写痛点细节（手忙脚乱/堆积/混乱） |
| 3 | Peak — 崩溃顶点 | 最高 | 最戏剧化的瞬间 |
| 4 | Turn — 转折出现 | 意外 | [品牌元素/产品/工具] 入场 |
| 5 | Relief — 问题解决 | 轻松 | 同一场景恢复秩序，人物放松 |
| 6（CTA） | 收尾 — 行动指引 | 信任 | 产品/Logo + 干净背景 |

##### 弧线 B — 教程/步骤

| 张数 | 叙事角色 | 画面方向 |
|------|---------|---------|
| 1（封面） | 成品展示 — 先看结果 | 最终效果的漂亮展示 |
| 2-5 | Step 1-4 — 过程拆解 | 每步一个关键动作，同场景同人物 |
| 6（CTA） | 总结 + 行动指引 | 回到成品 + 品牌信息 |

##### 弧线 C — 对比/排名

| 张数 | 叙事角色 | 画面方向 |
|------|---------|---------|
| 1（封面） | 抛出问题 — "你知道吗？" | 引发好奇的画面 |
| 2-5 | 逐项展示 | 每项一个场景，同构图框架不同内容 |
| 6（CTA） | 结论 + 行动指引 | 胜出项 + 品牌收尾 |

**弧线张数可调整：** 以上按 6 张示例，实际 carousel 可以是 4-10 张。根据内容需要增减中间张数，但保持"封面→中间递进→CTA 收尾"的基本结构。

---

#### 二、锁定人物锚点描述（Character Anchor）

在写任何 prompt 之前，先写一段 **人物锚点描述**，全系列所有张都重复使用这段文字，确保人物外观一致：

```
character_anchor = "[性别] [年龄段] [行业角色], wearing [服装颜色+款式],
[发型], [体型], [其他显著外观特征]"
```

**构建规则：**
- 从行业推导人物角色（餐饮→厨师/服务员，美容→美容师/顾客，健身→教练/学员）
- 服装颜色尽量使用品牌色（如品牌主色是黑色 → black apron）
- 描述要足够具体，让不同帧的生成结果能对上同一个人
- **每张 prompt 的 Subject 开头都粘贴这段描述**，只改动作部分

---

#### 三、Prompt 写法

##### 基准图 Prompt（第 1 张）

正常走六要素公式，额外加一致性锚定指令：

```
[① Subject: character_anchor + 第 1 张的动作]
[② Setting: 场景描述（视觉属性基类 + 行业推导）]
[③ Style: 风格关键词]
[④ Lighting: 光线描述]
[⑤ Composition: 构图 + 文字留白]
[⑥ Mood & Technical: 品牌色 + 氛围]

This is slide 1 of [总数] in a visual story sequence.
Establish the character appearance and environment clearly
for visual consistency across the series.

1:1 square aspect ratio, high quality, professional photography
```

##### 链式图 Prompt（第 2 张起）

每张都传入第 1 张的输出作为 reference image，prompt 结构：

```
image_generate(
  prompt="[下方完整 prompt]",
  reference_image=image_1,
  aspect_ratio="1:1"
)
```

Prompt 内容：

```
[① Subject: character_anchor（原样重复）+ 本张的新动作/表情]
[② Setting: 同一场景 + 本张的变化细节（新道具出现/物品位置变化）]
[③ Style: 与第 1 张相同]
[④ Lighting: 与第 1 张相同]
[⑤ Composition: 本张的构图调整（镜头远近/角度可变）+ 文字留白]
[⑥ Mood & Technical: 品牌色相同 + 本张的情绪关键词变化]

Slide [N] of [总数]. Same character and environment as the reference image.
[本张叙事指令：一句话描述情节递进]

1:1 square aspect ratio, high quality, professional photography
```

**关键规则：reference_image 始终传入第 1 张（image_1），不是上一张。** 如果每张都参考上一张（1→2→3→4），风格会像传话游戏逐渐漂移。始终锚定第 1 张，保证所有图的视觉基准是同一个锚点。

---

#### 四、一致性控制

**必须跨张保持一致的：**
- 人物外观 — character_anchor 原样重复，不改动
- 场景环境 — 同一空间，不跳场
- 色调和光线 — style + lighting 描述一模一样
- 品牌色分布 — 60/30/10 比例不变
- 画面比例 — 全部 1:1

**允许跨张变化的：**
- 人物动作和表情 — 叙事推进的核心
- 镜头角度和距离 — 特写 ↔ 中景切换增加节奏感
- 前景道具 — 新元素入场 = 剧情转折
- 情绪氛围词 — 从 stressed → relieved 等情绪递进

---

#### 五、生成流程

```
Step 1 → 生成基准图（第 1 张），走完整六要素公式
Step 2 → 自检基准图：风格/色调/人物是否符合品牌规范
         不合格 → 调整 prompt 重新生成（最多 2 次）
Step 3 → 链式生成第 2 到最后一张：
         每张传入 image_1 作为 reference_image
         prompt 只变动作/表情/情绪/新道具
Step 4 → 全部生成完毕后，通览检查整体一致性
         如某张明显跑偏 → 单独重新生成该张（仍锚定 image_1）
```

---

#### 六、草稿记录

草稿中按张记录，标注叙事角色：

```markdown
## 配图路径
- 第 1 张（Hook）：[public_url]
- 第 2 张（Escalate）：[public_url]
- 第 3 张（Peak）：[public_url]
- 第 4 张（Turn）：[public_url]
- 第 5 张（Relief）：[public_url]
- 第 6 张（CTA）：[public_url]
```

---

### Story / Reels 封面

**aspect_ratio：** `"9:16"`

竖屏特殊要求 — 主体居中，上下留空：

```
[subject] [action], [scene/background],
vertical 9:16 portrait composition,
subject centered in middle 70% of frame,
[style], [lighting], [mood/color tone],
clean space at top and bottom for text overlay,
high quality, professional photography
```

---

## Prompt 组装检查清单

出图前对照检查：

- [ ] ① Subject 够具体吗？有动作、有细节？
- [ ] ② Setting 用了视觉属性基类 + 行业推导？不是凭空想的？
- [ ] ③ Style 跟帖子类型匹配吗？跟品牌调性一致吗？
- [ ] ④ Lighting 跟场景明暗属性一致？没踩禁区？
- [ ] ⑤ Composition 选了帖子类型对应的构图模板？标注了文字留白？
- [ ] ⑥ 品牌色注入了吗？强调色只有一个 pop？氛围词没踩禁区？
- [ ] 结尾加了 `high quality, professional photography`？
- [ ] aspect_ratio 跟目标平台匹配？

**Carousel 额外检查：**
- [ ] 选了叙事弧线？每张的叙事角色明确？
- [ ] character_anchor 写了？每张 prompt 都原样重复了？
- [ ] 第 2 张起都传入 image_1 作为 reference_image？（不是上一张）
- [ ] style / lighting / 品牌色描述全系列一致？只变动作和情绪？

---

## 完整示例

### 示例：痛点共鸣帖（餐饮行业，品牌调性科技/活力）

**分析过程：**
```
帖子类型：痛点共鸣 → 构图模板：前景+中景+背景，upper 35% 留白
行业：餐饮快餐 → 场景：fast food kitchen
视觉属性：bright + clean & organized + neutral + spacious + glossy & modern
品牌色：主色 #1A1A1A / 辅色 #FFFFFF / 强调色 #33CCFF
品牌调性：科技/活力 → 氛围词：busy, energetic, real / 禁区：moody, dark
```

**输出 prompt：**
```
A fast food restaurant cook in a black apron, seen from behind,
rapidly assembling takeout orders at a bright stainless steel counter.
A corded commercial telephone mounted on the wall nearby is ringing,
with a small cyan blue indicator light blinking.
Order tickets hanging on a rail above, white to-go containers stacked neatly.

Set inside a bright, clean and organized American fast food kitchen
with glossy stainless steel surfaces. Spacious framing.
Natural daylight spills through the pickup window.

Commercial editorial photography style, crisp and modern.

Bright even overhead LED lighting with soft natural fill from the window.
No harsh shadows. High-key.

Shot from a slightly low angle across the counter.
The ringing wall phone visible in the left foreground,
the cook in the center-right. Shallow depth of field, 35mm lens.

Busy, energetic, and real mood. Color palette predominantly white, silver,
and warm neutrals with one pop of cyan blue (#33CCFF) from the phone light.
The upper 35% of the image is relatively clean for text overlay.

4:5 portrait aspect ratio, high quality, professional photography.
```