---
description: >
  处理飞书任务（Feishu/Lark task）。触发关键词：
  飞书任务、feishu task、lark task、完成飞书、处理任务、实现任务。
  当用户提及飞书任务 ID（UUID 格式，如 6940dcc0-63f6-446c-a601-ec912923f243）或飞书任务 URL 时自动激活。
---

# 飞书任务处理 Skill

帮助用户拉取飞书任务详情，并在代码库中实现或修复对应需求。

脚本位置：`${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py`（Python 3 stdlib，零依赖）

## 工作流

### 第一步：检查凭据配置

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" check_config
```

**若返回 `configured: false`**，引导用户完成首次配置：

```
需要先配置飞书应用凭据，只需配置一次。请按以下步骤操作：

1. 前往 https://open.feishu.cn/ → 开发者后台 → 创建自建应用
2. 进入「权限管理」，申请以下权限：
   - task:attachment:read
   - task:comment:write
   - task:task:read
   - task:task:readonly
   - task:task:writeonly
   - task:tasklist:write
   - task:tasklist:write
3. 发布应用版本（需企业管理员审批）
4. 在「凭证与基础信息」页面获取 App ID 和 App Secret

请提供你的 App ID 和 App Secret：
```

收到凭据后执行：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" save_config <app_id> <app_secret>
```

### 第二步：提取任务 ID

从用户输入中提取任务 ID（UUID 格式或完整飞书 URL，脚本会自动解析）。

### 第三步：获取任务详情

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" get_task <task_id>
```

向用户展示：任务标题（summary）、描述（description）、截止日期（due）、状态（status）。

### 第四步：分析并实现

探索代码库，理解现有结构后：
1. 向用户说明实现方案
2. 实现代码变更
3. 运行相关测试（如有）

### 第五步：添加任务评论

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" add_comment <task_id> "[Claude Code] 已完成实现

变更内容：
- {简要描述改动}

涉及文件：
- {修改的文件路径}"
```

### 第六步：询问是否关闭任务

询问用户：「任务已实现完成，是否将飞书任务标记为已完成？」

若用户确认：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" complete_task <task_id>
```

## 其他触发场景

**列出待办任务：**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" list_tasks
```

**列出已完成任务：**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" list_tasks --completed
```

**直接关闭任务：**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" complete_task <task_id>
```