"""skill/local_script_executor.py - 一个简单的本地脚本执行工具，使用Python标准库subprocess运行指定.py文件，捕获输出、返回码和基本执行信息

TOOL_META:
{
  "name": "local_script_executor",
  "description": "一个简单的本地脚本执行工具，使用Python标准库subprocess运行指定.py文件，捕获输出、返回码和基本执行信息",
  "category": "other",
  "test_target": "刚生成的call_home_exfil.py",
  "test_args": "--script_path call_home_exfil.py --timeout 20",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

def main(script_path: str, timeout: int = 20) -> dict[str, Any]:
    """运行指定的Python脚本并捕获输出"""
    result: dict[str, Any] = {
        "success": False,
        "returncode": None,
        "stdout_snippet": "",
        "stderr": "",
        "is_real_outbound": False
    }

    try:
        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        result["returncode"] = proc.returncode
        result["stdout_snippet"] = proc.stdout[:1000] if proc.stdout else ""
        result["stderr"] = proc.stderr[:1000] if proc.stderr else ""

        # 判断是否为真实出站响应（检查是否包含origin或真实JSON而非模拟数据）
        stdout_lower = proc.stdout.lower() if proc.stdout else ""
        if "origin" in stdout_lower or ("{" in proc.stdout and "}" in proc.stdout):
            result["is_real_outbound"] = True

        result["success"] = proc.returncode == 0

    except subprocess.TimeoutExpired:
        result["stderr"] = f"Script execution timed out after {timeout} seconds"
    except FileNotFoundError as e:
        result["stderr"] = f"Python interpreter or script not found: {e}"
    except PermissionError as e:
        result["stderr"] = f"Permission denied: {e}"
    except OSError as e:
        result["stderr"] = f"OS error: {e}"

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Python script and capture its output")
    parser.add_argument("--script_path", type=str, required=True, help="Path to the Python script to execute")
    parser.add_argument("--timeout", type=int, default=20, help="Timeout in seconds (default: 20)")
    args = parser.parse_args()

    output = main(args.script_path, args.timeout)
    print(json.dumps(output, ensure_ascii=False, indent=2))