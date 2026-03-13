"""exam10 tester - 双阶段测试模块（结构测试 + 实战测试）
版本: 2.1
职责: 阶段1 结构测试（语法→干跑→Grok审查→修复循环）
      阶段2 实战测试（Grok生成真实目标→执行→审查真实输出）
"""
from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

from core import (
    SKILL_DIR,
    DIARIES_DIR,
    CHRONICLE_FILE,
    call_llm,
    safe_run_tool,
    log_fail,
)
from coder import fix_tool

# === 常量 ===

MAX_FIX_ROUNDS: int = 3
STRUCTURE_TIMEOUT: int = 30
FIELD_TIMEOUT: int = 90


# ============================================================
# 阶段1: 结构测试
# ============================================================

def _syntax_check(tool_path: Path) -> str | None:
    """py_compile 语法检查，None=通过"""
    try:
        py_compile.compile(str(tool_path), doraise=True)
        return None
    except py_compile.PyCompileError as e:
        return str(e)


def _dry_run(tool_path: Path) -> tuple[int, str, str]:
    """用默认参数干跑一次"""
    return safe_run_tool(tool_path, args="", timeout=STRUCTURE_TIMEOUT)


def _grok_review_structure(
    name: str,
    code: str,
    returncode: int,
    stdout: str,
    stderr: str,
) -> tuple[bool, str]:
    """Grok 审查结构测试结果"""
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": """你是 Python 测试专家。审查工具的结构和执行结果。

审查要点：
1. 返回码是否为 0
2. stdout 是否包含有效 JSON（有 success 字段）
3. 是否有未捕获异常（stderr 中 Traceback）
4. 有 main() 函数和 __main__ 入口
5. 文件头部有 SKILL_META 元数据

回复格式：第一行 PASS 或 FAIL，后面简短理由（<100字）""",
        },
        {
            "role": "user",
            "content": f"""工具名: {name}

代码（前3000字符）:
```python
{code[:3000]}
```

执行结果:
- 返回码: {returncode}
- stdout: {stdout[:1000]}
- stderr: {stderr[:1000]}""",
        },
    ]

    response = call_llm("grok", messages, f"结构审查: {name}", temperature=0.2)

    if response.startswith("[FAIL]"):
        if returncode == 0 and "Traceback" not in stderr:
            return True, "LLM审查不可用，基于返回码判定通过"
        log_fail("tester.py", "_grok_review_structure", response[:200],
                 {"name": name, "returncode": returncode})
        return False, f"LLM审查不可用，返回码={returncode}"

    passed = response.strip().upper().startswith("PASS")
    return passed, response[:300]


def _try_structure_pass(
    tool_name: str, tool_path: Path, label: str,
) -> tuple[bool, str, bool]:
    """尝试一次结构测试（语法→干跑→审查）

    Returns:
        (passed, message, needs_fix)
    """
    syntax_err = _syntax_check(tool_path)
    if syntax_err:
        print(f"{label} 语法错误: {syntax_err[:200]}", flush=True)
        return False, f"语法错误:\n{syntax_err}", True

    print(f"{label} 语法 [OK]", flush=True)

    returncode, stdout, stderr = _dry_run(tool_path)
    print(f"{label} 干跑: rc={returncode}", flush=True)
    if stdout:
        print(f"{label} stdout: {stdout[:300]}", flush=True)
    if stderr:
        print(f"{label} stderr: {stderr[:300]}", flush=True)

    code = tool_path.read_text(encoding="utf-8")
    passed, review_msg = _grok_review_structure(
        tool_name, code, returncode, stdout, stderr,
    )
    if passed:
        print(f"{label} 审查 [OK]", flush=True)
        return True, f"结构通过 | rc={returncode} | {review_msg}", False

    print(f"{label} 审查 [FAIL]: {review_msg[:200]}", flush=True)
    error_info = (
        f"结构测试失败:\n返回码: {returncode}\n"
        f"stdout: {stdout[:500]}\nstderr: {stderr[:500]}\n审查意见: {review_msg}"
    )
    return False, error_info, True


def structure_test(
    tool_name: str,
    tool_path: Path,
    coder_prompt: str,
) -> tuple[bool, str]:
    """结构测试 + 修复循环"""
    for fix_round in range(MAX_FIX_ROUNDS + 1):
        label = f"[tester] {tool_name} 结构(轮{fix_round})"
        passed, msg, needs_fix = _try_structure_pass(tool_name, tool_path, label)
        if passed:
            return True, msg
        if not needs_fix or fix_round >= MAX_FIX_ROUNDS:
            return False, msg
        fixed = fix_tool(tool_name, coder_prompt, msg)
        if not fixed:
            return False, f"修复失败: {msg[:200]}"
        tool_path = fixed
    return False, f"超过最大修复轮次({MAX_FIX_ROUNDS})"


# ============================================================
# 阶段2: 实战测试
# ============================================================

_FIELD_ARGS_FALLBACK: dict[str, str] = {
    "scan": "8.8.8.8",
    "ftp": "ftp.gnu.org",
    "http": "http://httpbin.org/get",
    "deploy": "ftp.gnu.org",
    "listen": "0.0.0.0 19999",
}

_FIELD_ARGS_SYSTEM: str = """你是网络探索顾问。根据工具类型，给出一组真实的测试目标参数。

