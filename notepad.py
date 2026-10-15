"""claude-notepad: 外挂式 Claude Code 会话记录本，不接管终端、零侵入。

数据源就是 Claude Code 自己的会话记录 ~/.claude/projects/*/*.jsonl，
不装 hook、不改变任何操作习惯。运行: python notepad.py
打包: pyinstaller --onefile --noconsole --name claude-notepad notepad.py
界面语言跟随系统，可用环境变量 CLAUDE_NOTEPAD_LANG=zh|en 覆盖。
"""
import ctypes
import json
import os
import shutil
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import Tk, ttk

PROJECTS = Path.home() / ".claude" / "projects"
PAGE = 10

STR = {
    "zh": {
        "refresh": "刷新",
        "restore_sel": "恢复选中",
        "restore_yesterday": "恢复昨日",
        "pick": "选",
        "col_time": "最后活跃",
        "col_project": "项目目录",
        "col_title": "在干什么",
        "page": "第 {} 页",
        "prev": "‹ 上一页",
        "next": "下一页 ›",
        "started": "已启动 {} 个窗口",
        "skipped": "，跳过 {} 个（项目目录已不存在）",
        "no_yesterday": "昨天没有会话记录",
        "untitled": "（无标题）",
        "unknown_dir": "（未知目录）",
    },
    "en": {
        "refresh": "Refresh",
        "restore_sel": "Restore selected",
        "restore_yesterday": "Restore yesterday",
        "pick": "Sel",
        "col_time": "Last active",
        "col_project": "Project dir",
        "col_title": "What it was doing",
        "page": "Page {}",
        "prev": "‹ Prev",
        "next": "Next ›",
        "started": "Launched {} windows",
        "skipped": ", skipped {} (project dir missing)",
        "no_yesterday": "No sessions recorded yesterday",
        "untitled": "(untitled)",
        "unknown_dir": "(unknown dir)",
    },
}


def detect_lang():
    v = os.environ.get("CLAUDE_NOTEPAD_LANG")
    if v:
        return v if v in ("zh", "en") else "zh"
    try:
        lang = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFFFF
        return "zh" if lang in (0x0004, 0x0804) else "en"  # zh-Hans 通用 / zh-CN
    except Exception:
        return "en"


def parse_session(path: Path):
    """从会话 jsonl 提取 cwd 和标题。标题优先 aiTitle，回退首条用户消息。"""
    cwd = title = first = None
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                # 子串预过滤，省掉对无关行的 json 解析
                if '"cwd"' not in line and '"ai-title"' not in line and '"type":"user"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue  # 正在写入的会话可能有半行
                if cwd is None and o.get("cwd"):
                    cwd = o["cwd"]
                if o.get("type") == "ai-title" and o.get("aiTitle"):
                    title = o["aiTitle"]
                if first is None and o.get("type") == "user" and not o.get("isMeta"):
                    c = o.get("message", {}).get("content")
                    if isinstance(c, str) and c.strip():
                        first = c.strip()
                if cwd and title:
                    break
    except OSError:
        return None
    return {
        "id": path.stem,
        "cwd": cwd,
        "title": title or (first[:60] if first else None),
        "mtime": path.stat().st_mtime,
        "path": path,
    }


