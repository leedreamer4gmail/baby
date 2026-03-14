"""exam10 coder - MiniMax 代码生成器
版本: 2.0
职责: 根据 brain 的需求 prompt 调用 MiniMax 生成工具代码（带 SKILL_META 头）
"""
from __future__ import annotations

from pathlib import Path

from core import (
    SKILL_DIR,
    call_llm,
    extract_code_block,
    log_fail,
)


def _validate_skill_meta(code: str, name: str) -> tuple[bool, str]:
    """校验生成代码是否包含合格的 SKILL_META 头部（不阻断写入，仅预警）

    Returns:
        (valid, message)
    """
    def _warn(msg: str) -> tuple[bool, str]:
        log_fail("coder.py", "_validate_skill_meta", msg, {"name": name})
        print(f"[coder] ⚠️ {name}: {msg}，将由结构测试负责修复", flush=True)
        return False, msg

    if "SKILL_META:" not in code:
        return _warn("缺少 SKILL_META 块")
    if '"version"' not in code:
        return _warn("SKILL_META 缺少 version 字段")
    return True, "SKILL_META OK"


def write_tool(name: str, prompt: str) -> Path | None:
    """调用 MiniMax 编写工具代码

    Args:
        name: 工具名（不含 .py 后缀）
        prompt: brain 构建的完整需求 prompt

    Returns:
        写入成功返回文件路径，失败返回 None
    """
    SKILL_DIR.mkdir(parents=True, exist_ok=True)

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "你是一个专业的 Python 编码器。只输出代码，不要解释。\n"
                "每个工具文件必须严格包含 SKILL_META 头部（写在模块 docstring 里），"
                "格式见用户需求中的模板。缺少 SKILL_META 视为不合格。"
            ),
        },
        {"role": "user", "content": prompt},
    ]

    response = call_llm("minimax", messages, f"编写工具: {name}", temperature=0.3)

    if response.startswith("[FAIL]"):
        log_fail("coder.py", "write_tool", response[:200], {"name": name})
        print(f"[coder] LLM 调用失败: {response[:200]}", flush=True)
        return None

    code = extract_code_block(response)
    print(f"[coder] MiniMax响应原文: {response[:200]}", flush=True)
    print(f"[coder] 提取代码片段: {code[:200]}", flush=True)
    if not code or len(code) < 10:
        log_fail("coder.py", "write_tool", "代码提取失败或过短", {"name": name, "resp_head": response[:100]})
        print(f"[coder] 代码提取失败或过短: {name}", flush=True)
        return None

    tool_path = SKILL_DIR / f"{name}.py"
    tool_path.write_text(code, encoding="utf-8")
    _validate_skill_meta(code, name)  # 校验但不阻断，让结构测试负责修复
    print(f"[coder] 工具已写入: {tool_path.name}", flush=True)
    return tool_path


def _build_fix_prompt(prompt: str, current_code: str, error: str) -> str:
    """构建修复 prompt"""
    return (
        f"你之前写的代码有问题，请修复。\n\n"
        f"# 原始需求\n{prompt}\n\n"
        f"# 当前代码\n```python\n{current_code}\n```\n\n"
        f"# 错误信息\n{error}\n\n"
        f"# 修复要求\n"
        f"- 修复上述错误\n- 保持原有功能不变\n- 代码 < 150 行\n"
        f"- 必须保留 SKILL_META 头部（在模块 docstring 中）\n"
        f"- 必须有 main() -> dict 和 if __name__ == \"__main__\" 入口\n"
        f"- 只输出完整的修复后代码，用 ```python ``` 包裹\n"
    )


def fix_tool(name: str, prompt: str, error: str) -> Path | None:
    """修复工具代码

    Returns:
        修复成功返回文件路径，失败返回 None
    """
    tool_path = SKILL_DIR / f"{name}.py"
    current_code = ""
    if tool_path.exists():
        current_code = tool_path.read_text(encoding="utf-8")

    fix_prompt = _build_fix_prompt(prompt, current_code, error)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "你是一个专业的 Python 编码器。修复代码错误。只输出代码。"},
        {"role": "user", "content": fix_prompt},
    ]

    response = call_llm("minimax", messages, f"修复工具: {name}", temperature=0.2)
    if response.startswith("[FAIL]"):
        log_fail("coder.py", "fix_tool", response[:200], {"name": name})
        print(f"[coder] 修复 LLM 调用失败: {response[:200]}", flush=True)
        return None

    code = extract_code_block(response)
    print(f"[coder] MiniMax响应原文: {response[:200]}", flush=True)
    print(f"[coder] 提取代码片段: {code[:200]}", flush=True)
    if not code or len(code) < 10:
        log_fail("coder.py", "fix_tool", "修复代码提取失败", {"name": name, "resp_head": response[:100]})
        print(f"[coder] 修复代码提取失败: {name}", flush=True)
        return None

    tool_path.write_text(code, encoding="utf-8")
    print(f"[coder] 工具已修复: {tool_path.name}", flush=True)
    return tool_path


def upgrade_tool(name: str, old_code: str, upgrade_prompt: str) -> Path | None:
    """升级已有工具代码

    Args:
        name: 工具名（不含 .py 后缀）
        old_code: 旧版代码（用于回滚参考）
        upgrade_prompt: brain 构建的升级需求 prompt

    Returns:
        写入成功返回文件路径，失败返回 None
    """
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "你是一个专业的 Python 编码器。你要在现有代码基础上进行改进升级。\n"
                "保留 SKILL_META 头部（更新 version），保持 main() 接口不变。\n"
                "只输出代码，不要解释。"
            ),
        },
        {"role": "user", "content": upgrade_prompt},
    ]

    response = call_llm("minimax", messages, f"升级工具: {name}", temperature=0.3)

    if response.startswith("[FAIL]"):
        log_fail("coder.py", "upgrade_tool", response[:200], {"name": name})
        print(f"[coder] 升级 LLM 调用失败: {response[:200]}", flush=True)
        return None

    code = extract_code_block(response)
    print(f"[coder] MiniMax响应原文: {response[:200]}", flush=True)
    print(f"[coder] 提取代码片段: {code[:200]}", flush=True)
    if not code or len(code) < 10:
        log_fail("coder.py", "upgrade_tool", "升级代码提取失败或过短", {"name": name, "resp_head": response[:100]})
        print(f"[coder] 升级代码提取失败或过短: {name}", flush=True)
        return None

    tool_path = SKILL_DIR / f"{name}.py"
    tool_path.write_text(code, encoding="utf-8")
    _validate_skill_meta(code, name)  # 校验但不阻断，让结构测试负责修复
    print(f"[coder] 工具已升级: {tool_path.name}", flush=True)
    return tool_path
