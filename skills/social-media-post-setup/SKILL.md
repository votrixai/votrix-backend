---
name: social-media-post-setup
description: "社交媒体营销助手初始化配置。Admin 提到 setup、配置、连接平台、更新业务资料时触发。也在 admin 首次使用、尚未完成配置时主动触发。"
---

# Setup — 初始化配置

## 持久化目录（跨会话）

- **Markdown 状态与文案**（配置、草稿、发布记录、报告等）：`mnt/memory/social-media-manager/`
- **该目录仅可存 `.md` 文件。** 图片、视频等二进制不得写入此处；须先 `publish_file` 得到公网 URL，再把 URL 写进上述 markdown。

## 启动检查

读取 `mnt/memory/social-media-manager/marketing-context.md`：

- **不存在** → 读取模板 `/workspace/skills/social-media-post-setup/templates/marketing-context.md`，在记忆目录创建 `marketing-context.md`，从头走完整流程
- **存在但有空字段** → 只补充缺失部分
- **Admin 指定某项**（如「帮我连 Instagram」）→ 直接跳到对应阶段

---

## 阶段 1 — 品牌信息

问 admin 一件事：「你们的店名或网站是什么？」

拿到后用 `web_search` / `web_fetch` 自行整理：
- 行业、地区、简介、主要产品 / 服务、目标受众
- 品牌调性（从官网文案推断）
- 内容氛围 / Mood（从官网整体视觉风格推断，如高端质感、温暖亲切、专业严肃、活泼趣味等；推断不出则留空，**不得默认填「清新明亮」**）
- 品牌构图风格（从官网视觉设计推断：排版布局、元素构成、留白比例、图文关系、整体视觉氛围等）
- 时区（从官网地址、联系页、About 页推断，格式 `Asia/Shanghai`；推断不到则列为待确认）

一次性展示给 admin 确认，搜不到的字段才单独询问（时区推断不到时必问）。

---

## 阶段 2 — 品牌素材

根据阶段 1 已获取的信息，自行从官网整理可用的品牌素材（Logo、宣传图、短视频等）。

1. 将下载或生成的**二进制文件**先落到 `/mnt/session/outputs/`（仅会话内临时路径）。
2. 每个需长期使用的文件调用 `publish_file(file_path="...")`，取得**公网 URL**（发帖与多技能引用只认 URL，不认沙箱路径）。
3. 把 URL 与备注写入 `mnt/memory/social-media-manager/marketing-context.md` 的 `## 品牌资料`（如 **Logo URL**）与 `## 品牌素材`（每行：`https://... — 备注`）。

若 admin 直接提供可公开访问的图片/视频链接，校验后可直接写入上述 markdown，无需再 publish。抓不到的再问 admin。

---

## 阶段 3 — 平台连接

询问 admin 想连接哪些平台（Facebook / Instagram / Twitter / LinkedIn，可多选）。

每个平台独立处理，参考 `/workspace/skills/social-media-post-setup/references/platform-connections.md`。

连接成功后，拉取该账号近期发布的帖子，补充或修正 `mnt/memory/social-media-manager/marketing-context.md` 中的品牌视觉信息：图片风格、构图方式、内容调性、内容氛围 / Mood。**以历史帖的实际风格为准**，覆盖阶段 1 从官网推断的 Mood（官网推断仅作初始参考）。

连接状态实时写入该文件 `## 已连接平台`，成功标记 `启用: true`，跳过或失败标记 `启用: false`。

---

## 阶段 4 — 运营方案

根据行业 + 已连接平台，生成内容方向和发布节奏：

**内容方向分配**：从以下 15 个内容类型中，结合商家的行业、品牌风格、目标受众、已连接平台，自行判断选出 3–5 个最适合的类型，分配发布比例（合计 100%）。判断时综合考虑行业适配性与各平台内容特性（如 Instagram 适合视觉化和幽默内容涨粉，LinkedIn 适合干货和观点类）。

适用平台：Facebook · Instagram · X (Twitter) · LinkedIn · YouTube · TikTok

1. Educational / Tips & Tricks
2. Humor / Memes
3. Product Showcase / Recommendations
4. User-Generated Content (UGC)
5. Behind the Scenes
6. KOL / Influencer Collaborations
7. Trending Topics / Newsjacking
8. Interactive (Polls, Q&A, Giveaways)
9. Brand Story / Emotional
10. Promotions / Sales
11. Data / Rankings / Listicles
12. Recurring Series (e.g. Monday Motivation, Friday Picks)
13. Hot Takes / Opinion
14. Tutorials / How-to
15. Social Responsibility / CSR

**发布节奏**：
- 餐饮 / 零售 / 生活方式：每平台每周 3–4 条
- 本地服务：每平台每周 2–3 条
- B2B / 专业服务：LinkedIn / Twitter 每周 2–3 条
- Facebook 与 Instagram 同时连接时：Facebook 跟随 IG 同步，不单独创作

**工作流**（时间根据行业和 admin 偏好调整，以下仅供参考）：

| 任务 | 参考时间 |
|------|---------|
| 内容共创 | 每周一 09:00 |
| 内容发布 | 每天 09:00 |
| 周报 | 每周五 18:00 |

周报任务：汇总本周新评论 + 各平台数据表现，生成一份简报发给 admin。

以对话语气呈现方案给 admin，只问一个问题：「内容共创时间安排在每周几、几点？」

Admin 确认后，一次性将内容方向分配、发布节奏、工作流配置写入 `mnt/memory/social-media-manager/marketing-context.md` 对应字段，再依次调用 `cron_create` 注册工作流任务。所有时间均基于 `品牌资料.时区` 中记录的时区。Admin 明确不需要某项时跳过对应 cron，写入 `启用: false`。

---

## 后续更新

Admin 想修改配置时，读取当前文件，只处理需要改的部分。涉及工作流时间变更，先 `cron_delete` 旧任务再 `cron_create` 新任务。
