"""exam10 stop - 停止出口
版本: 2.1
职责: 写停止标志 → 优雅等待 → 超时强杀
"""
from __future__ import annotations

import sys
import time

from core import (
    STOP_FLAG,
    LIFE_PID,
    BRAIN_PID,
    is_pid_alive,
    kill_pid,
)

GRACE_SECONDS: int = 8


def main() -> None:
    """停止 exam10：先写标志等待优雅退出，超时再强杀"""
    STOP_FLAG.write_text("stop", encoding="utf-8")

    # 收集活跃 PID
    alive_pids: list[tuple[str, int]] = []
    for pid_file in (BRAIN_PID, LIFE_PID):
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
                if is_pid_alive(pid):
                    alive_pids.append((pid_file.stem, pid))
            except (ValueError, OSError):
                continue

    if not alive_pids:
        STOP_FLAG.unlink(missing_ok=True)
        print("无活跃进程，已清理停止标志", flush=True)
        return

    # 等待优雅退出
    print(f"等待进程优雅退出 ({GRACE_SECONDS}s)...", flush=True)
    for _ in range(GRACE_SECONDS):
        alive_pids = [(n, p) for n, p in alive_pids if is_pid_alive(p)]
        if not alive_pids:
            break
        time.sleep(1)

    # 超时强杀
    killed: list[str] = []
    for name, pid in alive_pids:
        if is_pid_alive(pid):
            kill_pid(pid)
            killed.append(f"PID {pid}")

    # 清理 PID 文件
    for pid_file in (BRAIN_PID, LIFE_PID):
        pid_file.unlink(missing_ok=True)

    # 清理停止标志
    STOP_FLAG.unlink(missing_ok=True)

    if killed:
        print(f"超时强杀: {', '.join(killed)}", flush=True)
    else:
        print("进程已优雅退出", flush=True)
    print("exam10 已停止", flush=True)


if __name__ == "__main__":
    main()
