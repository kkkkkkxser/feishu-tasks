#!/usr/bin/env python3
"""
Feishu Task API helper — stdlib only, zero external dependencies.

Usage:
  python3 feishu_api.py check_config
  python3 feishu_api.py save_config <app_id> <app_secret>
  python3 feishu_api.py get_task <task_id>
  python3 feishu_api.py list_tasks [--completed] [--page_size N]
  python3 feishu_api.py complete_task <task_id>
  python3 feishu_api.py add_comment <task_id> <comment>

Output: JSON to stdout. Errors exit with code 1.
"""

import sys
import os
import json
import time
import re
import urllib.request
import urllib.error
import pathlib

FEISHU_BASE = "https://open.feishu.cn"
PLUGIN_ROOT = pathlib.Path(
    os.environ.get("CLAUDE_PLUGIN_ROOT", pathlib.Path(__file__).parent.parent)
)
# 配置存在 Claude Code 插件缓存目录，与插件文件分离，更新插件不会丢失凭据
USER_CONFIG_DIR = pathlib.Path.home() / ".claude" / "plugins" / "cache" / "coder-xiaotian" / "feishu-tasks"
CONFIG_FILE = USER_CONFIG_DIR / "config.json"
TOKEN_CACHE_FILE = USER_CONFIG_DIR / ".token_cache.json"

UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I
)


# ── HTTP helper ───────────────────────────────────────────────────────────────

def http(method: str, path: str, token: str = None, body: dict = None) -> dict:
    url = FEISHU_BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


# ── Config ────────────────────────────────────────────────────────────────────

def read_config() -> dict | None:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return None


def save_config(app_id: str, app_secret: str) -> dict:
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({"app_id": app_id, "app_secret": app_secret}, indent=2))
    TOKEN_CACHE_FILE.unlink(missing_ok=True)  # clear stale token
    return {"success": True, "message": f"凭据已保存到 {CONFIG_FILE}"}


def check_config() -> dict:
    cfg = read_config()
    if not cfg or not cfg.get("app_id") or not cfg.get("app_secret"):
        return {
            "configured": False,
            "message": (
                "飞书凭据未配置。请按以下步骤操作：\n\n"
                "1. 前往 https://open.feishu.cn/ → 开发者后台 → 创建自建应用\n"
                "2. 进入「权限管理」，申请权限：\n"
                "   - task:task:read\n"
                "   - task:task:write\n"
                "   - task:task_comment:write\n"
                "3. 发布应用版本（需企业管理员审批）\n"
                "4. 在「凭证与基础信息」获取 App ID 和 App Secret\n\n"
                "获取后运行：python3 feishu_api.py save_config <app_id> <app_secret>"
            ),
        }
    return {"configured": True, "app_id": cfg["app_id"]}


# ── Token (file-cached) ───────────────────────────────────────────────────────

def get_token() -> str:
    # Check file cache
    if TOKEN_CACHE_FILE.exists():
        cache = json.loads(TOKEN_CACHE_FILE.read_text())
        if time.time() < cache.get("expires_at", 0):
            return cache["token"]

    cfg = read_config()
    if not cfg:
        raise RuntimeError("凭据未配置，请先运行 check_config")

    result = http("POST", "/open-apis/auth/v3/tenant_access_token/internal", body={
        "app_id": cfg["app_id"],
        "app_secret": cfg["app_secret"],
    })
    if result.get("code") != 0:
        raise RuntimeError(f"获取 token 失败（code={result.get('code')}）：{result.get('msg')}")

    token = result["tenant_access_token"]
    expires_at = time.time() + result.get("expire", 7200) - 60  # refresh 60s early

    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE_FILE.write_text(json.dumps({"token": token, "expires_at": expires_at}))
    return token


# ── Task ID parser ────────────────────────────────────────────────────────────

def parse_task_id(raw: str) -> str:
    m = UUID_RE.search(raw)
    if m:
        return m.group(0)
    return raw.strip()


# ── API operations ────────────────────────────────────────────────────────────

