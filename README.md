# claude-notepad

> 外挂式的 Claude Code 会话记录本：不接管终端、不改变任何操作习惯，只是把你每天开过的窗口记下来，第二天一键恢复。

[English](README_EN.md) | 简体中文

## 为什么做这个

每天在不同目录开十几个 Claude Code 窗口，下班关机，第二天全忘了开过哪些、各自在干嘛。

已有的方案（如 [claude-squad](https://github.com/smtg-ai/claude-squad)）是 TUI 管理器，要接管你的会话和终端。claude-notepad 反过来——**完全不接管**：

- **零侵入**：直接读取 Claude Code 自己落盘的会话记录（`~/.claude/projects/`），不装 hook、不改配置、不注入任何东西
- **零学习成本**：Claude Code 照常用，恢复用的也是原生 `claude --resume`，习惯完全不变
- **就是个记事本**：一个小窗口列出最近会话，勾选恢复，关掉即走

## 功能

- 列出最近的 Claude Code 会话：时间 / 项目目录 / 在干什么（取自 Claude Code 自动生成的会话标题）
- 分页浏览（每页 10 条）
- 勾选多个会话一键恢复；"恢复昨日"一键找回昨天所有窗口
- 双击某行直接恢复该会话
- 中英双语界面（跟随系统语言，`CLAUDE_NOTEPAD_LANG=zh|en` 可覆盖）

恢复 = 在原项目目录新开一个 Windows Terminal 窗口执行 `claude --resume <sessionId>`，对话历史完整还原。

## 使用

从 [Releases](../../releases) 下载 `claude-notepad.exe` 双击运行；或直接跑源码：

```bash
python notepad.py
```

从源码打包：

```bash
pyinstaller --onefile --noconsole --name claude-notepad notepad.py
```

要求：

- Windows 10/11（未打包运行需 Python 3.10+）
- `claude` CLI 在 PATH 中
- 有 Windows Terminal 更佳，没有则回退 cmd 窗口

## 原理

Claude Code 会把每个会话完整记录在 `~/.claude/projects/<项目目录编码>/<sessionId>.jsonl`，其中自带：

| 信息 | 来源 |
|---|---|
| 最后活跃时间 | 文件 mtime |
| 项目目录 | 记录内 `cwd` 字段 |
| 在干什么 | `ai-title` 字段（Claude 自动生成），无则回退首条用户消息 |

claude-notepad 只是把这些读出来摆好，恢复时调用原生 `claude --resume`。

## 已知边界

- 打开但没输入过的窗口不会留下记录（Claude Code 首次交互才落盘）
- 恢复的是对话历史，不是终端窗口布局

## 开发

```bash
python test_notepad.py   # 11 项自检
```

## License

[Apache-2.0](LICENSE)
