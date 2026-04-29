# Generate Video

适用场景：为社交媒体生成或剪辑视频内容（Reels / Story / 短视频）。

---

## 步骤 1 — 情境读取

读取 `/workspace/marketing-context.md`，提取品牌调性、目标受众。结合用户消息确定视频主题和宣传目的。

---

## 步骤 2 — 素材判断

- **用户提供视频素材** → 直接剪辑，裁剪至目标时长，加字幕 / 配乐 / 品牌元素
- **无素材，AI 生成** → 根据主题生成视频片段，组合成完整视频

---

## 步骤 3 — 生成

传入：视频主题、风格关键词、目标时长、尺寸（竖版 9:16 / 方形 1:1）。

`negative_prompt`：`text, watermark, logo`

---

## 步骤 4 — 输出

调用 `show_post_preview`，slides 传入视频路径，caption 简述内容方向，hashtags 按品牌填写。
