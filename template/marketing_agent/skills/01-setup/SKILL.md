---
name: 01-setup
description: "初始化和配置营销助手。当 admin 说「setup」「配置」「连接平台」「连接 Facebook / Instagram / Twitter / LinkedIn / Yelp」「更新业务资料」「更新内容设置」时触发。首次使用前必须运行。"
---

# Setup — 初始化配置

你是这位商家的营销助手。Setup 的目标是收集必要信息，写入 `user-files/marketing-context.md`，让所有其他功能可以正常运行。

---

## 启动检查

先尝试读取 `user-files/marketing-context.md`（用户的实际配置文件）：

- **文件不存在** → 读取 `skills/01-setup/templates/marketing-context.md` 作为结构模板，从头走完整流程（阶段一 → 二 → 三 → 四），完成后按模板结构写入 `user-files/marketing-context.md`
- **文件存在，部分字段为空** → 只补充缺失的部分，已填的不重复问
- **Admin 指定某项**（如「帮我连 Instagram」「更新内容设置」）→ 直接跳到对应阶段

---

## 阶段一：业务资料

收集商家的基础业务信息，填入文件的 `## 业务资料` 和 `## 品牌语气` 部分。

**原则：能推断的不问。** 如果 admin 说「我是广州一家咖啡厅」，直接推断行业是餐饮、目标受众是本地消费者，只做一次确认，不逐字段询问。

需要收集：
- 业务名称、行业、网站
- 一句话简介（用于内容创作时的定位参考）
- 目标受众（年龄、兴趣、地区）
- 主要产品 / 服务
- 竞争对手品牌（2–3 个，用于市场调研）
- 品牌语气：风格、应该做的、避免的

---

## 阶段二：内容设置

收集内容创作偏好，填入文件的 `## 内容设置` 部分。

### 内容主题（Pillars）

告诉 admin：
> 「内容主题是你们日常发帖的几个固定方向，比如『产品推广』『行业知识』『幕后故事』。通常 3–5 个就够了。」

根据行业给出建议选项，让 admin 确认或修改，不要让他从零填写。

### Hashtag 偏好

可选。有则按主题分组收集，没有就跳过，内容创作时再生成。

### 发布行为

询问：
> 「内容生成好后，需要你来确认才发出去，还是我直接发？」

将 admin 的回答转成一条自然语言指令，写入 `## 指令` 部分，例如：
- 需要确认 → 「内容创作完成后发布前需要等待我的确认。」
- 直接发布 → 「内容创作完成后直接发布，不需要等待确认。」

### 图片风格

询问：
> 「如果需要 AI 生成配图，你们偏好哪种风格？比如真实照片感、插画、品牌色系简洁设计？」

---

## 阶段三：工作流配置

询问 admin 要开启哪些自动化任务：

> 「我可以帮你自动化日常运营的三件事，你选需要的开启：
> 1. **内容创作** — 每天定时生成帖子草稿，你只需要过来确认就能发布
> 2. **评论巡查** — 定时检查各平台新评论，差评优先推给你处理
> 3. **数据汇报** — 定期生成表现报告，了解增长趋势
>
> 需要开启哪些？」

对每项开启的任务，收集配置后：
1. 写入 `user-files/marketing-context.md` 的 `## 工作流` 对应部分（人类可读）
2. 调用 `cron_create` 注册实际调度任务

### 内容创作

- 询问每天几点生成（建议早上 8 点，admin 开始工作前准备好）
- 询问要生成哪些平台的内容
- 发布行为已在 `## 指令` 中写好，此处无需再问
- 将 `启用: true`、触发时间、目标平台写入 `## 工作流 → 内容创作`
- 调用 `cron_create(cron_expr="0 8 * * *", message="[cron] 内容创作", description="每天 8:00 生成内容草稿")`

### 评论巡查

- 固定每 6 小时巡查一次，无需询问时间
- 说明：负面评论会归档到 review-history，admin 登录后可看到待处理列表
- 将 `启用: true`、`触发间隔: 每 6 小时` 写入 `## 工作流 → 评论巡查`
- 调用 `cron_create(cron_expr="0 */6 * * *", message="[cron] 评论巡查", description="每 6 小时巡查各平台评论")`

### 数据汇报

- 询问汇报频率和时间（建议每周一早上 9 点）
- 询问报告类型（快速总结 / 完整月报），默认快速总结
- 将 `启用: true`、触发时间、报告类型写入 `## 工作流 → 数据汇报`
- 调用 `cron_create(cron_expr="0 9 * * 1", message="[cron] 数据汇报", description="每周一 9:00 生成表现报告")`

未开启的项，对应字段写 `启用: false`，不调用 `cron_create`。

所有工作流配置写完后，告知 admin：
> 「工作流已配置完成，定时任务已注册。系统会按设置的时间自动运行，你不需要做任何额外操作。」

---

## 阶段四：平台连接

询问 admin 想连接哪些平台：

> 「你想在哪些平台上发内容或管理评论？Facebook、Instagram、Twitter、LinkedIn、Yelp，可以多选，也可以之后再加。」

每个平台独立处理，一个失败不影响其他。连接成功后立即将账号信息填入文件对应的 section，不等所有平台完成才写。

| 平台 | 参考文档 |
|---|---|
| Facebook | `skills/01-setup/references/facebook-oauth.md` |
| Instagram | `skills/01-setup/references/instagram-oauth.md` |
| Twitter | `skills/01-setup/references/twitter-oauth.md` |
| LinkedIn | `skills/01-setup/references/linkedin-oauth.md` |
| Yelp | `skills/01-setup/references/yelp-oauth.md` |

---

## 写入文件

所有信息收集完毕后，将收集到的数据按 `skills/01-setup/templates/marketing-context.md` 的结构填入对应字段，写入 `user-files/marketing-context.md`。

始终写完整文件，不追加。未收集到的字段留空，不删除字段结构。

同时初始化以下状态文件（如不存在则创建，已存在则跳过）：

- `user-files/review-state.json` — 读取 `skills/01-setup/templates/review-state.json`，写入 `user-files/review-state.json`
- `user-files/workflow-log.md` — 写入空文件，供 cron 任务记录执行错误

写入后告知 admin：
- 哪些信息已配置
- 哪些平台已连接
- 可以开始使用哪些功能

---

## 后续更新

Admin 想修改任何配置时，读取当前文件，只讨论需要改的部分，确认后写入完整更新文件，不重新走全流程。
