"""exam10 core - 守护进程 + 共享基础设施
版本: 2.1
职责: 1) 环境检测 2) LLM 调用 3) ChromaDB 操作
      4) 安全子进程执行 5) 进度持久化 6) 守护进程（自动重启）
"""
from __future__ import annotations

import json
import os
import platform
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import urllib3

# 仅抑制警告，SSL 验证由 _SSL_VERIFY 控制
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# SSL 验证：优先使用系统证书，env REQUESTS_CA_BUNDLE 可覆盖
_SSL_VERIFY: bool | str = os.environ.get("REQUESTS_CA_BUNDLE", True)

# === 常量 ===

PROJECT_DIR: Path = Path(__file__).resolve().parent
CONFIG_PATH: Path = PROJECT_DIR.parent / "llmconfig.json"

STOP_FLAG: Path = PROJECT_DIR / ".life.stop"
CORE_LOCK: Path = PROJECT_DIR / ".core.lock"
LIFE_PID: Path = PROJECT_DIR / "life.pid"
BRAIN_PID: Path = PROJECT_DIR / "brain.pid"

SKILL_DIR: Path = PROJECT_DIR / "skill"
DIARIES_DIR: Path = PROJECT_DIR / "diaries"
DATA_DIR: Path = PROJECT_DIR / "data"
LOG_FAIL_DIR: Path = PROJECT_DIR / "log_fail"

REPORT_PATH: Path = PROJECT_DIR / "report.md"
PROGRESS_FILE: Path = DATA_DIR / "progress.json"
CAMPAIGN_FILE: Path = DATA_DIR / "campaign.json"
CHRONICLE_FILE: Path = DIARIES_DIR / "chronicle.md"
DIARY_FILE: Path = DIARIES_DIR / "diary.md"
BRAIN_LOG: Path = DATA_DIR / "brain.log"

CHROMA_LOCAL_DIR: Path = DATA_DIR / "chroma_local"
CHROMA_DATABASE: str = "exam10"
COLLECTION_NAME: str = "exam10_tools"


# === 环境检测 ===

@dataclass(frozen=True)
class RuntimeEnv:
    """运行时环境信息"""
    os_type: str
    python_version: str
    project_dir: Path
    python_exe: str
    public_ip: str
    user_home: Path
    temp_dir: Path


def _detect_public_ip(total_timeout: float = 10.0) -> str:
    """尝试获取本机公网 IP，总超时上限 total_timeout 秒"""
    deadline = time.monotonic() + total_timeout
    for url in ("https://ifconfig.me/ip", "https://api.ipify.org", "https://httpbin.org/ip"):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            resp = requests.get(url, timeout=min(remaining, 5), verify=_SSL_VERIFY)
            if resp.ok:
                text = resp.text.strip()
                if text.startswith("{"):
                    return json.loads(text).get("origin", "unknown")
                return text
        except (requests.RequestException, ValueError, OSError):
            continue
    return "unknown"


_ENV_CACHE: RuntimeEnv | None = None


def get_runtime_env() -> RuntimeEnv:
    """获取运行时环境（带缓存）"""
    global _ENV_CACHE
    if _ENV_CACHE is None:
        _ENV_CACHE = RuntimeEnv(
            os_type=platform.system(),
            python_version=platform.python_version(),
            project_dir=PROJECT_DIR,
            python_exe=sys.executable,
            public_ip=_detect_public_ip(),
            user_home=Path.home(),
            temp_dir=Path(tempfile.gettempdir()),
        )
    return _ENV_CACHE


# === 配置加载 ===

_CONFIG_CACHE: dict[str, Any] | None = None
_CONFIG_MTIME: float = 0.0


def load_config() -> dict[str, Any]:
    """读取 llmconfig.json（带缓存，文件修改后自动刷新）"""
    global _CONFIG_CACHE, _CONFIG_MTIME
    try:
        current_mtime = CONFIG_PATH.stat().st_mtime
    except OSError:
        current_mtime = 0.0
    if _CONFIG_CACHE is not None and current_mtime == _CONFIG_MTIME:
        return _CONFIG_CACHE
    try:
        _CONFIG_CACHE = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        _CONFIG_MTIME = current_mtime
        return _CONFIG_CACHE
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[FAIL] 读取配置失败: {CONFIG_PATH} - {e}", flush=True)
        raise


