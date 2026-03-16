"""skill/html_form_extractor.py - 一个简单的HTML表单提取工具

TOOL_META:
{
  "name": "html_form_extractor",
  "description": "一个简单的HTML表单提取工具，支持提取authenticity_token、隐藏字段和常见注册字段",
  "category": "其他",
  "test_target": "模拟HTML片段，预期返回包含method、action及字段的字典",
  "test_args": "--html_content '<form id=\"signup-form\" method=\"POST\" action=\"/register\" enctype=\"multipart/form-data\"><input name=\"authenticity_token\" value=\"test_token\"><input name=\"user[login]\"><input name=\"user[email]\"><input type=\"file\" name=\"avatar\"></form>'",
  "version": "3.0"
}
"""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

def extract_form_fields(html_content: str, form_id: str = "") -> dict[str, Any]:
    """Extract form fields from HTML content."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        # Fallback: if form_id not specified or not found, get first <form>
        form_match = None
        if form_id:
            form_pattern = rf'<form[^>]*id=["\']?{re.escape(form_id)}["\']?[^>]*>(.*?)</form>'
            form_match = re.search(form_pattern, html_content, re.DOTALL | re.IGNORECASE)

        if not form_match:
            # Fallback to first form tag (handles forms without id)
            first_form_pattern = r'<form[^>]*>(.*?)</form>'
            form_match = re.search(first_form_pattern, html_content, re.DOTALL | re.IGNORECASE)
            if form_match:
                form_id = "first_form"

        if not form_match:
            results["message"] = "No form found in HTML"
            return results

        form_tag = form_match.group(0)
        form_content = form_match.group(1)

        # Debug: print matched form fragment
        print(f"[DEBUG] Matched form fragment (first 200 chars): {form_tag[:200]}...")

        # Extract form attributes
        method_match = re.search(r'method=["\']([^"\']+)["\']', form_tag, re.IGNORECASE)
        action_match = re.search(r'action=["\']([^"\']*)["\']', form_tag, re.IGNORECASE)
        enctype_match = re.search(r'enctype=["\']([^"\']*)["\']', form_tag, re.IGNORECASE)

        results["data"]["method"] = method_match.group(1).upper() if method_match else "GET"
        results["data"]["action"] = action_match.group(1) if action_match else ""
        results["data"]["enctype"] = enctype_match.group(1) if enctype_match else ""
        results["data"]["form_id"] = form_id

        # Extract all input fields (including file type)
        input_pattern = r'<input[^>]*>'
        inputs = re.findall(input_pattern, form_content, re.IGNORECASE)

        fields: list[dict[str, Any]] = []
        for inp in inputs:
            name_match = re.search(r'name=["\']([^"\']+)["\']', inp)
            if not name_match:
                continue

            name = name_match.group(1)
            value_match = re.search(r'value=["\']([^"\']*)["\']', inp)
            value = value_match.group(1) if value_match else ""
            type_match = re.search(r'type=["\']([^"\']+)["\']', inp)
            input_type = type_match.group(1).lower() if type_match else "text"

            # Skip submit, button, image, reset types (but keep file, hidden, text, password, checkbox, radio)
            if input_type in ("submit", "button", "image", "reset"):
                continue

            fields.append({"name": name, "value": value, "type": input_type})

        results["data"]["fields"] = fields
        results["success"] = True
        results["message"] = f"Extracted {len(fields)} fields from form '{form_id}'"

    except re.error as e:
        results["message"] = f"Regex error: {e}"
    except Exception as e:
        results["message"] = f"Error: {e}"

    return results

def main(html_content: str, form_id: str = "") -> dict[str, Any]:
    """Extract form fields from HTML content.

    Args:
        html_content: HTML string to parse
        form_id: Form ID to extract (default: first form)

    Returns:
        Dictionary with success status, message and extracted data
    """
    return extract_form_fields(html_content, form_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract form fields from HTML")
    parser.add_argument("--html_content", required=True, help="HTML content to parse")
    parser.add_argument("--form_id", default="", help="Form ID to extract (default: first form)")

    args = parser.parse_args()
    result = main(args.html_content, args.form_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))