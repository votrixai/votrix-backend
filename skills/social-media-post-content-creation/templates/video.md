# 视频 Prompt 模板

视频 prompt 是给 AI 导演看的分镜单，不是文案。用英文输出。

本模板覆盖两种场景：
- **AI 生成视频** — 调用 `video_generate`，五维度公式构建 prompt
- **用户自带视频** — 不做剪辑，只生成配套文案 + 封面图

视频剪辑（裁剪、拼接、加字幕时间线）不在本模板范围内。

---

## 第一步：读取品牌视觉规范

生成 prompt 前，先从 `/workspace/marketing-context.md` 提取：

- `## 品牌语气` → 决定视频调性（默认幽默搞笑，除非另有指定）
- `## 内容设置 → 图片风格` → 视觉风格关键词同样适用于视频
- `## 品牌色` → 提取主色、辅色、强调色，注入环境色调和道具颜色
- `## 行业` → 推导具体场景（餐饮→厨房/柜台，美容→店面，科技→办公室）

---

## 第二步：判断素材来源

### 路径 A — AI 生成视频

用户没有视频素材，需要 AI 从零生成。进入第三步（五维度公式）。

### 路径 B — 用户自带视频

用户提供了视频文件或 URL。

**处理流程：**
1. 收下视频 URL，写入草稿 `## 视频路径`
2. **分析视频内容** — 描述视频里拍的是什么、时长、情绪、关键画面
3. 根据视频内容 **反推文案方向** — 调用 `skill/social-media-post-content-creation/templates/copywriting.md` 生成配套 caption + hashtag
4. **生成封面图（可选）** — 调用 image 模板的六要素公式，生成一张 9:16 封面图：

```
image_generate(
  prompt="[基于视频内容构思的封面画面]",
  aspect_ratio="9:16"
)
```

5. 封面图走 SKILL.md 第六步品牌包装（加标题文字、Logo）
6. 写入草稿，流程结束

**路径 B 不涉及五维度公式，以下内容仅适用于路径 A。**

---

## 第三步：五维度 Prompt 公式（路径 A 专用）

```
维度一 风格(Tone) × 维度二 主题(Theme) × 维度三 主体(Subject) × 维度四 视角(POV) × 维度五 音频(Audio)
```

加上从第一步读取的品牌规范，共六层控制：

```
品牌规范（底层约束）
 └→ 风格 × 主题 × 主体 × 视角 × 音频
      └→ 最终 prompt
```

---

### 维度一：风格（Tone）

开头第一行写风格定基调。**默认使用喜剧/轻松风格，除非品牌语气另有指定。**

| 风格 | 开头写法 | 视觉感 | 节奏 | 适用品牌调性 |
|------|---------|--------|------|------------|
| **喜剧/轻松（默认）** | `Comedy style, 8 seconds.` | 夸张表情，快切，能量感强 | 快 | 活力/友好/幽默 |
| 电影感/戏剧 | `Cinematic style, 8 seconds.` | 慢镜，强光影，史诗构图 | 慢 | 高端/奢华 |
| 温情/真实 | `Warm documentary style, 8 seconds.` | 自然光，手持感，真实表情 | 平缓 | 温暖/亲和 |
| 专业/简洁 | `Clean commercial style, 8 seconds.` | 干净背景，产品居中，字幕标注 | 稳 | 专业/权威 |
| 励志/能量 | `Inspirational style, 8 seconds.` | 动感剪辑，正面情绪，大动作 | 快 | 活力/年轻 |

**风格禁区：**
- 品牌调性为"活力/友好" → 不用 Cinematic（太沉重）
- 品牌调性为"高端/奢华" → 不用 Comedy（太随意）
- 品牌调性为"专业/权威" → 不用 Comedy 或 Inspirational（太夸张）

---

### 维度二：主题（Theme）

主题决定场景弧线——画面里发生什么、顺序怎么排。

**弧线结构保留，具体场景由 AI 根据行业推导填充。** 以下模板中的 `[行业场景]`、`[行业痛点]`、`[品牌元素]` 等槽位需要从 marketing-context.md 推导。

#### 产品英雄（Product Hero）
```
[产品/服务] [细节特写: 质感 / 光泽 / 动态效果] on [行业推导的展示场景].
Camera slowly pushes in, revealing [核心功能/卖点].
[人物] picks it up / uses it / interacts with it.
Satisfied reaction. Cut to product with logo.
```

