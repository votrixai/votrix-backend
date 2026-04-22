# 图片 Prompt 模板

所有 prompt 用英文输出，结尾统一加 `high quality, professional photography`。

---

## 默认风格：幽默搞笑

**图片默认采用轻松幽默的视觉风格。** 除非 `marketing-context.md` 另有指定，否则优先使用以下风格关键词：

```
vibrant colors, playful composition, exaggerated expressions or props,
warm energetic lighting, fun and lighthearted mood,
high quality, professional photography
```

- 构图优先选 **close-up**（夸张表情/细节）或 **eye-level**（亲切感）
- 避免过于严肃的暗色调、戏剧性大光比
- 如有人物，表情应生动、夸张、真实感强

---

## 通用 Prompt 公式

```
[subject] [action],
[scene/background],
[style], [lighting], [mood/color tone],
[composition],
high quality, professional photography
```

**Composition 选项：** overhead shot / close-up / eye-level / rule of thirds / centered / wide establishing shot

---

## Single Feed（单图）

**aspect_ratio：** Instagram/Facebook Feed `"1:1"` 或 `"4:5"`；LinkedIn/Facebook Wide `"16:9"`

```
[subject] [action], [scene/background],
[style], [lighting], [mood/color tone],
[composition: overhead / close-up / eye-level / rule of thirds],
high quality, professional photography
```

**示例：**
```
steaming bowl of ramen on a dark wooden table, chopsticks resting on the side,
moody restaurant atmosphere, warm amber lighting, rich deep tones,
close-up, shallow depth of field,
high quality, professional photography
```

---

## Carousel（多图系列）

**aspect_ratio：** 统一 `"1:1"`（所有张保持一致）

先从 `marketing-context.md` 锁定 `base_style`，再逐张变 subject/action/scene：

```
# base_style（全系列复用，保证视觉一致性）
[style], [lighting], [mood/color tone], consistent series, same visual style and color palette

# 每张 prompt
[subject] [action], [scene], [base_style], slide N of [总数],
high quality, professional photography
```

草稿 `## 配图路径` 按张记录：
```
第 1 张：[public_url]
第 2 张：[public_url]
...
```

---

## Story / Reels 封面

**aspect_ratio：** `"9:16"`

竖屏要求主体居中，上下留空供文字叠加：

```
[subject] [action], [scene/background],
vertical 9:16 portrait composition, subject centered in middle 72% of frame,
[style], [lighting], [mood/color tone],
clean space at top and bottom for text overlay,
high quality, professional photography
```

---

## 风格词参考

| 风格 | 英文关键词 |
|------|-----------|
| **幽默/搞笑（默认）** | `vibrant colors`, `playful composition`, `exaggerated expression`, `fun props`, `warm energetic lighting`, `lighthearted mood` |
| 餐饮/食物 | `food photography`, `steam rising`, `golden hour light`, `bokeh background` |
| 商业/专业 | `corporate clean`, `minimalist`, `white background`, `studio lighting` |
| 生活方式 | `lifestyle photography`, `candid moment`, `natural daylight`, `warm tones` |
| 奢华/高端 | `luxury aesthetic`, `dramatic shadows`, `dark moody`, `fine dining` |
| 温情/真实 | `authentic documentary`, `natural light`, `candid`, `soft pastel tones` |
| 活力/年轻 | `vibrant colors`, `dynamic composition`, `energetic`, `bright and bold` |
