---
description: >
  飞书任务驱动的自动化开发流程。触发方式：/feishu-dev <task_id>。
  输入飞书任务 ID 或 URL，自动拉取需求、智能补问、生成 Plan、实现代码、
  验证、commit（自动带飞书任务链接）、push。
  当用户说"feishu-dev"、"飞书开发"、"自动开发飞书任务"时使用。
---

# 飞书任务驱动开发

输入飞书任务，自动完成：拉取需求 → 补问 → Plan → 实现 → 验证 → commit → push。

**人工介入只有 2 个点**：补问（~5秒点选）+ Plan 确认（~30秒扫一眼）。其余全自动。

脚本位置：`${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py`（复用已有的飞书 API 层）

---

## Phase 0：项目路径配置（一次性）

在 Phase 1 开始前，检查项目路径是否已配置：

```bash
PYTHONIOENCODING=utf-8 python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" check_project_config
```

**若已配置**（`configured: true`），直接进 Phase 1，从返回的 `frontend_path` / `backend_path` 读取对应 CLAUDE.md。

**若未配置**（`configured: false`），用 AskUserQuestion 询问一次：

```
【项目路径未配置】请提供前后端项目的根目录路径（没有的填 null）：
- 前端项目路径（如 /Users/xxx/work/my-web）
- 后端项目路径（如 /Users/xxx/work/my-api）
```

收到后保存（路径只需配置一次，后续所有任务复用）：

```bash
PYTHONIOENCODING=utf-8 python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" save_project_config "<frontend_path>" "<backend_path>"
```

---

## Phase 1：拉取 + 智能补问

### 1.1 检查凭据

```bash
PYTHONIOENCODING=utf-8 python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" check_config
```

若未配置，引导用户完成首次配置（同 feishu-task skill 的流程）。

### 1.2 提取任务 ID 并拉取

从用户输入中提取 UUID（支持纯 ID、飞书 URL、混合文本），然后拉取：

```bash
PYTHONIOENCODING=utf-8 python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" get_task <task_id>
```

### 1.3 分析任务信息

综合 `summary` + `description` + `comments` 分析需求。

**记录任务上下文**（后续 commit 时使用）：
- `task_id`：飞书任务 GUID
- `task_summary`：任务标题
- `task_link`：`https://applink.feishu.cn/client/todo/detail?guid=<task_id>`

### 1.3.5 加载项目编码规范

根据任务范围，从 Phase 0 获取的路径中读取对应 CLAUDE.md：

| 任务范围 | 读取文件 |
|---|---|
| 仅前端 | `{frontend_path}/CLAUDE.md`（如存在） |
| 仅后端 | `{backend_path}/CLAUDE.md`（如存在） |
| 前后端都涉及 | 两个都读 |

用 Read 工具读取，加载到上下文。Phase 3.2 实现代码时**严格遵循**，不得使用规范外的写法。若文件不存在则跳过。

### 1.3.6 清晰度门槛（开始分析前必须过）

读完任务后，先做一次自我评估，**达到清晰才进入 1.4**，否则先提问。

**可以继续的条件（同时满足）**：
- 知道要改哪个模块/页面（或能通过 1~2 次 grep 确定）
- 知道改什么（增/删/改，有具体描述）
- Bug 类任务：有截图、报错信息或日志中的至少一项

**需要先提问的情况（满足任意一条）**：
- 不知道涉及哪个页面或模块
- 描述过于模糊（如"优化一下"、"看看这个问题"）
- Bug 类任务但没有任何复现证据
- 本次对话中已有截图/日志 → 先分析这些，不要急着 grep 代码

提问要一次说完，不要分多轮：
```
我需要几个信息才能开始：
1. 这个问题出现在哪个页面？
2. 有截图或报错信息吗？
3. ...
```

### 1.4 判断是否需要补问

**不需要补问**（直接进 Phase 2）：
- 描述明确提到了代码目录名或文件名
- 用任务关键词 grep 代码库，只命中一个页面/模块
- 描述足够具体，能确定文件和操作

**需要补问**（用 AskUserQuestion）：
- 关键词 grep 命中多个候选文件，读取后仍无法区分
- 看不出要改前端还是后端
- 操作描述模糊（如"优化体验"、"提高稳定性"没有具体方案）
- 缺少关键参数（如"迁移到哪个新地址"）

### 1.5 补问策略

用 AskUserQuestion 生成选项。选项动态生成，来自：
1. 用任务关键词 grep 代码库，找到的候选文件
2. 读取候选文件前 30 行，判断页面/模块功能
3. 根据任务描述中的操作类型推断范围（删列→前端、新增接口→后端）

示例：

```
任务: "广告创意列表删除状态列"

→ grep "广告创意" + "ad_state" 找到 2 个候选文件
→ 补问：

【页面】你说的"广告创意"是指？
  ○ 创建广告/广告创意 (create-ads/index.vue) — 有 ad_state 列
  ○ 素材库 (asserts/index.vue) — 素材管理
  ○ 其他

【范围】需要改哪端？
  ○ 仅前端 (Recommended) — 删列/删过滤是典型前端操作
  ○ 仅后端
  ○ 前后端都要
```

---

## Phase 2：Plan（用户确认）

在写代码之前，输出一份简洁的实现计划，让用户 30 秒内扫完确认。

### Plan 格式