#### 问题解决（Problem → Solution）
```
[行业推导的场景]: [人物] looks stressed / overwhelmed.
[行业推导的痛点信号: 具体的问题表现].
Then — [品牌元素出现: 产品 / 界面 / 工具].
Problem resolves. [人物] visibly relieved, smiling.
```

#### 幕后故事（Behind the Scenes）
```
[行业推导的工作场所], [time: early morning / before opening / after hours].
[工作人员] [行业相关的手艺/操作动作].
Close-up hands at work. [感官细节: 声音 / 蒸汽 / 质感].
Cut to: finished result presented with care.
```

#### 顾客时刻（Customer Moment）
```
[顾客] walks in / arrives / discovers [品牌/产品].
[体验瞬间: 第一次使用 / 第一次看到效果 / 收到结果].
Genuine emotion — surprise, delight, or relief.
[Optional: 顾客对镜头说一句话].
```

#### 促销/限时（Promo / Offer）
```
Bold text overlay flashes: "[优惠内容 / 数字]".
Quick cuts: [产品1], [产品2], [开心的顾客].
[人物] holds up product, enthusiastic gesture.
Final frame: logo + "[CTA]". Strong, punchy ending.
```

#### 品牌价值（Brand Story）
```
[氛围场景: 行业推导的安静/有仪式感的时刻].
[展现品牌价值的瞬间: 细节 / 用心 / 匠心].
[Optional text overlay: 品牌 tagline 或核心价值主张].
Fade to logo. Emotional, quiet ending.
```

---

### 维度三：主体焦点（Subject）

决定镜头跟谁：

| 主体 | 描述写法 |
|------|---------|
| 产品主角 | `Camera focuses entirely on the product. Close-ups, texture details, no face shown.` |
| 人物主角 | `A [行业推导的人物角色] is the central subject. Face and reactions visible.` |
| 空间/氛围 | `No single subject. Camera moves through the space — [行业推导的环境].` |

---

### 维度四：视角（POV）

| 视角 | 描述写法 |
|------|---------|
| 旁观者（默认） | 不需要特别注明，正常第三视角 |
| 顾客 POV | `Shot from customer's point of view — we see what they see as they [行业相关的体验动作].` |
| 俯拍/平铺 | `Overhead flat-lay shot. Camera looks straight down at [subject on surface].` |
| 手持跟拍 | `Handheld camera follows [subject] through [space]. Slight natural shake, documentary feel.` |

---

### 维度五：音频策略（Audio）

视频生成工具（如 Veo 3）原生生成音频，必须明确指定：

| 策略 | 描述写法 | 适用场景 |
|------|---------|---------|
| 对话驱动 | `A [voice / person] says: "[台词]". Clear dialogue.` | 问题解决、顾客时刻 |
| 配乐驱动 | `[Music style] background music — [具体风格].` | 品牌故事、幕后 |
| 音效驱动 | `Sound of [行业相关音效]. No music, ambient sounds only.` | 幕后故事、产品特写 |
| 混合（默认推荐） | 配乐 + 单句台词 | 大多数场景 |

**配乐风格参考：**

| 品牌调性 | 推荐配乐风格 |
|---------|------------|
| 活力/友好/幽默 | quirky upbeat, funky, playful electronic |
| 专业/权威 | clean corporate, minimal piano, subtle electronic |
| 温暖/亲和 | soft acoustic guitar, warm piano, gentle strings |
| 高端/奢华 | elegant orchestral, sophisticated jazz, ambient |
| 年轻/大胆 | punchy electronic, hip-hop beat, energetic pop |

---

## 第四步：光线与色调

视频的光线跟随 image.md 相同的视觉属性基类逻辑：

| 场景明暗 | 推荐光线描述 |
|---------|------------|
| bright（默认） | Bright even lighting. Clean, energetic atmosphere. Well-lit environment. |
| dim | Warm ambient lighting. Soft shadows, intimate feel. Localized light sources. |
| dark | Dramatic directional lighting. Strong contrast. Moody atmosphere. |

**品牌色注入（视频版）：**

不像图片那样精确控制颜色，视频中品牌色通过以下方式体现：
- **环境色调** — `Overall color grading leans toward [品牌色调描述: warm neutrals / cool blues / etc.]`
- **道具颜色** — `Key props feature [品牌强调色] — [具体物品]`
- **结尾帧** — `Final frame: [品牌主色] background with logo in [品牌辅色]`