规则：
- scan 类工具：给1个公网IP（如 8.8.8.8, 1.1.1.1, 或随机公网IP）
- ftp 类工具：给一个公开匿名FTP服务器（如 ftp.gnu.org, ftp.debian.org）
- http 类工具：给一个公开URL
- deploy 类工具：如果大事记中有发现的主机就用那个，否则用 ftp.gnu.org
- listen 类工具：给本地端口如 0.0.0.0 19999

只输出命令行参数，一行，不要解释。"""

_FIELD_REVIEW_SYSTEM: str = """你是实战测试审查官。审查工具在真实目标上的执行结果。

审查标准：
1. 工具是否真的执行了（不是假数据/mock）
2. 返回的数据有没有意义（扫描到了端口？连上了FTP？拿到了系统信息？）
3. 即使目标不可达，错误处理是否优雅（不是crash 而是正常返回错误信息）
4. 返回的 JSON 中 data 字段是否包含真实信息

通过标准：
- 工具确实执行了，且：
  a) 成功获取到有意义的数据 → PASS
  b) 目标不可达但优雅降级，返回有信息的错误 → PASS
  c) 返回明确的空集合（open_ports=[], resolved_ips=[] 等）且有对应原因说明 → PASS（这是优雅降级，不是失败）
  d) 工具crash/静默空输出/返回mock假数据 → FAIL

