---
name: poster-design
description: >
  完整海报设计流程。从零开始设计可直接发布的宣传海报（单张或 Carousel 组图）：情境读取、叙事规划、文案创作、风格决策、排版设计、色彩系统、素材生成、Pillow合成、质量复查。
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
- **发布尺寸**：单张从平台推断，推断不出默认 1080×1080；Carousel 固定 1080×1350px
- **品牌素材**：读取 `marketing-context.md` 的「品牌素材」节，提取 Logo 和吉祥物路径列表（可为空）

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

## 步骤 3 — 风格决策

始终默认使用 `photographic`（写实摄影风格）——这是标准选择，效果最好。锁定 style token，贯穿全程不更改；Carousel 所有张保持一致。

只有客户明确指定其他风格时才切换，且必须提供具体风格名称（如 `anime`、`cinematic`、`digital-art`、`fantasy-art`、`comic-book`、`pixel-art`）。不接受「插画」「卡通」这类笼统描述，不根据受众或语气自行推断风格。

**图片必须 clean**：生成图片背景干净、主体清晰、无视觉杂乱。在步骤 6 生图 prompt 中必须加入 `clean background, clear subject, no visual clutter`。

---

## 步骤 4 — 排版设计

根据海报模式选定模板，记录选定模板，步骤 6 素材生成和步骤 7 合成均依据此模板的区域定义。

- **单张**：按下方选择逻辑选定 T1–T8 之一
- **Carousel**：按叙事角色对应选定——Hook → C1，Content → C2，CTA → C3

**单张模板选择逻辑**：

```
单品 + 信息量大（价格/标签/特性）  → T1 Top-image Bottom-text
单品 + 品牌感为主                  → T4 Centered Frame
多品 / 组合套装                    → T7 Grid
品牌大片 / 氛围驱动                → T3 Full Bleed
高端 + 复杂信息                    → T5 Overlay Card
产品功能介绍                       → T2 Left-image Right-text
活动公告 / 开业                    → T8 Type-dominant
年轻 / 潮流受众                    → T6 Diagonal Split
无法判断                           → T1 Top-image Bottom-text
```

> 所有坐标基于 1080×1080 画布。其他尺寸按比例缩放。安全边距：40px。

### T1 — Top-image Bottom-text
图片填满顶部 60%（y:0–648）。文字区域填满底部 40%（y:648–1080，纯色填充）。文字从上到下：主标题 → 副标题 → 价格 → 标签组 → CTA。图片不需要为文字留白。

### T2 — Left-image Right-text
左侧 50% 为产品图（x:0–540）。右侧 50% 为文字区域（x:540–1080，纯色）。文字左对齐，从上到下：主标题 → 副标题 → 特性列表 → 价格 → CTA。

### T3 — Full Bleed
图片填满 100% 画布。底部 35% 加渐变遮罩（透明 → 黑色或品牌色）。文字放在遮罩上，白色/浅色。生成图片时注意底部 35% 将被遮罩覆盖。

### T4 — Centered Frame
纯色或渐变背景。产品图居中（约 600×500，需透明背景）。主标题在上方，价格和 CTA 在下方。

### T5 — Overlay Card
背景图填满画布（可模糊处理）。半透明圆角矩形（60–80% 不透明度）置于中下区域。所有文字排列在卡片内。

### T6 — Diagonal Split
画布沿对角线分割，一侧放图片，另一侧纯色放文字。角度 15–30°。适合动感/潮流感。

### T7 — Grid
顶部标题栏（160px）。下方 2×2 网格，每格包含产品图 + 名称 + 价格。底部店铺信息。每张产品图单独生成，统一背景和构图。

### T8 — Type-dominant
纯色或渐变背景。大标题（80–120px）是视觉主角。图片可选，仅作小点缀。适合活动公告、开业。

---

> Carousel 画布：1080×1350px（4:5）。安全边距：40px。

### C1 — Bold Hero
图片填满全画布。底部 40%（y:810–1350）加渐变遮罩（透明 → 品牌深色）。主标题放在遮罩上：大字 80–100px，白色或浅色。可选副标题在主标题下方，32–40px。生成图片时注意：底部 40% 将被覆盖，顶部 60% 的构图要足够强。

