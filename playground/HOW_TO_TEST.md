# How to Test Agents

## 概览

测试系统基于文件 I/O：
- `scripts/test_input.txt` — 往里写消息，agent 会读取并处理
- `scripts/test_output.txt` — agent 的完整回复都写在这里，包括 tool calls 和结果

---

## 快速启动

### 第一次启动（全量 provision）

```bash
cd votrix-backend
python scripts/test_scheduling_agent.py --force
```

`--force` 会：
1. 重新上传 skills 到 Anthropic
2. 为测试 user 创建 Anthropic managed agent
3. 自动连接 API_KEY 类型的 integrations（如 Apollo）
4. 创建 Composio MCP server
5. 启动 file-watching loop，等待输入

### 跳过 provision，复用上次 agent（快速重启）

```bash
python scripts/test_scheduling_agent.py --skip-provision
```

适合：修改了代码逻辑（非 config/skill），想快速重启的情况。

### 发单条消息然后退出（适合 CI 或脚本）

```bash
python scripts/test_scheduling_agent.py --skip-provision --message "用apollo搜索 Peter Yue"
```

---

## 发消息的方式

Agent 启动后进入 watch loop，有三种方式写消息：

### 方式 1：直接写文件（推荐，Claude Code 用这个）

```bash
echo "帮我连接 instagram 账号" > scripts/test_input.txt
```

**重要**：用 `>` 覆盖，不要用 `>>` 追加。Agent 每处理完一条消息就会清空 input 文件，
如果用 `>>` 追加旧内容会被重复发送。

### 方式 2：在终端里手动输入

打开另一个 terminal：
```bash
echo "你好" > scripts/test_input.txt
```

### 方式 3：--message 参数（单次，exit 后）

```bash
python scripts/test_scheduling_agent.py --skip-provision --message "用apollo搜索 Peter Yue"
```

---

## 查看输出

### 实时跟踪（推荐）

```bash
tail -f scripts/test_output.txt
```

### 查看最后 N 行

```bash
tail -50 scripts/test_output.txt
```

### 搜索特定内容

```bash
grep -A5 "tool:" scripts/test_output.txt      # 所有 tool calls
grep "ERROR\|error" scripts/test_output.txt   # 所有错误
grep "\[done\]" scripts/test_output.txt       # 每轮耗时
```

输出格式：
```
────────────────────────────────────────────────────────────
[user] 用户消息
────────────────────────────────────────────────────────────

agent 回复文字...
  ↳ [tool: TOOL_NAME] {"param": "value"}
  ↳ [result] 工具返回结果（截断到 120 字符）

────────────────────────────────────────────────────────────
[done] 12.3s
────────────────────────────────────────────────────────────
```

---

## 完整测试流程（以 scheduling-agent 为例）

下面是测试 Apollo + Instagram + Twitter 全链路的标准步骤，
每一步等 `[done]` 出现后再发下一条：

```bash
# 0. 启动 agent（第一次用 --force，之后用 --skip-provision）
python scripts/test_scheduling_agent.py --force

# 1. 等待 [ready] 出现，然后在另一个 terminal 里发消息：

# 步骤 0：测试 Apollo 搜索（验证 API_KEY 自动连接）
echo "用apollo搜索 Peter Yue 这个人的信息" > scripts/test_input.txt

# 步骤 1：auth Instagram（OAuth，需要用户点击 redirect_url）
echo "帮我连接 instagram 账号" > scripts/test_input.txt
# → agent 返回 redirect_url，用户点击授权

# 步骤 2：auth Twitter（同上）
echo "我完成了instagram授权，帮我连接 twitter 账号" > scripts/test_input.txt
# → agent 返回 redirect_url，用户点击授权

# 步骤 3：发 Instagram 帖子（需要先 auth）
echo "帮我生成一张AI科技风格的图片并发布到instagram，配上caption和hashtag" > scripts/test_input.txt

# 步骤 3b：Instagram 是两步流程，agent 可能只 create container 没有 publish
# 如果帖子没出现，让 agent 执行 publish 步骤：
echo "请执行 INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH 把刚才的 container 发布出去" > scripts/test_input.txt

# 步骤 4：发 Twitter 推文
echo "在twitter上发一条关于AI科技的推文，简短一点配hashtag" > scripts/test_input.txt
```

