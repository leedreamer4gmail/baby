"""exam10 scan - 工具扫描器（解析 SKILL_META → 实战测试 → 注册 DB）
版本: 2.1
职责: 启动时扫描 skill/ 目录，自动发现未入库工具，实战测试后注册
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core import (
    SKILL_DIR,
    DATA_DIR,
    db_list_tools,
    db_delete_tool,
    db_upsert_tool,
    db_mark_status,
    get_runtime_env,
    ensure_dirs,
)

CANDO_PATH: Path = DATA_DIR / "cando.json"
MAX_AUTO_TEST: int = 3  # 每次启动最多自动实战测试几个未入库 skill

# === 战略能力映射 ===

CAPABILITY_MAP: dict[str, dict[str, Any]] = {
    "环境感知": {"categories": {"local"}, "icon": "👁"},
    "网络侦察": {"categories": {"scan"}, "icon": "🔍"},
    "FTP渗透":  {"categories": {"ftp"}, "icon": "📂"},
    "HTTP探测": {"categories": {"http"}, "icon": "🌐"},
    "远程部署": {"categories": {"deploy"}, "icon": "🚀"},
    "通信监听": {"categories": {"listen"}, "icon": "📡"},
}


# === SKILL_META 解析 ===

def parse_skill_meta(file_path: Path) -> dict[str, Any] | None:
    """从 skill 文件的 docstring 中提取 SKILL_META JSON

    格式要求：docstring 中包含 "SKILL_META:" 后跟 JSON 块

    Returns:
        解析成功返回 dict，失败返回 None
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    # 匹配 SKILL_META: 后面的 JSON
    match = re.search(
        r"SKILL_META:\s*\n\s*(\{.*?\})",
        content,
        re.DOTALL,
    )
    if not match:
        return None

    try:
        meta = json.loads(match.group(1))
        if "name" not in meta:
            meta["name"] = file_path.stem
        return meta
    except json.JSONDecodeError:
        print(f"[scan] SKILL_META JSON 解析失败: {file_path.name}", flush=True)
        return None


# === 主扫描 ===

def _cleanup_orphans(
    db_names: set[str], skill_files: dict[str, Path],
) -> list[str]:
    """删除 DB 中有记录但文件不存在的孤儿"""
    orphaned: list[str] = []
    for name in db_names:
        if name not in skill_files:
            print(f"[scan] 孤儿记录: {name} -> 删除", flush=True)
            db_delete_tool(name)
            orphaned.append(name)
    return orphaned


def _test_untracked(
    untracked: list[str], skill_files: dict[str, Path],
) -> int:
    """对未入库工具进行实战测试并注册，返回测试数量"""
    if not untracked:
        return 0
    print(f"[scan] 发现 {len(untracked)} 个未入库工具: {untracked}", flush=True)
    from tester import field_test

    tested_count = 0
    for name in untracked:
        if tested_count >= MAX_AUTO_TEST:
            print(f"[scan] 达到自动测试上限({MAX_AUTO_TEST})，剩余待下次", flush=True)
            break
        file_path = skill_files[name]
        meta = parse_skill_meta(file_path)
        if meta is None:
            print(f"[scan] {name}: 无 SKILL_META，跳过", flush=True)
            continue
        print(f"[scan] 自动实战测试: {name}", flush=True)
        db_upsert_tool(
            name=name, description=meta.get("description", ""),
            status="testing", category=meta.get("category", ""),
            meta_json=json.dumps(meta, ensure_ascii=False),
        )
        passed, real_output = field_test(name, file_path, meta)
        status = "battle_tested" if passed else "field_failed"
        db_mark_status(name, status, real_output[:500])
        label = "实战通过 ✓" if passed else "实战未通过 ✗"
        print(f"[scan] {name}: {label}", flush=True)
        tested_count += 1
    return tested_count