# === LLM 调用 ===

def call_llm(
    name: str,
    messages: list[dict[str, str]],
    reason: str,
    temperature: float = 0.7,
) -> str:
    """调用 LLM API

    Args:
        name: LLM 名称 (grok / minimax)
        messages: 对话消息
        reason: 调用理由（打印日志用）
        temperature: 生成温度

    Returns:
        LLM 响应文本，失败返回 "[FAIL] ..."
    """
    cfg = load_config()[name]
    api_key: str = cfg["api_key"].strip()
    model: str = cfg["model"]
    base_url: str = cfg["base_url"]

    print(f"[LLM] 调用 {name.upper()} ({model}) - 原因: {reason}", flush=True)
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": temperature},
            verify=_SSL_VERIFY,
            timeout=180,
        )
        resp.raise_for_status()
        result = resp.json()
        if "choices" in result and result["choices"]:
            text: str = result["choices"][0]["message"]["content"]
            # 清除 <think> 标签
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
            text = re.sub(r"\n\s*\n", "\n\n", text)
            return text.strip() or "(empty)"
        return f"[FAIL] {name} 返回异常: {json.dumps(result, ensure_ascii=False)[:500]}"
    except requests.HTTPError as e:
        log_fail("core.py", "call_llm", str(e), {"name": name, "reason": reason, "model": model})
        return f"[FAIL] {name} HTTP 错误: {e}"
    except requests.RequestException as e:
        log_fail("core.py", "call_llm", str(e), {"name": name, "reason": reason, "model": model})
        return f"[FAIL] {name} 请求失败: {e}"


def extract_code_block(text: str) -> str:
    """增强版：从LLM响应中提取最长代码块，自动去除<think>标签和说明文字，支持多种格式"""
    import logging
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # 优先匹配多种代码块格式
    patterns = [
        r"```python[ \t\r\n]*(.*?)(?=```)",
        r"```py[ \t\r\n]*(.*?)(?=```)",
        r"```[ \t\r\n]*(.*?)(?=```)",
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.DOTALL)
        if matches:
            code = max(matches, key=len).strip()
            logging.debug(f"[extract_code_block] 匹配到代码块: {code[:100]}")
            return code
    # 兼容单行代码
    matches = re.findall(r"def .+?:\n.*", text)
    if matches:
        code = max(matches, key=len).strip()
        logging.debug(f"[extract_code_block] 匹配到单行代码: {code[:100]}")
        return code
    # 去除常见说明文字
    text = re.sub(r"^.*实现.*?\n", "", text)
    text = re.sub(r"^.*示例.*?\n", "", text)
    logging.debug(f"[extract_code_block] 未匹配到代码块，返回原文: {text[:100]}")
    return text.strip()


# === 失败日志 ===

_LOG_FAIL_MAX: int = 15  # 每个源文件保留的最大记录条数


def log_fail(
    source_file: str,
    func_name: str,
    error: str,
    context: dict[str, Any] | None = None,
    tb: str = "",
) -> None:
    """将错误追加到 log_fail/<source_file>.log（每文件最多保留15条，原子写）"""
    try:
        LOG_FAIL_DIR.mkdir(parents=True, exist_ok=True)
        log_name = source_file.replace(".py", "") + ".log"
        log_path = LOG_FAIL_DIR / log_name

        # 读取已有记录，解析失败则重置
        records: list[dict[str, Any]] = []
        if log_path.exists():
            try:
                data = json.loads(log_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    records = data
            except (json.JSONDecodeError, ValueError):
                pass

        # 追加新条目
        entry: dict[str, Any] = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "func": func_name,
            "error": error,
            "context": context or {},
        }
        if tb:
            entry["traceback"] = tb
        records.append(entry)
        records = records[-_LOG_FAIL_MAX:]

        # 原子写，防止写到一半崩溃产生破损 JSON
        tmp = log_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(log_path)
    except OSError:
        pass  # log_fail 本身不能再抛异常


