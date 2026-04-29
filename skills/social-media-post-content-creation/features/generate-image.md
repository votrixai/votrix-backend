# Generate Image

适用场景：为社交媒体生成图片内容（不叠文字排版）。单图或组图（Carousel）。

---

## 步骤 1 — 情境读取

读取 `/workspace/marketing-context.md`，提取品牌名、行业、调性、品牌构图风格、目标受众。结合用户消息确定：
- 发布主题和宣传目的
- 单图还是组图

---

## 步骤 2 — 主题设计

**单图**：确定一个清晰的画面主题。

**组图（Carousel）**：先读取 `/mnt/skills/social-media-post-content-creation/features/carousel.md`，根据宣传目的选定内容模式，规划每张的叙事角色和画面方向。

- 若用户未明确指定主题风格，默认选用**幽默互动类**。
- 若宣传目的是推广产品，优先使用**幽默种草类**，首选**产品救场**；但需检查本次对话中已使用过的模式，避免重复，依次轮换至其他幽默种草模式（避雷种草→错误打开方式→产品拟人自白→夸张测评）。

告知用户每张主题，确认后再进入风格和色彩决策。

---

## 步骤 3 — 风格决策

读取 `/mnt/skills/social-media-post-content-creation/features/styles.md`，按选择逻辑决定风格，默认 **Photography**。

根据宣传目的（情感共鸣 / 问题解决 / 冲动消费 / 信任建立 / 好奇吸引）和受众心理（普通消费者被真实场景打动、年轻消费者被视觉趋势吸引、企业决策者被专业感说服、高端消费者被克制质感说服）选定最有效的风格。

锁定 **style token**，组图所有张保持一致。

---

## 步骤 4 — 色彩体系

读取 `/mnt/skills/social-media-post-content-creation/features/colors.md`，根据品牌调性和宣传目的自行选定或组合色调关键词。色调须与 `marketing-context.md` 中记录的品牌构图风格的整体视觉氛围一致，不基于具体色值。

组图所有张使用同一色调描述。

---

## 步骤 5 — 生成

每张传入：
- 步骤 2 的画面主题
- 步骤 3 的 style token
- 步骤 4 的色调关键词
- **Composition keywords**：从 `marketing-context.md` 的品牌构图风格中提取关键词（如排版布局方式、留白偏好、元素密度等）；无记录时兜底使用 `single focal point, generous negative space, minimal elements, clean composition, focused subject, no clutter`
- 如后续需叠文字：注明 `leave clean space in [位置] for text overlay`
- `negative_prompt`：`text, watermark, logo, typography, busy background, cluttered, multiple competing subjects, decorative noise, visual complexity`

**组图一致性**：第 2 张起传入第 1 张作为 reference image，保持人物 / 场景 / 风格连贯。

---

## 步骤 6 — 质量检查

| 检查项 | 合格标准 |
|--------|---------|
| 无文字 | 图中无任何文字或水印 |
| 主题准确 | 画面内容与主题描述匹配 |
| 留白充足 | 需叠文字区域干净 |
| 组图一致 | 各张风格 / 色调统一 |

不合格则补充描述重新生成。

---

## 输出

调用 `show_post_preview`，slides 按张传入路径，caption 简述内容方向，hashtags 按品牌和内容填写。
