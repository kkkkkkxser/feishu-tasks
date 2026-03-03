# claude-feishu-tasks

Claude Code 插件：在对话中直接拉取飞书（Lark）任务并在代码库中实现。

**零依赖**：仅需系统自带的 Python 3，无需 `npm install` 或任何第三方库。

## 功能

- 说「帮我完成飞书任务 6940dcc0-63f6-446c-a601-ec912923f243」，Claude 自动获取任务详情并实现需求
- 首次使用时自动引导配置飞书凭据
- 实现完成后自动添加评论并可标记任务完成

## 安装

```bash
/plugins install github.com/{你的GitHub用户名}/claude-feishu-tasks
```

安装后重启 Claude Code，首次使用时会自动引导配置飞书凭据。

## 前置条件

- Python 3（macOS / Linux 系统自带）
- 飞书自建应用（见下方配置步骤）

## 飞书应用权限配置

在[飞书开发者后台](https://open.feishu.cn/)创建自建应用，申请以下权限并发布版本（需企业管理员审批）：

| 权限 | 说明 |
|------|------|
| `task:task:read` | 读取任务详情 |
| `task:task:write` | 更新任务状态（完成） |
| `task:task_comment:write` | 添加任务评论 |

凭据首次配置后保存在 `{插件目录}/feishu-config.json`，后续无需重新配置。

## 使用示例

```
# 实现指定任务（UUID 格式）
帮我完成飞书任务 6940dcc0-63f6-446c-a601-ec912923f243

# 完整 URL 也支持
处理这个飞书任务：https://applink.feishu.cn/client/todo/detail?guid=6940dcc0-63f6-446c-a601-ec912923f243

# 列出待办任务
列出我的飞书任务

# 直接关闭任务
关闭飞书任务 6940dcc0-63f6-446c-a601-ec912923f243
```

## 脚本直接使用

```bash
CLAUDE_PLUGIN_ROOT=/path/to/plugin

# 检查凭据
python3 skills/feishu-task/feishu_api.py check_config

# 保存凭据
python3 skills/feishu-task/feishu_api.py save_config cli_xxx your_secret

# 获取任务
python3 skills/feishu-task/feishu_api.py get_task 6940dcc0-63f6-446c-a601-ec912923f243

# 列出任务
python3 skills/feishu-task/feishu_api.py list_tasks
python3 skills/feishu-task/feishu_api.py list_tasks --completed

# 完成任务
python3 skills/feishu-task/feishu_api.py complete_task 6940dcc0-63f6-446c-a601-ec912923f243

# 添加评论
python3 skills/feishu-task/feishu_api.py add_comment 6940dcc0-63f6-446c-a601-ec912923f243 "实现完成"
```