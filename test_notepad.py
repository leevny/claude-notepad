"""smoke test: python test_notepad.py"""
import json
import os
import tempfile
import time
from pathlib import Path

from notepad import list_files, page_sessions, yesterday_files

FAIL = []


def check(name, cond):
    if not cond:
        FAIL.append(name)
    print(("PASS" if cond else "FAIL"), name)


def write(p: Path, lines, mtime=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in lines), encoding="utf-8")
    if mtime:
        os.utime(p, (mtime, mtime))


with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    write(
        root / "proj-a" / "aaaa.jsonl",
        [
            {"type": "mode", "sessionId": "aaaa"},
            {"type": "user", "message": {"content": "帮我改登录页"}, "cwd": "D:\\work\\proj-a"},
            {"type": "ai-title", "aiTitle": "修复登录页bug", "sessionId": "aaaa"},
        ],
        mtime=1000,
    )
    write(
        root / "proj-b" / "bbbb.jsonl",
        [{"type": "user", "message": {"content": "写个爬虫吧"}, "cwd": "D:\\work\\proj-b"}],
        mtime=2000,  # 更新，应排在前面
    )
    write(root / "proj-b" / "cccc.jsonl" / "subagents" / "x.jsonl", [{"cwd": "X"}], mtime=3000)
    write(root / "proj-c" / "dddd.jsonl", [{"type": "mode"}], mtime=1500)
    write(  # 昨天的会话
        root / "proj-d" / "eeee.jsonl",
        [{"type": "user", "message": {"content": "昨天的活"}, "cwd": "D:\\work\\proj-d"}],
        mtime=time.time() - 86400,
    )

    files = list_files(root=root)
    stems = [f.stem for f in files]
    check("排除 subagents 深层文件", "x" not in stems)
    check("按 mtime 倒序", stems[:2] == ["cccc", "eeee"])  # cccc 是同名目录，解析时跳过

    rows, nxt = page_sessions(files, 0, 10)
    check("解析失败的文件跳过", [s["id"] for s in rows] == ["eeee", "bbbb", "dddd", "aaaa"])
    check("空会话返回占位 None（GUI 层做 i18n）", next(s for s in rows if s["id"] == "dddd")["title"] is None)
    check("翻页游标指向文件末尾", nxt == len(files))
    check("取 aiTitle", next(s for s in rows if s["id"] == "aaaa")["title"] == "修复登录页bug")
    check("无 aiTitle 回退首条用户消息", next(s for s in rows if s["id"] == "bbbb")["title"] == "写个爬虫吧")
    check("cwd 提取", next(s for s in rows if s["id"] == "bbbb")["cwd"] == "D:\\work\\proj-b")

    rows1, nxt1 = page_sessions(files, 0, 1)
    check("分页每页条数生效", len(rows1) == 1 and nxt1 == 2)
    rows2, _ = page_sessions(files, nxt1, 1)
    check("翻页续接（解析失败的文件不占行）", rows2[0]["id"] == "bbbb")

    ystems = {f.stem for f in yesterday_files(files)}
    check("恢复昨日只含昨天的会话", ystems == {"eeee"})

print("OK" if not FAIL else f"{len(FAIL)} FAILED")
raise SystemExit(1 if FAIL else 0)
