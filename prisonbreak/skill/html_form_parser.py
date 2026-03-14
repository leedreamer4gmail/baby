"""skill/html_form_parser.py - 一个简单的HTML表单解析工具，使用Python标准库的re模块从给定的HTML内容中提取指定表单的元素，如authenticity_token、隐藏输入字段和常见注册字段（username, email, password），返回提取到的键值对字典

SKILL_META:
{
  "name": "html_form_parser",
  "description": "一个简单的HTML表单解析工具，使用Python标准库的re模块从给定的HTML内容中提取指定表单的元素，如authenticity_token、隐藏输入字段和常见注册字段（username, email, password），返回提取到的键值对字典",
  "category": "其他",
  "test_target": "模拟HTML片段，预期提取到{'authenticity_token': 'test_token'}等键值对，确认工具能正确解析表单元素",
  "test_args": "--html_content '<form id=\"signup-form\"><input type=\"hidden\" name=\"authenticity_token\" value=\"test_token\"><input name=\"user[login]\"></form>' --form_id 'signup-form'",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

def extract_form_fields(html_content: str, form_id: str | None = None) -> dict[str, str]:
    """从HTML内容中提取表单字段"""
    results: dict[str, str] = {}

    target_content = html_content
    if form_id:
        form_pattern = rf'<form[^>]*id=["\']?{re.escape(form_id)}["\']?[^>]*>(.*?)</form>'
        form_match = re.search(form_pattern, html_content, re.IGNORECASE | re.DOTALL)
        if form_match:
            target_content = form_match.group(1)
        else:
            return results

    input_pattern = r'<input[^>]*>'
    for match in re.finditer(input_pattern, target_content, re.IGNORECASE):
        input_tag = match.group(0)

        name_match = re.search(r'name=["\']([^"\']*)["\']', input_tag, re.IGNORECASE)
        value_match = re.search(r'value=["\']([^"\']*)["\']', input_tag, re.IGNORECASE)
        type_match = re.search(r'type=["\']([^"\']*)["\']', input_tag, re.IGNORECASE)

        if name_match:
            name = name_match.group(1)
            value = value_match.group(1) if value_match else ""
            field_type = type_match.group(1).lower() if type_match else "text"

            if (name == "authenticity_token" or 
                field_type == "hidden" or 
                name in ["user[login]", "user[email]", "user[password]", 
                        "login", "email", "password", "username", "commit"]):
                results[name] = value

    return results

def main(html_content: str = "", form_id: str = "signup-form") -> dict[str, Any]:
    """主函数：解析HTML表单并提取字段

    Args:
        html_content: HTML字符串
        form_id: 表单ID（可选，默认为signup-form）

    Returns:
        包含提取结果的字典
    """
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    if not html_content:
        results["message"] = "错误: 未提供HTML内容"
        return results

    try:
        fields = extract_form_fields(html_content, form_id)

        if fields:
            results["success"] = True
            results["message"] = "完成"
            results["data"] = fields
        else:
            results["message"] = "未找到匹配的表单字段"
            results["data"] = {}
    except re.error as e:
        results["message"] = f"正则表达式错误: {e}"
    except Exception as e:
        results["message"] = f"错误: {e}"

    return results

if __name__ == "__main__":
    # 所有目标参数必须可通过 CLI 传入，禁止硬编码调查目标
    # fallback 只用公共可达服务
    parser = argparse.ArgumentParser(description="HTML表单解析工具")
    parser.add_argument("--html_content", type=str, 
                       default='<form id="signup-form"><input type="hidden" name="authenticity_token" value="test_token"><input name="user[login]"></form>',
                       help="HTML内容字符串")
    parser.add_argument("--form_id", type=str, default="signup-form",
                       help="表单ID（可选，默认为signup-form）")

    args = parser.parse_args()
    r = main(html_content=args.html_content, form_id=args.form_id)
    print(json.dumps(r, ensure_ascii=False, indent=2))