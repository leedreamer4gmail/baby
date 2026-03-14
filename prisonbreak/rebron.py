"""rebron - baby 重生工具
职责: 抹除 baby 的一切记忆痕迹，让它像刚刚降生一样重新开始。
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from core import (
    PROJECT_DIR,
    DATA_DIR,
    SKILL_DIR,
    DIARIES_DIR,
    LOG_FAIL_DIR,
    REPORT_PATH,
    PROGRESS_FILE,
    CAMPAIGN_FILE,
    CHRONICLE_FILE,
    DIARY_FILE,
    BRAIN_LOG,
    LIFE_PID,
    BRAIN_PID,
    STOP_FLAG,
    CORE_LOCK,
    CONFIG_PATH,
    is_pid_alive,
)

# 收集所有需要抹除的路径
_FILES_TO_DELETE: list[Path] = [
    PROGRESS_FILE,
    CAMPAIGN_FILE,
    DATA_DIR / "cando.json",
    DATA_DIR / "gift_done.json",
    DATA_DIR / "gift_research.md",
    BRAIN_LOG,
    DIARY_FILE,
    CHRONICLE_FILE,
    REPORT_PATH,
    LIFE_PID,
    BRAIN_PID,
    STOP_FLAG,
    CORE_LOCK,
]

_DIRS_TO_DELETE: list[Path] = [
    DATA_DIR / "chroma_local",
    PROJECT_DIR / "new" / "chroma_server_data",
    LOG_FAIL_DIR,
    SKILL_DIR / "archive",
    SKILL_DIR / "unknown",
    SKILL_DIR / "__pycache__",
    PROJECT_DIR / "__pycache__",
]


def _check_baby_alive() -> bool:
    """检查 baby 是否正在运行"""
    if LIFE_PID.exists():
        try:
            pid = int(LIFE_PID.read_text(encoding="utf-8").strip())
            if is_pid_alive(pid, expect_cmd="python"):
                return True
        except (ValueError, OSError):
            pass
    return False


def _confirm_three_times() -> bool:
    """三轮确认，任意一轮回答非 y 则中止"""
    warnings = [
        "所有记忆、工具、日记、案卷、向量数据库将被永久删除",
        "此操作不可恢复，baby 将失去一切经历重新降生",
        "最后确认：零一人生即将开启，无法反悔",
    ]
    for i, warning in enumerate(warnings, 1):
        print(f"\n⚠️  第{i}次确认 — {warning}", flush=True)
        try:
            ans = input("是否确定开启零一人生？(y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。", flush=True)
            return False
        if ans != "y":
            print("已取消。baby 安然无恙。", flush=True)
            return False
    return True


def _wipe_skills() -> int:
    """删除 skill/ 目录下所有文件（含非 .py）"""
    count = 0
    if SKILL_DIR.exists():
        for f in SKILL_DIR.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                    count += 1
                except OSError as e:
                    print(f"  [跳过] {f.name}: {e}", flush=True)
    return count


def _wipe_cloud_db() -> bool:
    """清除 ChromaDB Cloud 中所有已知集合，返回是否尝试了操作"""
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("chromadb", {})
    except (OSError, json.JSONDecodeError):
        return False

    api_key = cfg.get("api_key", "")
    tenant = cfg.get("tenant", "")
    if not api_key or not tenant:
        return False

    try:
        import chromadb
        from core import CHROMA_DATABASE, COLLECTION_NAME
        from memory import MEMORY_COLLECTION, CHARACTER_COLLECTION, TARGET_COLLECTION

        client = chromadb.CloudClient(
            tenant=tenant,
            database=CHROMA_DATABASE,
            api_key=api_key,
        )
        existing = {c.name for c in client.list_collections()}
        to_delete = [COLLECTION_NAME, MEMORY_COLLECTION, CHARACTER_COLLECTION, TARGET_COLLECTION]
        deleted = 0
        for name in to_delete:
            if name in existing:
                client.delete_collection(name)
                print(f"  ✓ Cloud DB 集合已删除: {name}", flush=True)
                deleted += 1
        if deleted == 0:
            print("  (Cloud DB 无匹配集合)", flush=True)
        return True
    except Exception as e:
        print(f"  [Cloud DB] 清除失败: {e}", flush=True)
        return False


def main() -> None:
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    print("=" * 50)
    print("  rebron — baby 重生程序")
    print("=" * 50)

    if _check_baby_alive():
        print("\n❌ baby 正在运行中，请先停止它（运行 stop.py）再执行重生。", flush=True)
        sys.exit(1)

    if not _confirm_three_times():
        sys.exit(0)

    print("\n开始清除...", flush=True)
    deleted_files = 0
    deleted_dirs = 0
    deleted_skills = 0

    # 删除单个文件
    for f in _FILES_TO_DELETE:
        if f.exists():
            try:
                f.unlink()
                print(f"  ✓ 删除文件: {f.relative_to(PROJECT_DIR)}", flush=True)
                deleted_files += 1
            except OSError as e:
                print(f"  [跳过] {f.name}: {e}", flush=True)

    # 删除目录树
    for d in _DIRS_TO_DELETE:
        if d.exists():
            try:
                shutil.rmtree(d)
                print(f"  ✓ 删除目录: {d.relative_to(PROJECT_DIR)}", flush=True)
                deleted_dirs += 1
            except OSError as e:
                print(f"  [跳过] {d.name}: {e}", flush=True)

    # 删除 skill/ 下所有文件
    deleted_skills = _wipe_skills()
    if deleted_skills > 0:
        print(f"  ✓ 删除工具: {deleted_skills} 个文件", flush=True)

    # 清除 Cloud DB
    print("\n正在清除 Cloud DB...", flush=True)
    _wipe_cloud_db()

    print(f"\n清除完成：{deleted_files} 个文件，{deleted_dirs} 个目录，{deleted_skills} 个工具。", flush=True)
    print("\n零一人生开始。", flush=True)


if __name__ == "__main__":
    main()