def get_task_comments(tid: str, token: str) -> list:
    result = http("GET", f"/open-apis/task/v2/comments?resource_type=task&resource_id={tid}&page_size=100", token=token)
    if result.get("code") != 0:
        return []
    items = result.get("data", {}).get("items", [])
    return [
        {
            "id": c["id"],
            "content": c.get("content", ""),
            "created_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(int(c["created_at"]) // 1000)) if c.get("created_at") else None,
        }
        for c in items
    ]


def get_task(task_id: str) -> dict:
    tid = parse_task_id(task_id)
    token = get_token()
    result = http("GET", f"/open-apis/task/v2/tasks/{tid}?user_id_type=user_id", token=token)
    if result.get("code") != 0:
        raise RuntimeError(f"获取任务失败（code={result.get('code')}）：{result.get('msg')}")

    t = result["data"]["task"]
    due_ts = t.get("due", {}).get("timestamp")
    return {
        "id": t["guid"],
        "summary": t["summary"],
        "description": t.get("description", ""),
        "status": t.get("status", "todo"),  # "todo" = 未完成, "done" = 已完成
        "due": time.strftime("%Y-%m-%d %H:%M", time.localtime(int(due_ts))) if due_ts else None,
        "members": [{"id": m["id"], "role": m.get("role")} for m in t.get("members", [])],
        "comments": get_task_comments(tid, token),
    }


def list_tasks(completed: bool = False, page_size: int = 20) -> dict:
    token = get_token()
    params = f"page_size={min(page_size, 100)}&completed={str(completed).lower()}&user_id_type=user_id"
    result = http("GET", f"/open-apis/task/v2/tasks?{params}", token=token)
    if result.get("code") != 0:
        raise RuntimeError(f"列出任务失败（code={result.get('code')}）：{result.get('msg')}")

    items = result["data"].get("items", [])
    return {
        "tasks": [
            {
                "id": t["guid"],
                "summary": t["summary"],
                "status": t.get("status", "todo"),  # "todo" = 未完成, "done" = 已完成
                "due": (
                    time.strftime("%Y-%m-%d", time.localtime(int(t["due"]["timestamp"])))
                    if t.get("due") else None
                ),
            }
            for t in items
        ],
        "has_more": result["data"].get("has_more", False),
    }


def complete_task(task_id: str) -> dict:
    tid = parse_task_id(task_id)
    token = get_token()
    result = http(
        "PATCH",
        f"/open-apis/task/v2/tasks/{tid}?user_id_type=user_id",
        token=token,
        body={"task": {"completed_at": str(int(time.time() * 1000))}, "update_fields": ["completed_at"]},
    )
    if result.get("code") != 0:
        raise RuntimeError(f"完成任务失败（code={result.get('code')}）：{result.get('msg')}")
    return {"success": True, "message": f"任务 {tid} 已标记为完成"}


def add_comment(task_id: str, comment: str) -> dict:
    tid = parse_task_id(task_id)
    token = get_token()
    result = http(
        "POST",
        "/open-apis/task/v2/comments",
        token=token,
        body={"resource_type": "task", "resource_id": tid, "content": comment},
    )
    if result.get("code") != 0:
        raise RuntimeError(f"添加评论失败（code={result.get('code')}）：{result.get('msg')}")
    return {"success": True, "comment_id": result["data"]["comment"]["id"]}


# ── CLI entry ─────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]
    try:
        if cmd == "check_config":
            out = check_config()
        elif cmd == "save_config":
            out = save_config(args[1], args[2])
        elif cmd == "get_task":
            out = get_task(args[1])
        elif cmd == "list_tasks":
            completed = "--completed" in args
            page_size = 20
            if "--page_size" in args:
                page_size = int(args[args.index("--page_size") + 1])
            out = list_tasks(completed, page_size)
        elif cmd == "complete_task":
            out = complete_task(args[1])
        elif cmd == "add_comment":
            # comment may contain spaces, join remaining args
            out = add_comment(args[1], " ".join(args[2:]))
        else:
            raise RuntimeError(f"未知命令：{cmd}")

        print(json.dumps(out, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()