---

## 第五步：Prompt 组装

将五个维度 + 光线色调组装为完整 prompt：

```
[维度一：风格开头]

[维度二：主题弧线，填入行业推导的具体内容]
[维度三：主体焦点描述]
[维度四：视角描述（如非默认）]

[光线描述]
[品牌色调注入]
[维度五：音频策略]
```

调用：

```
video_generate(
  prompt="[组装好的完整 prompt]",
  aspect_ratio="9:16",    # IG/FB Reels/Story
  duration=8              # 默认 8 秒
)
```

---

## 平台格式对照

| 平台 | aspect_ratio | duration | 备注 |
|------|-------------|----------|------|
| Instagram Reels | `"9:16"` | `8` | 主力视频格式 |
| Facebook Reels | `"9:16"` | `8` | 与 IG 同素材 |
| Instagram Story | `"9:16"` | `8` | |
| LinkedIn Video | `"16:9"` | `8` | 横屏，专业感 |
| Twitter | — | — | 不支持视频生成，改发配图 |

---

## 出片前检查清单

- [ ] 第一步读了品牌规范？风格选择跟品牌调性一致？
- [ ] 主题弧线里的场景是根据行业推导的，不是硬编码的？
- [ ] 音频策略明确指定了？（不能留空让 AI 随机）
- [ ] 品牌色有体现？（环境色调 / 道具 / 结尾帧）
- [ ] 光线描述跟场景明暗一致？没踩品牌禁区？
- [ ] aspect_ratio 跟目标平台匹配？
- [ ] 如果是用户自带视频 → 只做文案 + 封面图，没有去动视频本身？

---

## 完整示例

### 示例 A：AI 生成 — 喜剧 × 问题解决 × 人物 × 旁观者 × 混合音频

**分析过程：**
```
品牌：CaterAI（餐饮AI）
品牌调性：科技/活力 → 默认 Comedy style
行业：快餐 → 场景：fast food kitchen / counter
品牌色：主色 #1A1A1A / 强调色 #33CCFF
痛点：电话响了没人接
```

**输出 prompt：**
```
Comedy style, 8 seconds.

Frantic fast food kitchen — a corded phone on the wall ringing non-stop,
two cooks juggling orders, one tries to reach for the phone but nearly drops a tray.
Exhausted look directly at camera: helpless shrug.
Suddenly — the phone picks up by itself, a calm AI voice says:
"Thank you for calling, how can I help you?"
Staff freeze. Slow turn. Jaws drop in unison. Relieved laughter.

Bright even overhead kitchen lighting. Clean, energetic atmosphere.
Overall color grading: clean warm neutrals with a pop of cyan blue (#33CCFF)
from the phone's indicator light.

Quirky upbeat electronic music. Sound of phones ringing, then sudden silence.
AI voice line clear over the music.
```

### 示例 B：用户自带视频 — 只做文案 + 封面图

**用户输入：** "我拍了一段厨房忙碌的视频，帮我发 Reels"

**处理：**
1. 收下视频 URL → 写入草稿 `## 视频路径`
2. 分析视频：快餐厨房高峰期，多人同时出餐，节奏很快
3. 反推文案方向 → 适合"幕后故事"类型
4. 生成 caption：

```
The chaos you don't see behind the counter. 🔥

Every order, every call, every "can I get extra sauce" —
handled by a team that never stops moving.

But what if the phone calls handled themselves?
That's where CaterAI comes in. 📞🤖

#BehindTheScenes #RestaurantLife #CaterAI #KitchenChaos #TakeoutLife
```

5. 生成封面图 prompt（调用 image 模板）：

```
image_generate(
  prompt="A dynamic action shot of fast food kitchen staff assembling orders,
  motion blur on hands, bright overhead lighting, stainless steel counter,
  energetic and real mood, vertical 9:16 composition,
  subject centered in middle 70%, clean space at top and bottom for text overlay,
  warm neutrals with one pop of cyan blue, commercial editorial photography,
  high quality, professional photography",
  aspect_ratio="9:16"
)
```

6. 封面图进 SKILL.md 第六步 → Canva 加标题 "The chaos behind the counter 🔥" + Logo