### C2 — Split Content
顶部 55%（y:0–742）：图片填充，无文字。底部 45%（y:742–1350）：纯品牌色或近白色填充。文字从上到下排列在底部区域：单点主标题（56–72px）→ 正文 1–2 行（32–36px）→ 可选小标签。每张只传递一个核心信息，不堆叠多个内容。

### C3 — CTA Focus
纯品牌色背景（无主图，或右上角小点缀图，最多占画布 30%）。居中对齐文字：品牌名/Logo 占位（顶部）→ CTA 主标题 60–72px → 行动指引 34–40px（如：点击关注 / 收藏备用 / 点击跳转）→ 可选二维码或账号。高对比度，极简视觉。

---

## 步骤 5 — 色彩系统

根据客户偏好、品牌调性和海报目标受众决定配色——包含底色、主色块/装饰色、文字色、强调色（价格/CTA）、图片色调关键词（用于步骤 6 的 `mood` 参数）。若 `marketing-context.md` 有品牌色则优先使用。Carousel 所有张使用同一色调描述。

**文字颜色规则**：
- 浅底色：主标题用深色，价格/CTA 用强调色
- 深底色：主标题用 #FFFFFF，价格/CTA 用强调色
- 叠图上（T3/T5）：检测背景亮度 → 暗区（<100）用白色，亮区（>180）用深色，中间调加半透明遮罩后用白色

---

## 步骤 6 — 素材生成

### 6a. 主图素材

**用户有 Reference Image 且清晰** → 直接用于合成，跳过生成。

**用户有 Reference Image 但模糊或质量差** → 以 reference 为参考重新生成，提升质量和风格一致性。

**用户无 Reference Image** → 将以下参数交给 generate-image skill 执行生成。generate-image skill 负责参数锁定、风格锚提取、逐张生成与每张审查的完整流程。

---

#### 参数映射（poster-design → generate-image）

| generate-image 参数 | 取值来源 |
|---|---|
| `prompt` | 步骤 2 确认的文案主题 + 下方模板区域约束 |
| `style` | 步骤 3 的 style token |
| `mood` | 步骤 5 的 Image Tone Keywords——整套图共用同一描述，不因每张主题不同而改变 |
| `composition` | 下方模板区域约束（含留白指令） |
| `context` | 步骤 1 的用途（`poster-background` / `social-media` 等） |
| `aspect_ratio` | 步骤 1 的发布尺寸 |
| `negative_elements` | `text, typography, letters, numbers, watermark, busy background, cluttered, decorative noise` |
| `reference_image_urls` | 用户上传的风格参考图（如有） |

> `negative_elements` 始终包含 `text` 和 `typography`：图片生成模型无法可靠渲染文字，任何生成出来的文字都会变形或乱码。文字统一在步骤 7 Pillow 合成阶段写入。

---

#### 模板区域约束（传入 `composition`）

| 模板 | composition 约束 |
|------|----------------|
| T1 | subject fills top 60% of frame, composed for 1080×648, subject fully visible within this area |
| T2 | subject fills left 50% of frame, composed for 540×1080 |
| T3 | full frame 1080×1080, subject in top 65%, leave clean space in bottom 35% for gradient overlay |
| T4 | transparent background, centered subject, approximately 600×500 area |
| T5 | full frame, keep subject toward top or side, center-bottom area will be covered by a card overlay |
| T6 | full frame, diagonal split composition, subject on one side |
| T7 | multiple small images, unified background color and framing across each |
| T8 | small optional image, not the visual focal point |
| C1 | full frame 1080×1350, subject in top 60%, leave clean space in bottom 40% for gradient overlay |
| C2 | subject fills top 55% of frame, composed for 1080×742 |
| C3 | no main image needed — skip generation |

### 6b. 背景图

