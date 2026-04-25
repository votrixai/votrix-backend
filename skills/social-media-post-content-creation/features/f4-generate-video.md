# F4 — 剧本 + 参考图生成叙事视频

**工具**：`image_generate`（起始帧）+ `video_generate`（Veo 3，image-to-video）+ ffmpeg 拼接

---

## 步骤 1：确认必要信息

从上下文推断，**只问真正缺少的**：

| 信息 | 处理方式 |
|------|---------|
| 品牌色 / 语气 / 行业 | 从 `marketing-context.md` 读取；没有则用默认（幽默搞笑） |
| 平台 / 宽高比 | 从对话推断；无法推断默认 9:16 |
| 视频风格 | 从品牌语气推断；无法推断默认轻松幽默 |
| **故事思路** | **唯一必问项** |
| **目标时长** | 未提供则根据场景数推算（每场 8s × N 场景） |

---

## 步骤 2：规划场景

根据故事思路 + 品牌语气推断叙事弧线，**直接规划，不询问用户**：

- 痛点 / 功能展示 → 问题→解决（默认）
- 品牌故事 / 幕后 → 幕后故事
- 新品 / 卖点 → 产品英雄
- 顾客体验 → 顾客时刻
- 活动促销 → 促销限时

每场只支持 4s / 6s / 8s，按目标时长规划场景数：

| 目标时长 | 场景数 | 每场时长 |
|---------|-------|---------|
| ~24s | 3 场 | 8s |
| ~32s | 4 场 | 8s |
| ~48s | 6 场 | 8s |

将场景表（场景号 + 一句话画面描述 + 叙事角色）简要告知用户，**确认后再生成**。

---

## 步骤 3：锁定 character_anchor

从行业推导人物，服装取品牌主色：

```
[性别] [年龄段] [行业角色], wearing [品牌色服装], [发型], [体型]
```

**每场 prompt 原样粘贴，只改动作部分。**

---

## 步骤 4：准备各场景起始帧

每场视频需要一张起始图，来源按优先级判断：

1. **用户有提供参考图** → 直接用，从中选与本场画面最接近的一张
2. **用户没有参考图** → 用 `image_generate` 生成：
   - Prompt：`character_anchor` + 本场动作 + 行业场景 + 品牌色调
   - 尺寸：与视频宽高比一致（9:16 → 1080×1920，16:9 → 1920×1080）
   - 固定结尾：`No text, no watermarks. Cinematic still frame.`

---

## 步骤 5：逐场景生成视频

对每张起始帧调用 `video_generate`（image-to-video 模式）：

**Prompt 格式**（一句话，一个动作）：

```
[character_anchor], [单一动作/状态变化], [简单环境]. [运镜]. [音频描述].
```

示例：
```
A barista in a navy apron smiles and slides a coffee cup across the counter. Slow push in. Warm upbeat background music.
```

**调用参数：**
```
image: [本场起始帧]
prompt: [上述一句话 prompt]
aspect_ratio: "9:16" 或 "16:9"
duration_seconds: 8
negative_prompt: "text overlay, watermark, blurry"
```

每场生成后确认 `status: true` + URL 有效。视觉质量由用户预览确认，Claude 无法播放视频。

---

## 步骤 6：ffmpeg 拼接

```bash
# 统一尺寸
for i in scene_*.mp4; do
  ffmpeg -i "$i" -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" \
    -c:v libx264 -c:a aac "norm_${i}"
done

# 拼接
ls norm_scene_*.mp4 | sort | awk '{print "file "$0}' > filelist.txt
ffmpeg -f concat -safe 0 -i filelist.txt -c:v libx264 -c:a aac final.mp4
```

---

## 步骤 7：用户预览 + 文案

展示最终视频 URL，询问：哪个场景不理想（可单独重生成替换）/ 整体风格是否符合预期。

同时生成配套 caption：情感共鸣优先，补充视频没有呈现的信息（价格/地址/活动时间），结尾引导行动。Hashtag 5-12 个。
