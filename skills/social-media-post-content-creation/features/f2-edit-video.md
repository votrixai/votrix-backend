# F2 — 图片/视频素材合成短视频

**适用场景**：商家有若干实拍照片或视频片段，需要剪辑拼接成短视频发布。

**核心工具**：ffmpeg（AI 生成命令，沙盒运行）

**与 F4 的区别**：F2 只用商家已有素材，不生成新视频内容。

---

## 步骤 1：收集信息

确认以下信息，缺什么问什么：

- **素材文件**：所有图片/视频的路径或 URL，逐一列出
- **视频主题**：这条视频想传达什么（产品展示 / 活动回顾 / 氛围种草 / 教程演示）
- **目标平台**：决定宽高比
  - Reels / TikTok / 抖音：9:16（1080×1920）
  - YouTube / LinkedIn：16:9（1920×1080）
  - 未指定默认：9:16
- **目标时长**：未提供则根据素材数量自动决定（每张图 3s，每段视频取核心片段）
- **背景音乐**（可选）：提供文件路径/URL 则混入；不提供则输出无音频版本

---

## 步骤 2：规划素材顺序

分析每个素材，确定编排顺序：

1. 找视觉冲击力最强的素材 → 放第一个（Hook）
2. 按故事逻辑或情绪递进排列中间素材
3. 最有品牌感或行动感的素材 → 放最后（CTA 区域）

每个素材确定：
- 图片：停留时长（快节奏 2s，故事型 3–4s）
- 视频片段：截取起止时间（保留核心内容，去掉冗余）
- 转场：默认淡入淡出；动感内容可用硬切

将规划结果简要告知用户，确认顺序后继续。

---

## 步骤 3：生成 ffmpeg 脚本并执行

生成完整 shell 脚本，在沙盒中逐步执行，**每步执行后验证输出文件存在且大小 > 0 再继续**。

**3.1 下载远程文件（若素材是 URL）**
```bash
curl -L "https://..." -o /tmp/asset_01.jpg
```

**3.2 统一所有素材尺寸**（避免拼接时出现黑边）
```bash
# 图片转视频片段，统一尺寸
ffmpeg -loop 1 -i asset_01.jpg \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,\
fade=t=in:st=0:d=0.3,fade=t=out:st=2.7:d=0.3" \
  -t 3 -c:v libx264 -pix_fmt yuv420p clip_01.mp4

# 视频片段截取 + 统一尺寸
ffmpeg -ss 00:00:02 -to 00:00:08 -i asset_02.mp4 \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" \
  -c:v libx264 -c:a aac clip_02.mp4
```

**3.3 生成 concat 列表并拼接**
```bash
# filelist.txt 内容：
# file 'clip_01.mp4'
# file 'clip_02.mp4'
# ...

ffmpeg -f concat -safe 0 -i filelist.txt -c copy merged.mp4
```

**3.4 混入背景音乐（如果用户提供了音乐）**
```bash
ffmpeg -i merged.mp4 -stream_loop -1 -i music.mp3 \
  -shortest -map 0:v -map 1:a -c:v copy -c:a aac final.mp4
```

**3.5 加结尾 CTA 字幕（最后 4s）**
```bash
ffmpeg -i final.mp4 \
  -vf "drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:\
text='[CTA文字]':fontsize=48:fontcolor=white:\
box=1:boxcolor=black@0.5:boxborderw=10:\
x=(w-text_w)/2:y=h*0.85:enable='gte(t,VIDEO_END-4)'" \
  output.mp4
```

输出保存至 `/workspace/assets/video_{slug}.mp4`

---

## 步骤 4：质量复查

用 ffprobe 检查输出文件，不合格则修正后重新执行对应步骤：

```bash
ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=width,height,codec_type -of default output.mp4
```

| 检查项 | 合格标准 |
|-------|---------|
| 文件存在且有内容 | size > 0 |
| 时长符合预期 | duration 与规划时长接近（±2s 内） |
| 尺寸正确 | width × height 与目标平台匹配 |
| 视频流存在 | codec_type=video 出现 |
| 音频流（若有音乐）| codec_type=audio 出现 |

**字幕安全区**：CTA 文字 x/y 坐标距画布边缘 ≥ 80px，避免被平台 UI 遮挡。

---

## 步骤 5：生成文案

为视频配套 caption。

**原则**：
- 不描述视频内容（用户看得到）
- 补充视频没有呈现的信息：价格、地址、活动时间、报名方式等
- Hook 可以是视频开场画面的文字呼应

**Hashtag**：5–12 个，大众标签 + 垂直标签 + 地理标签组合

---

## 输出

向用户展示：
1. 视频文件路径（时长 + 素材数量）
2. Caption + Hashtags
3. 询问：满意直接发布，还是调整素材顺序/节奏/文案？
