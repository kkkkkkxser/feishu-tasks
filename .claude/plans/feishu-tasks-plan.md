# 飞书任务 Claude Code 插件

## Context

用户希望在 Claude Code 对话中说「帮我完成飞书任务 ot-xxx」，Claude Code 自动拉取飞书任务详情并在代码库中实现/修复，最终发布为可供他人安装使用的 Claude Code 插件。

---

## 目标产物

一个独立的 GitHub 仓库 `claude-feishu-tasks`，可通过 Claude Code 插件机制安装。

---

## 插件结构（参考 claude-mem 插件的真实结构）

```
claude-feishu-tasks/
├── package.json              # 插件元数据（name, version, keywords, author）
├── .mcp.json                 # MCP Server 配置，声明工具入口和环境变量
├── scripts/
│   └── feishu-mcp-server.cjs # MCP Server 实现（Node.js CommonJS）
├── skills/
│   └── feishu-task.md        # Skill 文件，关键词匹配自动触发
└── README.md
```

---

## 关键文件内容

### `package.json`
```json
{
  "name": "claude-feishu-tasks",
  "version": "1.0.0",
  "description": "Claude Code plugin: fetch Feishu tasks and implement them in your codebase",
  "keywords": ["feishu", "lark", "task", "claude-code-plugin"],
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0"
  }
}
```

### `.mcp.json`（格式参考 claude-mem 实测结构）
```json
{
  "mcpServers": {
    "feishu-tasks": {
      "type": "stdio",
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/feishu-mcp-server.cjs"],
      "env": {
        "FEISHU_APP_ID": "${FEISHU_APP_ID}",
        "FEISHU_APP_SECRET": "${FEISHU_APP_SECRET}"
      }
    }
  }
}
```

### MCP Server 暴露的工具（`scripts/feishu-mcp-server.cjs`）

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `get_task` | `task_id: string` | 获取任务标题、描述、截止日期、负责人 |
| `list_my_tasks` | `completed?: bool, page_size?: number` | 列出待办任务 |
| `complete_task` | `task_id: string` | 标记任务已完成 |
| `add_task_comment` | `task_id, comment` | 添加实现摘要评论 |
| `save_config` | `app_id: string, app_secret: string` | 保存凭据到插件目录 |
| `check_config` | 无 | 检查凭据是否已配置 |

凭据读取顺序：先读取 `${CLAUDE_PLUGIN_ROOT}/feishu-config.json`，不存在则返回「需要配置」状态。
token 用 tenant_access_token（自动缓存 + 刷新）。
task_id 支持 `ot-xxx` 格式和完整飞书任务 URL 两种输入。

飞书 API 端点：
- Token: `POST /open-apis/auth/v3/tenant_access_token/internal`
- 获取任务: `GET /open-apis/task/v2/tasks/{task_guid}`
- 列出任务: `GET /open-apis/task/v2/tasks`
- 更新任务: `PATCH /open-apis/task/v2/tasks/{task_guid}`
- 添加评论: `POST /open-apis/task/v2/tasks/{task_guid}/comments`

### `skills/feishu-task.md`（自动触发 Skill）

description 关键词覆盖：「飞书任务」「feishu task」「lark task」「ot-」前缀等。

工作流步骤：
1. 从用户输入提取 task_id
2. 调用 `get_task` 获取完整任务详情
3. 探索代码库，向用户说明实现方案
4. 实现代码
5. 调用 `add_task_comment` 记录变更摘要
6. 询问用户是否调用 `complete_task` 关闭任务

---

## 首次使用引导流程（核心 UX）

无需环境变量，凭据保存在插件目录下的 `feishu-config.json`。

### 首次触发时的交互流程

```
用户：帮我完成飞书任务 ot-abc123
                    │
                    ▼
         Skill 激活 → 调用 check_config
                    │
           返回「未配置」
                    │
                    ▼
  Claude 引导用户：

  "需要先配置飞书应用凭据，只需一次。请按以下步骤操作：

  1. 前往 https://open.feishu.cn/ → 开发者后台 → 创建自建应用
  2. 进入「权限管理」，申请以下权限：
     - task:task:read（读取任务）
     - task:task:write（更新任务状态）
     - task:task_comment:write（添加评论）
  3. 发布应用版本（需企业管理员审批）
  4. 在「凭证与基础信息」页面获取 App ID 和 App Secret

  请提供你的 App ID 和 App Secret："
                    │
              用户提供凭据
                    │
                    ▼
         调用 save_config(app_id, app_secret)
         → 写入 ${CLAUDE_PLUGIN_ROOT}/feishu-config.json
                    │
                    ▼
         继续执行：调用 get_task(task_id)
```

### 凭据文件格式
```json
// ${CLAUDE_PLUGIN_ROOT}/feishu-config.json（不提交 git）
{
  "app_id": "cli_xxxxxxxxxxxxxxxx",
  "app_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

### 安装流程（无需手动配置任何环境变量）
```bash
/plugins install github.com/{你的GitHub用户名}/claude-feishu-tasks
# 安装后直接使用，首次使用时插件自动引导配置
```

---

## 现有参考资料

- 项目中的 `feishu.py`：已有 token 获取和缓存逻辑可作为 JS 版参考
- `~/.claude/plugins/cache/thedotmack/claude-mem/` ：实际插件结构参考

---

## 实现步骤

1. 创建新 GitHub 仓库 `claude-feishu-tasks`
2. 编写 `scripts/feishu-mcp-server.cjs`（飞书 API 客户端 + 4 个 MCP 工具）
3. 编写 `skills/feishu-task.md`（触发关键词 + 工作流指令）
4. 编写 `package.json` 和 `.mcp.json`
5. 编写 README（安装步骤、权限配置）
6. 本地测试：在 ads 项目中配置 `.mcp.json` 验证 token 获取和任务拉取
7. 提交发布到 GitHub

## 验证方式

1. 安装插件后重启 Claude Code
2. 说「帮我完成飞书任务 ot-xxx」，观察是否自动调用 `get_task` 工具
3. 确认返回任务标题和描述格式正确
4. 实现后确认 `add_task_comment` 能成功写入飞书
5. 确认 `complete_task` 能正确修改任务状态
