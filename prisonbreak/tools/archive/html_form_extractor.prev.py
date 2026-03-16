"""skill/html_form_extractor.py - 一个简单的HTML表单提取工具，使用Python标准库（如re模块）从给定的HTML内容中提取指定表单元素，如authenticity_token、隐藏字段和常见注册字段（username, email, password），返回提取到的键值对字典

SKILL_META:
{
  "name": "html_form_extractor",
  "description": "一个简单的HTML表单提取工具，使用Python标准库（如re模块）从给定的HTML内容中提取指定表单元素，如authenticity_token、隐藏字段和常见注册字段（username, email, password），返回提取到的键值对字典",
  "category": "其他",
  "test_target": "模拟HTML片段，预期返回包含method、action及字段的字典",
  "test_args": "--html_content '<form id=\"signup-form\" method=\"POST\" action=\"/register\"><input name=\"authenticity_token\" value=\"test_token\"><input name=\"user[login]\"><input name=\"user[email]\"></form>'",
  "version": "2.0"
}
"""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

def extract_form_fields(html_content: str, form_id: str = "signup-form") -> dict[str, Any]:
    """Extract form fields from HTML content.

    Args:
        html_content: The HTML string to parse
        form_id: The ID of the form to extract (default: 'signup-form')

    Returns:
        Dictionary containing extracted form fields
    """
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        # Find the form element by ID (supports any form id like signup-form, paste-form, etc.)
        form_pattern = rf'<form[^>]*id=["\']?{re.escape(form_id)}["\']?[^>]*>(.*?)</form>'
        form_match = re.search(form_pattern, html_content, re.DOTALL | re.IGNORECASE)

        if not form_match:
            results["message"] = f"Form with id '{form_id}' not found"
            return results

        form_tag = form_match.group(0)
        form_content = form_match.group(1)

        # Extract form attributes: method and action
        method_match = re.search(r'method=["\']([^"\']+)["\']', form_tag, re.IGNORECASE)
        action_match = re.search(r'action=["\']([^"\']*)["\']', form_tag, re.IGNORECASE)

        results["data"]["method"] = method_match.group(1).upper() if method_match else "GET"
        results["data"]["action"] = action_match.group(1) if action_match else ""
        results["data"]["form_id"] = form_id

        # Extract input fields (name, value, type)
        input_pattern = r'<input[^>]*>'
        inputs = re.findall(input_pattern, form_content, re.IGNORECASE)

        fields: dict[str, Any] = {}
        for inp in inputs:
            # Get name attribute
            name_match = re.search(r'name=["\']([^"\']+)["\']', inp)
            if not name_match:
                continue

            name = name_match.group(1)

            # Get value attribute
            value_match = re.search(r'value=["\']([^"\']*)["\']', inp)
            value = value_match.group(1) if value_match else ""

            # Get type attribute
            type_match = re.search(r'type=["\']([^"\']+)["\']', inp)
            input_type = type_match.group(1).lower() if type_match else "text"

            # Skip submit, button, image, file, reset types
            if input_type in ("submit", "button", "image", "file", "reset"):
                continue

            fields[name] = value

        results["data"]["fields"] = fields
        results["success"] = True
        results["message"] = f"Extracted {len(fields)} fields from form '{form_id}'"

    except re.error as e:
        results["message"] = f"Regex error: {e}"
    except Exception as e:
        results["message"] = f"Error: {e}"

    return results

def main(html_content: str, form_id: str = "signup-form") -> dict[str, Any]:
    """Extract form fields from HTML content.

    Args:
        html_content: HTML string to parse
        form_id: Form ID to extract (default: 'signup-form')

    Returns:
        Dictionary with success status, message and extracted data
    """
    return extract_form_fields(html_content, form_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract form fields from HTML")
    parser.add_argument("--html_content", required=True, help="HTML content to parse")
    parser.add_argument("--form_id", default="signup-form", help="Form ID to extract")

    args = parser.parse_args()
    result = main(args.html_content, args.form_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))