| 模板 | 处理方式 |
|------|---------|
| T3（全出血）/ T5（叠层卡片）/ C1（Bold Hero） | 生成纹理或渐变背景图 |
| T1 / T2 / T4 / T6 / T7 / T8 / C2 / C3 | 用步骤 5 的底色在 Pillow 中直接绘制，无需生成 |

---

## 步骤 7 — Pillow 合成

**逐张独立合成**，每张按以下顺序执行，完成并通过步骤 8 质量复查后再处理下一张。

### 合成层顺序

```
底色/背景图 → 主图素材 → 吉祥物（用户明确要求时）→ 渐变遮罩（如需）→ 色块 → 装饰线 → 文字层 → Logo
```

文字层永远在最上层，任何元素不得覆盖文字。

### 字体选择

- 中文：NotoSansCJK 系列（Bold → 主标题，Medium → 副标题，Regular → 正文，Light → 小字，Black → 大价格）
- 高端/文化语境：改用 NotoSerifCJK 系列
- 英文/数字：从 `canvas-fonts/` 目录按风格选取
- 中文字体路径：`/usr/share/fonts/opentype/noto/NotoSansCJK-{Weight}.ttc`

### 字号层级

| 级别 | 用途 | 字号 |
|------|------|------|
| L1 | 价格 / 关键数字 | 80–160px |
| L2 | 主标题 | 48–72px |
| L3 | 副标题 / 特性 | 26–36px |
| L4 | 标签组 | 24–32px |
| L5 | 联系方式 / 小字 | 20–26px |

### 每张合成流程

**① 加载图片**
加载当前张的原始图片素材。

**② 确定文字区域坐标**
根据步骤 4 选定的模板区域定义确定当前张的文字区域范围（x0, y0, x1, y1）。

**③ 分析亮度 → 决定遮罩和文字颜色**

```python
region = canvas.crop((x0, y0, x1, y1)).convert("L")
brightness = sum(region.getdata()) / (region.width * region.height)
```

| 亮度值 | 处理 |
|--------|------|
| > 180 | 加深遮罩（alpha 180–220），白色文字 |
| 60–180 | 半透明遮罩（alpha 120–160），白色文字 |
| < 60 | 轻遮罩或不加（alpha 60–100），白色文字 |

始终在背景图合成完成后、文字绘制前计算亮度。

**④ 动态计算字号和换行**

1. 从模板最大字号开始（L2 主标题：72px，L3 副标题：34px）
2. 用 `draw.textbbox((0, 0), text, font=font)[2]` 测量文字宽度
3. 超出区域宽度则每次减小 4px，重复直至不超出
4. 最小字号下限：主标题 36px，正文 22px
5. 确定最终字号后，先执行逐字换行（规则见下），再绘制

**⑤ 按层顺序合成**（见上方「合成层顺序」）

**⑥ 保存，进入步骤 8 质量复查**

### 强制规则

1. **防溢出**：绘制任何文字前用 `getbbox` 检查宽度，超出 `canvas_width - 80px` 则逐步缩小字号
2. **防重叠**：追踪每个文字元素的边界框（x0, y0, x1, y1），后续文字不得与之相交
3. **透明合成**：粘贴含 alpha 的图片时，始终传入第三个 mask 参数：`canvas.paste(img, pos, img)`
4. **图片填充**：用等比缩放 + 居中裁切（cover 模式），不得用 raw resize 拉伸
5. **颜色格式**：Pillow fill 使用 RGB 元组 `(R, G, B)`，不用 hex 字符串
6. **标签组换行**：横向排列标签，用 `getbbox` 计算每个标签宽度，超出右边界则换行
7. **渐变遮罩**：逐行绘制，alpha 从 0 渐变到目标值，避免色带
8. **画布尺寸**：在脚本顶部硬编码 `(1080, 1080)`，不从图片尺寸推导
9. **符号安全**：不用装饰性 Unicode 符号（✦ ✿ ★ ◆ ❤ ✔ 等）作为文字字符——NotoSansCJK 不覆盖这些字符会渲染为 □。改用 Pillow 几何图形，或加载 `/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf` 作为专用符号字体
10. **图片模式规范化**：每次 `paste()` 前用 `img.convert("RGBA")` 转换源图；所有合成完成后用 `canvas.convert("RGB")` 转换最终画布再保存
11. **多行文字换行**：不能只靠缩小字号处理长文本。实现逐字换行：逐字符累加直到 `getbbox` 宽度超过允许区域，再换行。在字号缩小之前先执行换行
12. **行间距**：行高 = 字号 × 1.4（中文），× 1.25（英文/数字）。不能只用字号叠加行距
13. **中英文字体分离**：中文字符用 NotoSansCJK，英文字母（A–Z, a–z, 0–9, 标点）用 `canvas-fonts/` 中匹配的字体。混合字符串按字符范围拆分，各自用对应字体对象绘制