def list_files(root=PROJECTS):
    """全部会话文件按最后活跃时间倒序。只扫一层，天然排除 subagents/。"""
    files = list(root.glob("*/*.jsonl"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def page_sessions(files, start, size):
    """解析 files[start:] 直到凑满一页，返回 (会话列表, 下一页起点)。"""
    out = []
    for i, f in enumerate(files[start:], start):
        s = parse_session(f)
        if s:
            out.append(s)
            if len(out) == size:
                return out, i + 1
    return out, len(files)


def yesterday_files(files):
    y = date.today() - timedelta(days=1)
    return [f for f in files if date.fromtimestamp(f.stat().st_mtime) == y]


def restore(sessions):
    """每个会话开一个新终端窗口 claude --resume。返回成功数。"""
    ok = 0
    for s in sessions:
        cwd = s["cwd"]
        if not cwd or not Path(cwd).is_dir():
            continue
        if shutil.which("wt"):  # Windows Terminal
            subprocess.Popen(["wt", "-d", cwd, "cmd", "/k", "claude --resume " + s["id"]])
        else:  # ponytail: 回退传统 cmd 窗口，够用
            subprocess.Popen(
                f'start "" cmd /k claude --resume "{s["id"]}"', shell=True, cwd=cwd
            )
        ok += 1
    return ok


def main():
    T = STR[detect_lang()]
    app = Tk()
    app.title("claude-notepad")

    top = ttk.Frame(app)
    top.pack(fill="x", padx=8, pady=6)
    ttk.Button(top, text=T["refresh"], command=lambda: refresh()).pack(side="left")
    ttk.Button(top, text=T["restore_sel"], command=lambda: restore_selected()).pack(side="right")
    ttk.Button(top, text=T["restore_yesterday"], command=lambda: restore_yesterday()).pack(
        side="right", padx=4
    )

    cols = ("pick", "time", "project", "title")
    tree = ttk.Treeview(app, columns=cols, show="headings", height=10)  # 恰好 10 行
    for c, w, a, k in (
        ("pick", 44, "center", "pick"),
        ("time", 110, "w", "col_time"),
        ("project", 320, "w", "col_project"),
        ("title", 460, "w", "col_title"),
    ):
        tree.heading(c, text=T[k])
        tree.column(c, width=w, anchor=a)
    tree.pack(fill="x", padx=8)  # 高度锁死 10 行，不随窗口拉伸

    bottom = ttk.Frame(app)
    bottom.pack(fill="x", padx=8, pady=4)
    prev_btn = ttk.Button(bottom, text=T["prev"], command=lambda: flip(-1))
    prev_btn.pack(side="left")
    page_lbl = ttk.Label(bottom)
    page_lbl.pack(side="left", padx=12)
    next_btn = ttk.Button(bottom, text=T["next"], command=lambda: flip(1))
    next_btn.pack(side="left")
    status = ttk.Label(bottom, anchor="e")
    status.pack(side="right", fill="x", expand=True)

    state = {"files": [], "page": 0, "picked": set(), "id2path": {}}

    def refresh():
        state["files"] = list_files()
        state["page"] = 0
        state["picked"].clear()
        draw()

    def draw():
        rows, nxt = page_sessions(state["files"], state["page"] * PAGE, PAGE)
        for s in rows:
            state["id2path"][s["id"]] = s["path"]
        tree.delete(*tree.get_children())
        for s in rows:
            t = datetime.fromtimestamp(s["mtime"]).strftime("%m-%d %H:%M")
            box = "☑" if s["id"] in state["picked"] else "☐"
            tree.insert(
                "", "end", iid=s["id"],
                values=(box, t, s["cwd"] or T["unknown_dir"], s["title"] or T["untitled"]),
            )
        page_lbl.config(text=T["page"].format(state["page"] + 1))
        prev_btn.state(["!disabled"] if state["page"] else ["disabled"])
        next_btn.state(["!disabled"] if nxt < len(state["files"]) else ["disabled"])

    def flip(d):
        state["page"] += d
        draw()

    def on_click(e):
        # 点第一列的 ☐/☑ 切换勾选
        if tree.identify_column(e.x) == "#1" and tree.identify_row(e.y):
            iid = tree.identify_row(e.y)
            if tree.set(iid, "pick") == "☑":
                state["picked"].discard(iid)
                tree.set(iid, "pick", "☐")
            else:
                state["picked"].add(iid)
                tree.set(iid, "pick", "☑")

    tree.bind("<Button-1>", on_click)
    tree.bind("<Double-1>", lambda e: restore_one(tree.identify_row(e.y)))

    def restore_one(iid):
        if iid and iid in state["id2path"]:
            s = parse_session(state["id2path"][iid])
            if s:
                do_restore([s])

    def restore_selected():
        ss = [parse_session(state["id2path"][i]) for i in state["picked"] if i in state["id2path"]]
        do_restore([s for s in ss if s])

    def restore_yesterday():
        ss = [s for s in (parse_session(f) for f in yesterday_files(state["files"])) if s]
        if not ss:
            status.config(text=T["no_yesterday"])
            return
        do_restore(ss)

    def do_restore(ss):
        valid = [s for s in ss if s["cwd"] and Path(s["cwd"]).is_dir()]
        n = restore(valid)
        msg = T["started"].format(n)
        if len(valid) < len(ss):
            msg += T["skipped"].format(len(ss) - len(valid))
        status.config(text=msg)

    refresh()
    app.mainloop()


if __name__ == "__main__":
    main()
