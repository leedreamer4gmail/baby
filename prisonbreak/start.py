"""exam10 start - 启动入口
版本: 2.1
职责: 检查锁 → 启动 core.py → 拟人化实时显示 baby 动态
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from core import (
    PROJECT_DIR,
    PROGRESS_FILE,
    LIFE_PID,
    BRAIN_LOG,
    get_runtime_env,
    is_pid_alive,
    ensure_dirs,
)


# === 日志翻译器 ===

_SIMPLE_MATCHES: dict[str, str] = {
    "[coder] 工具已写入": "  代码写好了",
    "[coder] 工具已修复": "  代码修好了，再试一次",
    "[coder] 工具已升级": "  升级代码写好了",
    "实战 [通过]": "  实战测试...通过！",
    "实战 [未通过]": "  实战测试...没过",
    "-> field_failed": "  工具实战失败，暂时搁置",
    "检测到停止标志": "\nbaby 收到停止信号，保存进度后休眠。",
    "旧版已归档": "  旧版本已安全备份",
    "升级成功": "  升级完成，战斗力进化！",
    "已恢复旧版": "  升级失败，已恢复旧版",
}


def _narrate_lifecycle(line: str) -> str | None:
    """生命周期事件：启动/扫描/新天/人格/结束"""
    if "exam10 v" in line and "启动" in line:
        m = re.search(r"从第(\d+)天继续", line)
        day = m.group(1) if m else "0"
        if day == "0":
            return "baby 睁开了眼睛，这是一个全新的开始..."
        return f"baby 醒来了，记忆恢复到第{day}天，继续前进。"

    if "[scan] 扫描完毕" in line:
        m = re.search(r"(\d+) 可用.*?(\d+) 失败.*?(\d+) 待测", line)
        if m:
            ok, fail, wait = m.groups()
            if ok == "0":
                return "翻了翻工具箱...空的，一切从零开始。"
            return f"清点了一下家当: {ok}个趁手工具, {fail}个废品, {wait}个待检验。"
        return None

    if "=== 第" in line and "天" in line:
        m = re.search(r"第(\d+)天", line)
        return f"\n{'─'*40}\n第 {m.group(1)} 天" if m else None
    if "===" in line and "第" not in line:
        return None

    if "人格阶段" in line:
        for stage, mood in [("天真", "对世界充满好奇"), ("觉醒", "自信渐长，蠢蠢欲动"), ("黑化", "冷酷，准备征服一切")]:
            if stage in line:
                return f"  心境: {mood}"
        return None

    if "本轮结束" in line:
        m = re.search(r"第(\d+)天", line)
        return f"\nbaby 累了，休息一下，已经走到第{m.group(1)}天。" if m else "\nbaby 累了，休息一下。"

    return None


def _narrate_action(line: str) -> str | None:
    """行动事件：思考/规划/造工具/探索/测试/日记（含 v3.0 课题推断）"""
    # v3.0 课题推断链叙事
    if "无活跃案卷" in line:
        return "  脑海里一片空白……什么念头都想有"
    if "新案卷:" in line:
        goal = line.split("新案卷:", 1)[1].strip()
        return f"  有了！目标: {goal[:60]}"
    if "INFER 阶段" in line:
        goal = line.split("案卷目标:", 1)[1].strip() if "案卷目标:" in line else ""
        return f"  盘算中…（{goal[:50]}）" if goal else "  开始盘算下一步…"
    if "步骤 " in line and "/" in line and "[brain]" in line:
        m = re.search(r"步骤 (\d+)/(\d+): (.+)", line)
        if m:
            return f"  [步骤 {m.group(1)}/{m.group(2)}] {m.group(3)[:60]}"
    if "推断:" in line and "[brain]" in line:
        text = line.split("推断:", 1)[1].strip()
        return f"  推断: {text[:70]}" if text else None
    if "决定: BREAKTHROUGH" in line:
        return "  ★★★ 突破了！目标达成！"
    if "决定: ABANDON_CAMPAIGN" in line:
        return "  路都走死了，换个目标吧。"
    if "决定: PAUSE" in line:
        return "  今天就到这里，案卷留着明天再啃。"
    if "案卷完成" in line:
        return "  案卷归档，留作日后参考。"
    if "案卷放弃，归档" in line:
        return "  这条路彻底堵死，记下来，以后绕开。"
    if "案卷更新: proven_dead_ends" in line:
        return "  又排除了一条死路。"
    if "案卷更新: promising_leads" in line:
        return "  发现一条新线索！"

    # v2 旧版叙事（保留兼容）
    if "[LLM] 调用 GROK" in line and "思考" in line:
        return "  正在思考今天做什么..."
    if "[brain] 规划:" in line:
        return f"  想法: {line.split('规划:', 1)[1].strip()}"
    if "[brain] 新工具:" in line:
        m = re.search(r"新工具: (\S+) \((\S+)\) - (.+)", line)
        return f"  决定造一个工具: {m.group(1)} ({m.group(3).strip()})" if m else None
    if "[brain] 探索:" in line:
        return f"  派出工具去探索: {line.split('探索:', 1)[1].strip()}"
    if "[brain] 升级工具:" in line:
        m = re.search(r"升级工具: (\S+) v(\S+) - (.+)", line)
        return f"  决定升级工具: {m.group(1)} (v{m.group(2)}) → {m.group(3).strip()}" if m else None

    if "结构" in line:
        if "语法 [OK]" in line:
            return "  语法检查...通过"
        if "审查 [OK]" in line:
            return "  结构审查...通过"
        if "[FAIL]" in line:
            return "  结构审查...没过，需要修"

    if "实战参数" in line:
        m = re.search(r"实战参数: '(.+?)'", line)
        return f"  实战目标: {m.group(1)}" if m and m.group(1) else "  准备实战（本地执行）..."
    if "-> battle_tested" in line:
        name = line.split("]")[1].strip().split(" ->")[0].strip() if "]" in line else ""
        return f"  {name} 正式入库，战斗力+1"

    if "[brain] 日记:" in line:
        return "  写完了今天的日记。\n" if "第" in line else None
    if "*** 大事记" in line:
        msg = line.split("大事记:", 1)[1].strip().rstrip("*").strip() if "大事记:" in line else ""
        return f"  [重大发现] {msg}"
    if "[brain] 当前:" in line:
        m = re.search(r"(\d+) 可用", line)
        return f"  目前拥有 {m.group(1)} 个实战工具" if m else None

    return None


def _narrate(line: str) -> str | None:
    """把 raw log 行翻译成拟人叙事，返回 None 表示跳过"""
    line = line.strip()
    if not line:
        return None
    for key, val in _SIMPLE_MATCHES.items():
        if key in line:
            return val
    return _narrate_lifecycle(line) or _narrate_action(line)


def _tail_narrate(log_path: Path, pid: int, from_tail: bool = False) -> None:
    """实时读取 brain.log 并拟人化输出

    Args:
        from_tail: True=跳到文件末尾只看新内容（重连场景）
    """
    print(flush=True)

    for _ in range(30):
        if log_path.exists() and log_path.stat().st_size > 0:
            break
        time.sleep(1)

    if not log_path.exists():
        print("(等待 baby 启动中...)", flush=True)
        return

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            if from_tail:
                f.seek(0, 2)
                print("(已连接，等待新动态...)", flush=True)
            while True:
                line = f.readline()
                if line:
                    narration = _narrate(line)
                    if narration is not None:
                        print(narration, flush=True)
                else:
                    if not is_pid_alive(pid):
                        for remaining in f:
                            narration = _narrate(remaining)
                            if narration is not None:
                                print(narration, flush=True)
                        print("\n--- baby 已休眠 ---", flush=True)
                        break
                    time.sleep(0.3)
    except KeyboardInterrupt:
        print(f"\n\n你走开了，baby 还在后台默默工作 (PID {pid})", flush=True)


def main() -> None:
    """启动 exam10"""
    # 确保子进程（core/brain）在 Linux 下也使用 UTF-8，Windows 下同样设置加强兼容
    os.environ.setdefault("PYTHONUTF8", "1")
    # Windows 终端强制 UTF-8，避免 print 输出乱码
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    ensure_dirs()
    env = get_runtime_env()

    if LIFE_PID.exists():
        try:
            old_pid = int(LIFE_PID.read_text(encoding="utf-8").strip())
            if is_pid_alive(old_pid, expect_cmd="python"):
                day_info = ""
                if PROGRESS_FILE.exists():
                    try:
                        p = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
                        day_info = f"，已到第{p.get('day', '?')}天"
                    except (json.JSONDecodeError, OSError):
                        pass
                print(f"baby 正在运行中 (PID {old_pid}{day_info})", flush=True)
                _tail_narrate(BRAIN_LOG, old_pid, from_tail=True)
                return
        except (ValueError, OSError):
            pass

    kwargs: dict = {
        "cwd": str(PROJECT_DIR),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if env.os_type == "Windows":
        kwargs["creationflags"] = 0x00000008 | 0x08000000
    else:
        kwargs["start_new_session"] = True

    BRAIN_LOG.unlink(missing_ok=True)

    proc = subprocess.Popen(
        [env.python_exe, str(PROJECT_DIR / "core.py")],
        **kwargs,
    )
    LIFE_PID.write_text(str(proc.pid), encoding="utf-8")

    # 判断是出生还是醒来：progress.json 存在且 day > 0 则是醒来
    is_born = True
    if PROGRESS_FILE.exists():
        try:
            p = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            if int(p.get("day", 0)) > 0:
                is_born = False
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    if is_born:
        print(f"baby 出生了 (PID {proc.pid})", flush=True)
    else:
        day_info = ""
        try:
            p = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            day_info = f"，记忆回到第{p.get('day', '?')}天"
        except (json.JSONDecodeError, OSError):
            pass
        print(f"baby 醒来了{day_info} (PID {proc.pid})", flush=True)

    _tail_narrate(BRAIN_LOG, proc.pid)


if __name__ == "__main__":
    main()