```
━━━ 实现计划 ━━━

任务: <任务标题>
链接: https://applink.feishu.cn/client/todo/detail?guid=<task_id>
页面: <目标文件路径>
范围: 仅前端 / 仅后端 / 前后端

要改:
  ✂ <具体改动点1>
  ✂ <具体改动点2>
  ...

不动:
  ✗ <明确不改的相邻功能1>
  ✗ <明确不改的相邻功能2>
  ...

确认后自动执行 →
━━━━━━━━━━━━━━
```

### Plan 生成策略

1. 从 Phase 1 确定的页面和范围出发
2. 读取目标文件，grep 具体要改的代码块
3. **数据类 bug 强制全链路排查**（在写 Plan 之前必须完成）：
   - 触发条件：描述含"数据不对/数据错误/显示了不该有的/总数对不上/没有过滤/没有筛选/数据不准"
   - 必须检查：① 前端传了什么参数 → ② 后端对应接口的 where/filter 条件 → ③ 两端都有问题则都列入 Plan
   - **找到前端 bug 不能停**，必须继续读后端接口代码，确认后端无误后才能收口
   - 范围字段写"前后端"，除非明确确认后端无问题
4. 列出所有要改的点（具体到功能粒度）
5. **主动列出不改什么**（防止误改相邻功能）
6. 等用户确认或修正

### "不动"列表的价值

主动列出不改什么，因为：
- 用户最怕"多改了不该改的"
- "不动"列表让用户一眼确认影响范围
- 如果"不动"里有用户想改的，立刻能发现

---

## Phase 3：全自动执行

用户确认 Plan 后，以下全部自动完成，不再有任何交互。

### 3.1 创建分支

```
规则：
  当前在 master/main → 自动创建 feat/feishu-{uuid前8位}
  当前在 dev 分支     → 自动创建 feat/feishu-{uuid前8位}
  当前在 feature 分支 → 直接在当前分支开发
  分支已存在          → 自动切换到已有分支
  
  如果当前在 master 且忘了建分支 → 自动补建后再继续
```

### 3.2 实现代码

按 Plan 中列出的每一项逐个修改。遵循：
- **Phase 1.3.5 已加载的项目 CLAUDE.md 编码规范**（写法、工具库、返回格式等严格按规范）
- **先找相似功能，再仿写**：grep 项目中已有的相似实现，用同样的模式
- 只改 Plan 中列出的，不多改任何东西

### 3.3 验证

```
自动检测项目类型并运行验证：

  有 package.json → npm run build:test（前端构建验证）
  有 pyproject.toml → python -m py_compile <changed_files>（后端语法检查）

  验证失败 → 读取错误 → 自动修复 → 重新验证
  最多重试 3 轮
  3 轮后仍失败 → 暂停，报告错误让人介入
```

### 3.4 代码 Review（commit 前）

实现完成后，重新读一遍改动的代码，从以下两个维度检查：

**范围检查**
- 只改了 Plan 中列出的文件，没有计划外的改动
- 没有误改相邻功能（对照 Plan 的"不动"列表）
- 没有遗留 console.log / print / TODO / debugger

**质量检查**
- 有没有更简洁/符合项目现有写法的实现方式
- 有没有潜在 bug：边界值、空值、异步竞态、类型问题等
- 有没有漏掉的场景（如只处理了成功没处理失败，只考虑了有数据没考虑空列表）

发现问题 → 直接修掉，不用问用户。
改动较大 → 在收尾报告里说明 review 发现了什么、改了什么。

### 3.5 Commit

**开始前记录 `git status` 快照**，完成后对比，只 add 新增/修改的文件。

绝不使用 `git add -A` 或 `git add .`。自动过滤：`.env`、`node_modules/`、`__pycache__/`、`*.log`。

Commit message 格式：

```
<type>: <根据实际 diff 写的简短描述，一句话>

Feishu-Task: https://applink.feishu.cn/client/todo/detail?guid=<task_id>
Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

- 首行根据 **实际 diff** 写，不照抄任务标题，精准反映改了什么
- 不加正文说明段落，保持简洁
- Type 自动判断：任务含"新增/增加/添加" → `feat:`，含"修复/bug/报错" → `fix:`，含"删除/重构" → `refactor:`，含"优化" → `perf:`，兜底 → `feat:`
- **Feishu-Task trailer 自动注入**，用户不需要手动写

### 3.6 Push

```bash
git push origin <当前分支名>
```

绝不 push 到 master/main/dev。

---

## Phase 4：收尾报告

### 4.1 标记飞书任务完成

push 成功后，自动执行：

```bash
PYTHONIOENCODING=utf-8 python3 "${CLAUDE_PLUGIN_ROOT}/skills/feishu-task/feishu_api.py" complete_task <task_id>
```

失败时不中断流程，在报告里标注 ❌ 并说明原因即可。

### 4.2 输出报告

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ 飞书任务已完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

任务: <任务标题>
链接: <飞书任务链接>

做了什么:
  <一句话概述实际变更>

改了:
  <文件路径>  (+N -M)
  ...

验证: <验证命令> ✅

Commit: <hash> <commit message 首行>
Branch: <分支名>
Pushed: ✅ / ❌ <原因>
飞书已完成: ✅ / ❌ <原因>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 异常处理

| 异常 | 自动处理 | 暂停问人 |
|------|----------|---------|
| 凭据未配置 | — | 引导配置 |
| 任务拉取失败 | 重试 1 次 | 仍失败则报错 |
| 描述有歧义 | AskUser 补问 | — |
| Plan 不对 | — | 用户修正 |
| grep 找不到目标 | 扩大搜索范围 | 确实找不到则问人 |
| build/compile 失败 | 自动修复，最多 3 轮 | 3 轮后仍失败 |
| push 失败 | — | 报错 |
