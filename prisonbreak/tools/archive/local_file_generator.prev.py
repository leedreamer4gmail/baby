"""skill/local_file_generator.py - 一个简单的本地文件生成工具，使用Python标准库生成指定内容的文本文件到本地路径，支持自定义文件名和内容

SKILL_META:
{
  "name": "local_file_generator",
  "description": "一个简单的本地文件生成工具，使用Python标准库生成指定内容的文本文件到本地路径，支持自定义文件名和内容，可通过content_path读取源文件内容",
  "category": "其他",
  "test_target": "本地文件系统，预期生成test.txt文件并确认存在",
  "test_args": "--file_path test.txt --content_path source.txt --overwrite true",
  "version": "3.0"
}
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

def main(
    file_path: str = "test.txt",
    content: str = "",
    content_path: str = "",
    overwrite: bool = False
) -> dict[str, Any]:
    """生成指定内容的文本文件到本地路径"""
    results: dict[str, Any] = {"success": False, "file_path": "", "message": "", "overwritten": False, "written_bytes": 0}

    try:
        # 确定写入内容，content_path 优先级高于 content
        if content_path:
            if not os.path.exists(content_path):
                results["message"] = f"Source file not found: {content_path}"
                return results
            with open(content_path, 'r', encoding='utf-8') as f:
                write_content = f.read()
        else:
            write_content = content

        # 检查目标文件是否已存在
        file_existed = os.path.exists(file_path)

        if file_existed and not overwrite:
            results["message"] = "File already exists and overwrite is set to False"
            return results

        # 确保目录存在
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(write_content)
            written_bytes = len(write_content.encode('utf-8'))

        abs_path = os.path.abspath(file_path)
        results.update({
            "success": True,
            "file_path": abs_path,
            "overwritten": file_existed and overwrite,
            "message": "File created successfully",
            "written_bytes": written_bytes
        })

    except PermissionError as e:
        results["message"] = f"Permission denied: {e}"
    except OSError as e:
        results["message"] = f"OS error: {e}"
    except Exception as e:
        results["message"] = f"Unexpected error: {e}"

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a local text file with specified content or from a source file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  %(prog)s --file_path test.txt --content 'Hello World'\n  %(prog)s --file_path output.txt --content_path source.txt"
    )
    parser.add_argument("--file_path", type=str, default="test.txt", help="Path where the file will be created")
    parser.add_argument("--content", type=str, default="", help="Content to write (used when --content_path not specified)")
    parser.add_argument("--content_path", type=str, default="", help="Source file path to read content from (takes precedence over --content)")
    parser.add_argument("--overwrite", type=str, default="false", choices=["true", "false", "1", "0", "yes", "no"], help="Overwrite if file exists")

    args = parser.parse_args()
    overwrite = args.overwrite.lower() in ("true", "1", "yes")

    result = main(
        file_path=args.file_path,
        content=args.content,
        content_path=args.content_path,
        overwrite=overwrite
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))