---

## 常见问题

### "No connected account found for user ID xxx for toolkit apollo"

Apollo 自动连接失败。重新 provision：
```bash
python scripts/test_scheduling_agent.py --force
```

根本原因：Composio `GET /connected_accounts?user_id=xxx` 的过滤参数不可靠，
`provisioning.py` 里已做客户端二次过滤（`item["user_id"] == entity_id`）。

### Instagram 帖子发了但看不到

Instagram Graph API 是两步流程：
1. `INSTAGRAM_POST_IG_USER_MEDIA` → 创建 container，返回 container_id
2. `INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH` → 真正发布

Agent 有时只做第一步。发现时让 agent 执行第二步即可。

### Twitter 发帖失败，"account_id" 错误

Twitter API 免费 tier 不支持发帖，需要 Basic ($100/月) 或更高。
auth 本身（OAuth redirect）不受影响，只有发帖操作需要付费 tier。

### billing_error: credit balance too low

Anthropic API 余额不足。去 console.anthropic.com → Plans & Billing 充值，
充值后重启 agent（不需要 --force）。

### 重复消息被处理多次 / output 里出现多个相同 user 消息

**根本原因：多个 watch loop 进程同时监听同一个 input.txt。**

`kill <PID>` 只杀 `uv` wrapper 进程，Python 子进程不会跟着退出。
必须用 `pkill -f` 杀掉所有相关进程：

```bash
pkill -f "test_post_agent.py"
# 或
pkill -f "test_scheduling_agent.py"
```

确认干净后再重启：
```bash
ps aux | grep test_post_agent | grep -v grep
```

不要用 `>>` 追加消息，用 `>` 覆盖写入。
Agent 处理完一条消息后会自动清空 input 文件。

### Sessions 是完全隔离的（无跨 session 记忆）

Anthropic managed agent 的每个新 session 都是完全独立的对话，
**不会继承同一 agent_id 下其他 session 的历史**。

如果新 session 里 agent "记得"旧内容，说明有残留的旧进程用旧 session 在回复，
而不是 session 之间共享了记忆。用 `pkill -f` 彻底清掉残留进程即可。

### [overloaded] 错误

Anthropic API 繁忙，agent 会自动等待 20s 后重试，无需手动干预。

---

## 换新 user 测试

修改 `scripts/test_scheduling_agent.py` 顶部的 `USER_ID`：

```python
USER_ID      = "votrix-ai-test-3"   # 改这里
DISPLAY_NAME = "Votrix AI Test 3"
```

然后 `--force` 重新 provision，新 user 会自动连接 API_KEY integrations（Apollo 等），
OAuth integrations（Instagram、Twitter）需要用户重新走 auth 流程。

---

## 关键文件

| 文件 | 作用 |
|------|------|
| `scripts/test_scheduling_agent.py` | 测试主脚本 |
| `scripts/test_input.txt` | 往这里写消息 |
| `scripts/test_output.txt` | agent 回复写在这里 |
| `scripts/.scheduling_agent_cache.json` | 缓存 agent_id/env_id/session_id（gitignored） |
| `agents/scheduling-agent/config.json` | agent 配置（model、integrations、tools） |
| `app/management/provisioning.py` | provision 逻辑，含 API_KEY 自动连接 |
| `app/tools/oauth.py` | manage_connections tool，OAuth redirect 流程 |
| `app/integrations/composio.py` | Composio REST API 封装 |

---

## 重要：模型必须用 Sonnet，不能用 Haiku

**现象**：用 `claude-haiku-4-5-20251001` 时，MCP 工具（如 `INSTAGRAM_POST_IG_USER_MEDIA`）会走 `agent.custom_tool_use` 而非 `agent.mcp_tool_use`，导致 Anthropic 返回 "Permission denied"，帖子发布失败。

**原因**：Haiku 会读 SKILL.md 里提到的工具名，然后把它们当成 custom tool 直接调用（AI 幻觉）。实际上这些工具只存在于 MCP，没有注册为 custom tool，所以调用被拒绝。

**结论**：所有需要调用 Composio MCP 工具的 agent，`config.json` 里的 `model` 必须设置为 `claude-sonnet-4-6`（或更高），不能用 Haiku。