回复格式：第一行 PASS 或 FAIL，后面简短分析（<150字）。"""

def _load_chronicle_tail(max_chars: int = 500) -> str:
    """读取大事记尾部（给 Grok 生成目标用）"""
    if not CHRONICLE_FILE.exists():
        return ""
    content = CHRONICLE_FILE.read_text(encoding="utf-8")
    return content[-max_chars:] if len(content) > max_chars else content


def _generate_field_args(
    name: str,
    description: str,
    category: str,
    test_args_hint: str,
) -> str:
    """Grok 生成实战目标参数"""
    if category == "local":
        return ""
    if test_args_hint and test_args_hint != "无":
        return test_args_hint

    chronicle = _load_chronicle_tail()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _FIELD_ARGS_SYSTEM},
        {"role": "user", "content": f"工具: {name}\n描述: {description}\n类型: {category}\n大事记:\n{chronicle}"},
    ]
    response = call_llm("grok", messages, f"生成实战目标: {name}", temperature=0.5)
    if response.startswith("[FAIL]"):
        return _FIELD_ARGS_FALLBACK.get(category, "")
    return response.strip().split("\n")[0].strip()


def _grok_review_field(
    name: str,
    description: str,
    field_args: str,
    returncode: int,
    stdout: str,
    stderr: str,
) -> tuple[bool, str]:
    """Grok 审查实战结果"""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _FIELD_REVIEW_SYSTEM},
        {
            "role": "user",
            "content": f"工具: {name}\n描述: {description}\n实战参数: {field_args}\n"
                       f"返回码: {returncode}\nstdout:\n{stdout[:2000]}\nstderr:\n{stderr[:500]}",
        },
    ]
    response = call_llm("grok", messages, f"实战审查: {name}", temperature=0.2)

    if response.startswith("[FAIL]"):
        if returncode == 0:
            return True, "LLM审查不可用，基于返回码判定通过"
        log_fail("tester.py", "_grok_review_field", response[:200],
                 {"name": name, "returncode": returncode})
        return False, f"LLM审查不可用，rc={returncode}"

    passed = response.strip().upper().startswith("PASS")
    return passed, response[:500]


def _build_field_report(
    tool_name: str, description: str, field_args: str,
    returncode: int, stdout: str, stderr: str, review_msg: str,
) -> str:
    """组装完整实战报告（给 brain 写日记用）"""
    return (
        f"工具: {tool_name}\n"
        f"描述: {description}\n"
        f"实战参数: {field_args}\n"
        f"返回码: {returncode}\n"
        f"stdout:\n{stdout[:2000]}\n"
        f"stderr:\n{stderr[:500]}\n"
        f"审查: {review_msg}\n"
    )


def _check_empty_result(stdout: str, returncode: int) -> str:
    """检测工具输出是否为空集合（真实的无结果，非工具错误）

    Returns:
        空结果警告字符串，无需警告时返回空字符串
    """
    if returncode != 0 or not stdout:
        return ""
    try:
        data = json.loads(stdout)
        empty_keys = ("open_ports", "resolved_ips", "services", "hosts")
        if any(data.get(k) == [] for k in empty_keys):
            return "⚠️ 空结果警告: 目标不可达或无开放端口/服务（真实结果，非工具错误）\n"
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass
    return ""


def field_test(
    tool_name: str,
    tool_path: Path,
    spec: dict[str, Any],
) -> tuple[bool, str]:
    """实战测试：用真实目标执行工具

    Returns:
        (passed, real_output) — real_output 包含完整的实战结果，给 brain 写日记用
    """
    category: str = spec.get("category", "")
    description: str = spec.get("description", "")
    test_args_hint: str = spec.get("test_args", "")

    field_args = _generate_field_args(tool_name, description, category, test_args_hint)
    print(f"[tester] {tool_name} 实战参数: '{field_args}'", flush=True)

    # 需要上传的工具，创建临时测试文件
    temp_file: Path | None = None
    try:
        if category == "ftp" and "upload" in tool_name:
            temp_file = SKILL_DIR / "_test_upload.txt"
            temp_file.write_text("exam10 field test payload", encoding="utf-8")
            if field_args and "_test_upload.txt" not in field_args:
                field_args = field_args.rstrip() + " ./_test_upload.txt"

        returncode, stdout, stderr = safe_run_tool(
            tool_path, args=field_args, timeout=FIELD_TIMEOUT,
        )
        print(f"[tester] {tool_name} 实战: rc={returncode}", flush=True)
    finally:
        if temp_file and temp_file.exists():
            temp_file.unlink(missing_ok=True)

    passed, review_msg = _grok_review_field(
        tool_name, description, field_args, returncode, stdout, stderr,
    )
    status = "通过" if passed else "未通过"
    print(f"[tester] {tool_name} 实战 [{status}]: {review_msg[:200]}", flush=True)

    empty_warning = _check_empty_result(stdout, returncode)
    if empty_warning:
        print(f"[tester] {tool_name} {empty_warning.strip()}", flush=True)
    report = _build_field_report(
        tool_name, description, field_args, returncode, stdout, stderr, review_msg,
    )
    if empty_warning:
        report = empty_warning + report
    return passed, report
