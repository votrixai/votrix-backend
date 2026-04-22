# 视频 Prompt 模板

视频 prompt 是给 AI 导演看的分镜单，不是文案。用英文输出。

## 默认风格：幽默搞笑

**视频默认使用喜剧/轻松风格（Comedy style）。** 除非 `marketing-context.md` 另有指定，否则维度一风格固定用 `Comedy style, 8 seconds.`，并遵循以下原则：

- 快切节奏、夸张表情、能量感强
- 优先选「问题解决」或「顾客时刻」主题，制造反转感
- 音频优先用「对话驱动」或「配乐+单句台词」混合，配搭 quirky/upbeat 音乐
- 避免史诗感大音乐、慢镜、暗调电影风

---

## 组合公式

```
风格(Tone) × 主题(Theme) × 主体(Subject) × 视角(POV) × 音频(Audio)
```

按以下五个维度各选一项，拼成最终 prompt。

---

## 维度一：风格（Tone）

开头第一行写风格定基调。

| 风格 | 开头写法 | 视觉感 | 节奏 |
|------|---------|--------|------|
| **喜剧/轻松（默认）** | `Comedy style, 8 seconds.` | 夸张表情，快切，能量感强 | 快，跳跳 |
| 电影感/戏剧 | `Cinematic style, 8 seconds.` | 慢镜，强光影，史诗构图 | 慢，有分量 |
| 温情/真实 | `Warm documentary style, 8 seconds.` | 自然光，手持感，真实表情 | 平缓，呼吸感 |
| 专业/简洁 | `Clean commercial style, 8 seconds.` | 干净背景，产品居中，字幕标注 | 稳，清晰 |
| 励志/能量 | `Inspirational style, 8 seconds.` | 动感剪辑，正面情绪，大动作 | 节奏驱动 |

---

## 维度二：主题（Theme）

主题决定场景弧线——画面里发生什么、顺序怎么排。

### 产品英雄（Product Hero）
```
[Product] [detail: texture / steam / shine] on [surface/setting].
Camera slowly pushes in, revealing [key feature].
[Someone] picks it up / tastes it / uses it.
Satisfied reaction. Cut to product with logo.
```

### 问题解决（Problem → Solution）
```
[Setting]: [person] looks stressed / overwhelmed.
[Pain cue: phones ringing / long queue / piles of work].
Then — [brand element appears: product / screen / tool].
Problem resolves. Person visibly relieved, smiling.
```

### 幕后故事（Behind the Scenes）
```
[Location: kitchen / workshop / storefront], [time: early morning / before opening].
[Staff member] [doing craft: chopping / arranging / preparing].
Close-up hands at work. [Sensory detail: steam / sound / texture].
Cut to: finished product presented with care.
```

### 顾客时刻（Customer Moment）
```
[Customer] walks in / arrives / discovers [brand].
[Moment of experience: first bite / first look / reaction].
Genuine emotion — surprise, delight, or relief.
[Optional: customer says one line to camera].
```

### 促销/限时（Promo / Offer）
```
Bold text overlay flashes: "[Offer / Number]".
Quick cuts: [product 1], [product 2], [happy customer].
[Person] holds up product, enthusiastic gesture.
Final frame: logo + "[CTA]". Strong, punchy ending.
```

### 品牌价值（Brand Story）
```
[Atmospheric scene: empty restaurant at dawn / founder at work].
[Moment that shows brand value: attention to detail / care / craft].
[Optional text overlay: brand tagline or single value statement].
Fade to logo. Emotional, quiet ending.
```

---

## 维度三：主体焦点（Subject）

决定镜头跟谁：

| 主体 | 描述写法 |
|------|---------|
| 产品主角 | `Camera focuses entirely on the product. Close-ups, texture details, no face shown.` |
| 人物主角 | `A [person: chef / owner / customer] is the central subject. Face and reactions visible.` |
| 空间/氛围 | `No single subject. Camera moves through the space — [restaurant / kitchen / storefront].` |

---

## 维度四：视角（POV）

| 视角 | 描述写法 |
|------|---------|
| 旁观者（默认） | 不需要特别注明，正常第三视角 |
| 顾客 POV | `Shot from customer's point of view — we see what they see as they [enter / order / eat].` |
| 俯拍/平铺 | `Overhead flat-lay shot. Camera looks straight down at [subject on surface].` |
| 手持跟拍 | `Handheld camera follows [subject] through [space]. Slight natural shake, documentary feel.` |

---

## 维度五：音频策略（Audio）

Veo 3 原生生成音频，必须明确指定：

| 策略 | 描述写法 |
|------|---------|
| 对话驱动 | `A [voice / person] says: "[台词]". Clear dialogue.` |
| 配乐驱动 | `[Music style] background music — [upbeat jazz / soft acoustic / epic orchestral / punchy electronic].` |
| 音效驱动 | `Sound of [sizzling / pouring / crowd murmur / phone ringing]. No music, ambient sounds only.` |
| 混合 | 配乐 + 单句台词，最常用 |

---

## 完整 Prompt 组装示例

### 示例 A：喜剧 × 问题解决 × 人物 × 旁观者 × 对话+音效

```
Comedy style, 8 seconds.

Frantic restaurant — phones ringing everywhere, staff visibly overwhelmed.
One staff member looks directly at camera: exhausted shrug.
Suddenly — a glowing phone screen appears, picks up automatically.
AI voice says: "Thank you for calling, I've got this."
Staff freeze. Slow turn. Jaws drop in unison.

Quirky upbeat music. Fast cuts. Exaggerated expressions.
Sound of phones ringing, then sudden silence.
```

### 示例 B：电影感 × 幕后故事 × 产品+人物 × 旁观者 × 配乐

```
Cinematic style, 8 seconds.

Early morning kitchen. Chef alone, preparing mise en place.
Close-up hands slicing with precision. Steam rises from a pan.
Camera slowly pulls back — full kitchen revealed, warm amber light.
Chef places the finished dish, steps back, nods.

Soft orchestral music, building gently. No dialogue. Ambient kitchen sounds underneath.
Rich warm tones, shallow depth of field.
```

### 示例 C：温情 × 顾客时刻 × 人物 × POV × 音效

```
Warm documentary style, 8 seconds.

Shot from customer POV — we walk through the restaurant entrance.
Host smiles and gestures to a table. Warm golden light inside.
We sit. A bowl of ramen is placed in front of us, steam rising.
First spoonful. Cut to: face — eyes close, genuine smile.

Soft acoustic guitar. Sound of gentle restaurant ambience.
Natural daylight, handheld feel, muted warm tones.
```

---

## 平台格式对照

| 平台 | aspect_ratio | duration_seconds | 备注 |
|------|-------------|-----------------|------|
| Instagram Reels | `"9:16"` | `8` | 主力视频格式 |
| Facebook Reels | `"9:16"` | `8` | 与 IG 同素材 |
| Instagram Story 视频 | `"9:16"` | `8` | |
| LinkedIn Video | `"16:9"` | `8` | 横屏，专业感 |
| Twitter | — | — | 不支持，改发配图 |