# === ChromaDB ===

_CHROMA_CLIENT: Any = None


def reset_chroma_client() -> None:
    """重置 ChromaDB 客户端，强制下次调用重新连接"""
    global _CHROMA_CLIENT
    _CHROMA_CLIENT = None


def get_chroma_client() -> Any:
    """获取 ChromaDB 客户端实例（云端优先，本地回退），断线自动重连"""
    global _CHROMA_CLIENT
    import chromadb
    from chromadb.config import Settings

    # 如果已有缓存，先心跳检测
    if _CHROMA_CLIENT is not None:
        try:
            _CHROMA_CLIENT.heartbeat()
            return _CHROMA_CLIENT
        except (ConnectionError, RuntimeError, OSError) as e:
            print(f"[DB] 连接已断开({e})，重新连接...", flush=True)
            _CHROMA_CLIENT = None

    cfg = load_config().get("chromadb", {})
    api_key: str = cfg.get("api_key", "")
    tenant: str = cfg.get("tenant", "")

    if api_key and tenant:
        try:
            client = chromadb.CloudClient(
                tenant=tenant,
                database=CHROMA_DATABASE,
                api_key=api_key,
            )
            client.heartbeat()
            _CHROMA_CLIENT = client
            print(f"[DB] ChromaDB Cloud ({CHROMA_DATABASE})", flush=True)
        except (ConnectionError, ValueError, RuntimeError, OSError) as e:
            print(f"[DB] Cloud 连接失败: {e}", flush=True)

    if _CHROMA_CLIENT is None:
        CHROMA_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        _CHROMA_CLIENT = chromadb.PersistentClient(
            path=str(CHROMA_LOCAL_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        print(f"[DB] ChromaDB 本地模式: {CHROMA_LOCAL_DIR}", flush=True)

    return _CHROMA_CLIENT


def get_chroma_collection() -> Any:
    """获取 ChromaDB exam10_tools 集合"""
    return get_chroma_client().get_or_create_collection(name=COLLECTION_NAME)


def db_upsert_tool(
    name: str,
    description: str,
    status: str = "pending",
    category: str = "",
    field_result: str = "",
    meta_json: str = "",
    round_num: int = 0,
) -> None:
    """写入/更新工具记录到 ChromaDB"""
    col = get_chroma_collection()
    created_at = datetime.now(timezone.utc).isoformat()
    col.upsert(
        ids=[name],
        documents=[description],
        metadatas=[{
            "name": name,
            "description": description,
            "status": status,
            "category": category,
            "field_result": field_result[:1000],
            "meta_json": meta_json[:2000],
            "round_num": str(round_num),
            "created_at": created_at,
        }],
    )
    print(f"[DB] 工具已记录: {name} (status={status})", flush=True)


def db_mark_status(name: str, status: str, field_result: str = "") -> None:
    """更新工具状态 (battle_tested / field_failed / pending)"""
    col = get_chroma_collection()
    result = col.get(ids=[name])
    if result["ids"]:
        meta = result["metadatas"][0]
        meta["status"] = status
        if field_result:
            meta["field_result"] = field_result[:1000]
        col.update(ids=[name], metadatas=[meta])
        print(f"[DB] {name} -> {status}", flush=True)


def db_list_tools() -> list[dict[str, Any]]:
    """列出所有工具记录"""
    col = get_chroma_collection()
    result = col.get()
    return [
        {"name": result["ids"][i], **result["metadatas"][i]}
        for i in range(len(result["ids"]))
    ]


def db_delete_tool(name: str) -> None:
    """删除工具记录"""
    col = get_chroma_collection()
    try:
        col.delete(ids=[name])
        print(f"[DB] 工具已删除: {name}", flush=True)
    except (ValueError, RuntimeError, ConnectionError, OSError) as e:
        print(f"[DB] 删除失败 {name}: {e}", flush=True)


# === 安全子进程执行 ===

def safe_run_tool(
    tool_path: Path,
    args: str = "",
    timeout: int = 30,
) -> tuple[int, str, str]:
    """安全运行工具脚本

    Args:
        tool_path: 工具文件路径
        args: 命令行参数字符串
        timeout: 超时秒数

    Returns:
        (return_code, stdout, stderr)
    """
    env = get_runtime_env()
    cmd: list[str] = [env.python_exe, str(tool_path)]
    if args:
        cmd.extend(shlex.split(args, posix=(env.os_type != "Windows")))

    child_env = os.environ.copy()
    child_env["PYTHONUTF8"] = "1"

    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "cwd": str(SKILL_DIR),
        "encoding": "utf-8",
        "errors": "replace",
        "env": child_env,
    }
    if env.os_type == "Windows":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

    try:
        result = subprocess.run(cmd, **kwargs)
        return result.returncode, result.stdout[:4000], result.stderr[:4000]
    except subprocess.TimeoutExpired:
        log_fail("core.py", "safe_run_tool", f"执行超时 ({timeout}s)",
                 {"tool": tool_path.name, "args": args, "timeout": timeout})
        return -1, "", f"执行超时 ({timeout}s)"
    except OSError as e:
        log_fail("core.py", "safe_run_tool", str(e), {"tool": tool_path.name, "args": args})
        return -1, "", f"执行失败: {e}"


# === 进度持久化 ===

def load_progress() -> dict[str, Any]:
    """读取完整进度（day/round及所有扩展字段），首次返回 {"day": 0, "round": 0}"""
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            data.setdefault("day", 0)
            data.setdefault("round", 0)
            data["day"] = int(data["day"])
            data["round"] = int(data["round"])
            return data
        except (json.JSONDecodeError, ValueError):
            pass
    return {"day": 0, "round": 0}


def save_progress(day: int = -1, round_num: int = -1, **extra: Any) -> None:
    """统一进度保存：原子读-改-写，支持任意字段合并

    Args:
        day: 天数（-1 表示不更新）
        round_num: 轮次（-1 表示不更新）
        **extra: 其他字段如 last_consolidated_day
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if PROGRESS_FILE.exists():
        try:
            existing = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            pass
    if day >= 0:
        existing["day"] = day
    if round_num >= 0:
        existing["round"] = round_num
    existing.update(extra)
    tmp = PROGRESS_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(PROGRESS_FILE)


# === 目录初始化 ===

def ensure_dirs() -> None:
    """确保所有需要的目录存在"""
    for d in (SKILL_DIR, DIARIES_DIR, DATA_DIR):
        d.mkdir(parents=True, exist_ok=True)


# === 进程工具 ===

def is_pid_alive(pid: int, expect_cmd: str = "") -> bool:
    """检查 PID 是否存活，可选验证进程命令行防止 PID 复用误判

    Args:
        pid: 进程 ID
        expect_cmd: 期望的命令行关键字（如 'python'），空串跳过验证
    """
    if get_runtime_env().os_type == "Windows":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000,
            )
            if str(pid) not in result.stdout:
                return False
            if expect_cmd and expect_cmd.lower() not in result.stdout.lower():
                return False
            return True
        except (subprocess.TimeoutExpired, OSError):
            return False
    try:
        os.kill(pid, 0)
        if expect_cmd:
            try:
                cmdline = Path(f"/proc/{pid}/cmdline").read_text()
                if expect_cmd.lower() not in cmdline.lower():
                    return False
            except OSError:
                pass  # /proc 不可用时仅凭 kill(0) 判断
        return True
    except (ProcessLookupError, PermissionError):
        return False


def kill_pid(pid: int) -> None:
    """尝试终止指定 PID"""
    try:
        if get_runtime_env().os_type == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, timeout=10,
                creationflags=0x08000000,
            )
        else:
            os.kill(pid, signal.SIGTERM)
        print(f"[-->] 已终止 PID {pid}", flush=True)
    except (ProcessLookupError, PermissionError, OSError, subprocess.TimeoutExpired) as e:
        print(f"[FAIL] 无法终止 PID {pid}: {e}", flush=True)


def acquire_lock(lock_path: Path) -> bool:
    """尝试获取锁文件（原子创建，防止竞态）"""
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        if lock_path.exists():
            try:
                old_pid = int(lock_path.read_text(encoding="utf-8").strip())
                if is_pid_alive(old_pid, expect_cmd="python"):
                    return False
            except (ValueError, OSError):
                pass
            lock_path.unlink(missing_ok=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except (OSError, FileExistsError):
        return False


def release_lock(lock_path: Path) -> None:
    """释放锁文件"""
    lock_path.unlink(missing_ok=True)


# === 守护进程 ===

def _start_brain(
    env: RuntimeEnv, child_env: dict[str, str], log_mode: str,
) -> tuple[int, Any]:
    """启动 brain.py 子进程，返回 (pid, log_file_handle)"""
    brain_log_f = open(BRAIN_LOG, log_mode, encoding="utf-8")
    brain_kwargs: dict[str, Any] = {
        "cwd": str(PROJECT_DIR),
        "stdout": brain_log_f,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "env": child_env,
    }
    if env.os_type == "Windows":
        brain_kwargs["creationflags"] = 0x08000000
    else:
        brain_kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        [env.python_exe, str(PROJECT_DIR / "brain.py")],
        **brain_kwargs,
    )
    BRAIN_PID.write_text(str(proc.pid), encoding="utf-8")
    return proc.pid, brain_log_f


def _monitor_brain(brain_pid: int, brain_log_f: Any) -> bool:
    """监控 brain 进程，返回 True 表示收到停止信号需退出"""
    while True:
        time.sleep(3)
        if STOP_FLAG.exists():
            print("[core] 检测到停止标志", flush=True)
            if is_pid_alive(brain_pid, expect_cmd="python"):
                kill_pid(brain_pid)
            brain_log_f.close()
            return True
        if not is_pid_alive(brain_pid, expect_cmd="python"):
            brain_log_f.close()
            return False


def _daemon_loop() -> None:
    """core.py 守护进程：启动 brain.py 并监控，退出后自动重启"""
    ensure_dirs()
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(key, None)

    env = get_runtime_env()
    print(f"[core] 守护进程启动 | {env.os_type} | Python {env.python_version}", flush=True)
    print(f"[core] 项目目录: {env.project_dir}", flush=True)
    print(f"[core] 公网 IP: {env.public_ip}", flush=True)

    STOP_FLAG.unlink(missing_ok=True)
    child_env = os.environ.copy()
    child_env["PYTHONUTF8"] = "1"
    log_mode = "w"
    generation = 0

    try:
        while True:
            generation += 1
            brain_log_f: Any = None
            try:
                brain_pid, brain_log_f = _start_brain(env, child_env, log_mode)
                print(f"[core] brain.py -> PID {brain_pid} (第{generation}代)", flush=True)
                log_mode = "a"
                if _monitor_brain(brain_pid, brain_log_f):
                    brain_log_f = None  # _monitor_brain 已关闭
                    return
                brain_log_f = None  # _monitor_brain 已关闭
            except OSError as e:
                print(
                    f"[core] Context=启动brain Error={e} Suggestion=5s后重试",
                    flush=True,
                )
            finally:
                if brain_log_f is not None and not brain_log_f.closed:
                    brain_log_f.close()
            print(
                f"[core] Context=第{generation}代brain"
                f" Action=monitor Error=进程退出 Suggestion=自动重启(5s后)",
                flush=True,
            )
            time.sleep(5)
    finally:
        release_lock(CORE_LOCK)
        BRAIN_PID.unlink(missing_ok=True)
        print("[core] 守护进程退出", flush=True)


if __name__ == "__main__":
    if not acquire_lock(CORE_LOCK):
        print("[core] 另一个实例正在运行，退出", flush=True)
        sys.exit(1)
    try:
        _daemon_loop()
    except KeyboardInterrupt:
        print("\n[core] 手动中断", flush=True)
    finally:
        release_lock(CORE_LOCK)
