# How to Test Agents

## 概览

测试系统基于文件 I/O：
- `tests/e2e/test_input.txt` — 往里写消息，agent 会读取并处理
- `tests/e2e/test_output.txt` — agent 的完整回复都写在这里，包括 tool calls 和结果

---

## 快速启动

### 第一次启动（全量 provision）

```bash
cd votrix-backend
python tests/e2e/test_post_agent.py --force
```

`--force` 会：
1. 重新上传 skills 到 Anthropic
2. 为测试 user 创建 Anthropic managed agent
3. 自动连接 API_KEY 类型的 integrations（如 Apollo）
4. 创建 Composio MCP server
5. 启动 file-watching loop，等待输入

### 跳过 provision，复用上次 agent（快速重启）

```bash
python tests/e2e/test_post_agent.py --skip-provision
```

适合：修改了代码逻辑（非 config/skill），想快速重启的情况。

### 发单条消息然后退出（适合 CI 或脚本）

```bash
python tests/e2e/test_post_agent.py --skip-provision --message "你好"
```

### 附带文件

```bash
python tests/e2e/test_post_agent.py --skip-provision --attach /path/to/file.png --message "帮我用这张图做帖子"
```

---

## 发消息的方式

Agent 启动后进入 watch loop，有两种方式写消息：

### 方式 1：直接写文件（推荐）

```bash
echo "帮我连接 instagram 账号" > tests/e2e/test_input.txt
```

**重要**：用 `>` 覆盖，不要用 `>>` 追加。Agent 每处理完一条消息就会清空 input 文件，
如果用 `>>` 追加旧内容会被重复发送。

### 方式 2：--message 参数（单次，exit 后）

```bash
python tests/e2e/test_post_agent.py --skip-provision --message "你好"
```

---

## 查看输出

### 实时跟踪（推荐）

```bash
tail -f tests/e2e/test_output.txt
```

### 搜索特定内容

```bash
grep -A5 "tool:" tests/e2e/test_output.txt      # 所有 tool calls
grep "ERROR\|error" tests/e2e/test_output.txt   # 所有错误
grep "\[done\]" tests/e2e/test_output.txt       # 每轮耗时
```

输出格式：
```
────────────────────────────────────────────────────────────
[user] 用户消息
────────────────────────────────────────────────────────────

agent 回复文字...
  ↳ [tool: TOOL_NAME] {"param": "value"}
  ↳ [result] 工具返回结果

────────────────────────────────────────────────────────────
[done] 12.3s
────────────────────────────────────────────────────────────
```

---

## 完整测试流程（post-agent）

每一步等 `[done]` 出现后再发下一条：

```bash
# 0. 启动 agent（第一次用 --force，之后用 --skip-provision）
python tests/e2e/test_post_agent.py --force

# ── 阶段一：Setup ──────────────────────────────────────

# 1. 触发 setup 流程（agent 会问店名/网站，然后自动搜索填充资料）
echo "帮我完成初始设置" > tests/e2e/test_input.txt

# 2. 回答 agent 问的店名（用你自己的或以下示例）
echo "我们的店叫晨光咖啡，在上海静安区，网站是 morninglight.coffee" > tests/e2e/test_input.txt

# 3. agent 搜索后会展示业务资料 + 运营方案，确认：
echo "看起来不错，就这样吧，发布前需要我确认" > tests/e2e/test_input.txt

# ── 阶段二：平台连接 ──────────────────────────────────

# 4. 连接 Instagram（OAuth）
echo "帮我连接 instagram" > tests/e2e/test_input.txt
# → agent 返回 redirect_url，用户点击授权

# 5. 连接 Twitter（OAuth）
echo "instagram 已授权，帮我连接 twitter" > tests/e2e/test_input.txt
# → agent 返回 redirect_url，用户点击授权

# ── 阶段三：内容创作 ──────────────────────────────────

# 6. 让 agent 创作一条帖子
echo "帮我写一条关于周末特价拿铁的 instagram 帖子，配上图片" > tests/e2e/test_input.txt

# ── 阶段四：文件工具 ──────────────────────────────────

# 7. 测试 download_file（agent 生成图片后自动调用）
echo "把刚才生成的图片给我下载" > tests/e2e/test_input.txt

# 8. 测试 publish_file（生成公开 URL）
echo "把图片发布成公开链接" > tests/e2e/test_input.txt
```

---

## 常见问题

### "No connected account found for user ID xxx for toolkit apollo"

Apollo 自动连接失败。重新 provision：
```bash
python tests/e2e/test_post_agent.py --force
```

### Instagram 帖子发了但看不到

Instagram Graph API 是两步流程：
1. `INSTAGRAM_POST_IG_USER_MEDIA` → 创建 container，返回 container_id
2. `INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH` → 真正发布

Agent 有时只做第一步。发现时让 agent 执行第二步即可。

### billing_error: credit balance too low

Anthropic API 余额不足。去 console.anthropic.com → Plans & Billing 充值。

### 重复消息被处理多次

**根本原因：多个 watch loop 进程同时监听同一个 input.txt。**

```bash
pkill -f "test_post_agent.py"
ps aux | grep test_post_agent | grep -v grep  # 确认干净
```

不要用 `>>` 追加消息，用 `>` 覆盖写入。

### Sessions 是完全隔离的（无跨 session 记忆）

每个新 session 都是完全独立的对话，不会继承其他 session 的历史。

### [overloaded] 错误

Anthropic API 繁忙，agent 会自动等待 20s 后重试，无需手动干预。

---

## 关键文件

| 文件 | 作用 |
|------|------|
| `tests/e2e/test_post_agent.py` | 测试主脚本 |
| `tests/e2e/test_input.txt` | 往这里写消息 |
| `tests/e2e/test_output.txt` | agent 回复写在这里 |
| `tests/e2e/.post_agent_cache.json` | 缓存 agent_id/env_id/session_id（gitignored） |
| `agents/post-agent/config.json` | agent 配置（model、integrations、tools） |
| `app/management/provisioning.py` | provision 逻辑 |
| `app/tools/oauth.py` | manage_connections tool，OAuth redirect 流程 |
| `app/integrations/composio.py` | Composio REST API 封装 |