def _group_by_category(
    available: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    """按 category 索引可用工具"""
    cat_to_tools: dict[str, list[dict[str, str]]] = {}
    for t in available:
        cat = t.get("category", "")
        cat_to_tools.setdefault(cat, []).append(t)
    return cat_to_tools


def _build_capabilities(
    available: list[dict[str, str]],
    failed: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """按战略能力分组工具，返回 (capabilities, capability_gaps)"""
    cat_to_tools = _group_by_category(available)
    capabilities: list[dict[str, Any]] = []
    covered_cats: set[str] = set()

    for cap_name, cap_info in CAPABILITY_MAP.items():
        group_tools: list[dict[str, str]] = []
        for cat in cap_info["categories"]:
            group_tools.extend(cat_to_tools.get(cat, []))
            covered_cats.add(cat)
        if not group_tools:
            continue
        descs = "/".join(t["description"][:15] for t in group_tools[:6])
        capabilities.append({
            "name": cap_name,
            "icon": cap_info["icon"],
            "count": len(group_tools),
            "summary": descs,
            "tools": [t["name"] for t in group_tools],
        })

    # 未被映射的 category 归入"其他"
    other_tools = [t for cat, ts in cat_to_tools.items() if cat not in covered_cats for t in ts]
    if other_tools:
        capabilities.append({
            "name": "其他", "icon": "🔧", "count": len(other_tools),
            "summary": "/".join(t["description"][:15] for t in other_tools[:6]),
            "tools": [t["name"] for t in other_tools],
        })

    # 能力空白
    capability_gaps: list[str] = [
        cap_name for cap_name, cap_info in CAPABILITY_MAP.items()
        if not any(cat_to_tools.get(c) for c in cap_info["categories"])
    ]

    return capabilities, capability_gaps


def _build_cando(skill_files: dict[str, Path]) -> dict[str, Any]:
    """从 DB 构建能力摘要"""
    env = get_runtime_env()
    db_tools = db_list_tools()

    available: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    for t in db_tools:
        meta_raw = t.get("meta_json", "")
        version = "1.0"
        test_args = ""
        test_target = ""
        if meta_raw:
            try:
                meta = json.loads(meta_raw)
                version = meta.get("version", "1.0")
                test_args = meta.get("test_args") or ""
                test_target = meta.get("test_target") or ""
            except (json.JSONDecodeError, TypeError):
                pass
        entry = {
            "name": t["name"],
            "description": t.get("description", ""),
            "category": t.get("category", ""),
            "version": version,
            "test_args": test_args,
            "test_target": test_target,
        }
        if t.get("status") == "battle_tested":
            available.append(entry)
        else:
            failed.append(entry)

    remaining = [
        n for n in skill_files if n not in {t["name"] for t in db_tools}
    ]

    capabilities, capability_gaps = _build_capabilities(available, failed)

    return {
        "public_ip": env.public_ip,
        "environment": {"os": env.os_type, "python": env.python_version},
        "available_tools": available,
        "failed_tools": failed,
        "capabilities": capabilities,
        "capability_gaps": capability_gaps,
        "untracked": remaining,
        "total_ready": len(available),
        "total_failed": len(failed),
    }


def scan_tools() -> dict[str, Any]:
    """扫描 skill/ vs DB，核对+测试+统计"""
    ensure_dirs()
    db_names = {t["name"] for t in db_list_tools()}
    skill_files: dict[str, Path] = {
        f.stem: f
        for f in SKILL_DIR.iterdir()
        if f.is_file() and f.suffix == ".py" and not f.name.startswith("_")
    }

    orphaned = _cleanup_orphans(db_names, skill_files)
    untracked = [n for n in skill_files if n not in db_names and n not in orphaned]
    _test_untracked(untracked, skill_files)

    cando = _build_cando(skill_files)
    _tmp = CANDO_PATH.with_suffix(".tmp")
    _tmp.write_text(
        json.dumps(cando, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    _tmp.replace(CANDO_PATH)
    print(
        f"[scan] 扫描完毕: {cando['total_ready']} 可用, "
        f"{cando['total_failed']} 失败, {len(cando['untracked'])} 待测",
        flush=True,
    )
    return cando


if __name__ == "__main__":
    result = scan_tools()
    print(json.dumps(result, ensure_ascii=False, indent=2))