### 输出路径

**单张**：`/mnt/session/outputs/poster_{slug}.png`

**Carousel**：`/mnt/session/outputs/poster_{slug}_slide{n}.png`

### Logo 合成（`marketing-context.md` 的「品牌素材 → Logo」有路径时执行）

- **质量预处理**：logo 无透明背景 → 先用 `rembg` 或阈值抠图去背；分辨率低或边缘模糊 → 直接做单色化处理（提取 alpha 通道形状，填充海报 `text_color`）
- **多路径选择**：有多个路径时，分析 logo 落点区域背景亮度：亮背景（> 128）用第一个，暗背景（≤ 128）用第二个；只有一个路径则做单色化处理
- **位置与尺寸**：右下角，距边 24px；宽度不超过画布宽度的 12%，保持原比例
- 用 Pillow `Image.alpha_composite` 合成，保留透明通道
- **生成新版本时**：将处理后的文件存入 `/workspace/assets/`，并在 `marketing-context.md` 的「品牌素材」对应字段追加一行 `路径 — 备注`

### 吉祥物合成（仅用户明确要求加吉祥物时执行）

- 位置由步骤 4 所选模板定义；尺寸：高度不超过画布高度的 35%，保持原比例
- 直接 paste，无需混合模式

### 报错处理

| 错误 | 处理 |
|------|------|
| `FileNotFoundError` | 检查路径；URL 先用 requests 下载到本地 |
| `OSError: cannot open resource` | 中文字体写死 `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc` |
| 输出文件为空 | 检查 `canvas.save()` 是否执行 |

---

## 步骤 8 — 质量复查

**每张合成后立即执行**，不等 Carousel 全部完成。读取输出图片，严格逐项检查。发现任何问题立即修正脚本重做当前张，确认合格后再继续下一张。

| 检查项 | 合格标准 | 不合格处理 |
|--------|---------|----------|
| **文字对比度** | 每条文字与其背景区域对比度明显，小字也清晰可读 | 调整文字颜色或加深遮罩后重做 |
| **文字溢出** | 没有任何文字被裁切到画布外 | 缩小字号或调整位置后重做 |
| **文字重叠** | 各文字层之间无覆盖，标签组无堆叠 | 重新计算间距后重做 |
| 文字完整 | 步骤 2 确认的所有文案都出现在图上 | 补充缺失内容后重做 |
| 无乱码 | 中文正常显示，无 □□□ | 检查字体路径后重做 |
| 无方块字符 | 所有装饰符号正常显示，无 □ | 改用 Pillow 几何图形或 NotoSansSymbols2 后重做 |
| 图片未变形 | 背景比例正常，主体未被裁切 | 修正 crop 逻辑后重做 |
| 风格一致 | 步骤 3 的 style 在视觉上体现；Carousel 各张视觉统一 | — |
| 信息不冗余 | 同一信息没有两处重复出现 | — |

最多 3 轮重做。3 轮后仍有问题 → 说明卡在哪项，请求进一步指导。

---

## 输出

调用 `show_post_preview` 工具展示海报：
- **单张**：`slides: [{ path: "/mnt/session/outputs/poster_{slug}.png", label: "海报" }]`
- **Carousel**：`slides` 按张传入所有路径，`label` 标注第几张及叙事角色（如"第 1 张 · Hook"）
- `caption`：一句话说明核心排版决策
- `hashtags`：`[]`
