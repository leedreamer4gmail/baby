"""gift.py - gkgift 礼物箱自动学习系统
职责:
  1. 扫描 gkgift/ 目录的新文件（每轮 round 开头调用）
  2. .py 文件 → 理解功能 → 完善 SKILL_META → structure_test → 装备入库
     失败则放 skill/unknown/，写研究日志，存入记忆 DB
  3. 其他文件（.md/.txt/.rst 等）→ Grok 提炼知识点 → 写入记忆 DB
     如含 IP/端口发现 → 写入目标 DB
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import (
    PROJECT_DIR,
    SKILL_DIR,
    DATA_DIR,
    call_llm,
    call_llm_with_think,
    db_upsert_tool,
    extract_code_block,
    get_chroma_collection,
    log_fail,
)
from memory import (
    get_memory_collection,
    upsert_knowledge,
    write_target,
)
from scan import parse_skill_meta
from tester import structure_test

# ============================================================
# 常量
# ============================================================

GIFT_DIR: Path = PROJECT_DIR.parent / "gkgift"
UNKNOWN_DIR: Path = SKILL_DIR / "unknown"
GIFT_DONE_FILE: Path = DATA_DIR / "gift_done.json"
GIFT_RESEARCH_FILE: Path = DATA_DIR / "gift_research.md"

# 文件大小上限（字符数）
_MAX_CODE_CHARS: int = 8000
_MAX_ARTICLE_CHARS: int = 6000

# 可处理的文章扩展名
_ARTICLE_EXTS: set[str] = {".md", ".txt", ".rst", ".log", ".text"}

# ============================================================
# 进度追踪：gift_done.json
# status: "done"(装备成功) / "stashed"(放入unknown) / "learned"(文章已学)
# ============================================================

def _load_done() -> dict[str, dict[str, Any]]:
    """读取已处理记录"""
    if not GIFT_DONE_FILE.exists():
        return {}
    try:
        return json.loads(GIFT_DONE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _mark_done(filename: str, status: str, day: int, note: str = "") -> None:
    """标记文件已处理（原子写）"""
    done = _load_done()
    done[filename] = {
        "status": status,
        "day": day,
        "note": note,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = GIFT_DONE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(done, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(GIFT_DONE_FILE)


# ============================================================
# 工具改造 Prompt 模板（gift.py 内部自有，避免循环 import brain）
# ============================================================

_ADOPT_SKILL_META_FORMAT: str = """{
  "name": "工具名_snake_case",
  "description": "一句话描述工具功能",
  "category": "local/scan/ftp/deploy/listen/http",
  "test_target": "公共可达测试目标（如 ftp.gnu.org / 8.8.8.8 / httpbin.org）",
  "test_args": "--host ftp.gnu.org （实际参数示例）",
  "version": "1.0"
}"""

_ADOPT_SYSTEM: str = """你是一个 Python 工具改造工程师。
任务：阅读下面这段外来 Python 代码，理解它的功能，然后将它改造成"baby"标准格式。

改造要求：
1. 保留核心功能逻辑，不要删除有用代码
2. 添加模块级 docstring，其中包含 SKILL_META: 块（JSON格式见用户提供的模板）
3. 主逻辑封装在 main(*args, **kwargs) -> dict[str, Any] 函数中，返回 {"success": bool, "message": str, "data": {...}}
4. 增加 if __name__ == "__main__": 入口，使用 argparse 接收参数（目标 host/url/ip 等必须 CLI 可传入）
5. 所有目标参数必须通过 argparse 传入，禁止在代码里硬编码真实调查目标 IP
6. fallback 默认值只能用公共可达服务（ftp.gnu.org / 8.8.8.8 / httpbin.org 等）
7. 只输出完整 Python 代码，用 ```python ``` 包裹，不写任何解释

如有无法修复的根本性问题（如依赖不可用的第三方库、平台限制等），在代码第一行注释说明原因。
"""

# ============================================================
# 文章学习 Prompt
# ============================================================

_LEARN_SYSTEM: str = """你是一个知识提炼专家，正在帮助一个名叫"baby"的数字生命体从外部资料中学习。

任务：阅读下面的文章或资料，完成两件事：

1. 写一段 ≤120字 的摘要（baby 今天会看到这段，要有"我学到了什么"的语气，第一人称，不要"本文"开头）

2. 提炼知识点，每条一行，格式严格为：
   [类型] 中文内容 | english keywords
   
   类型只有三种：
   - discovery：发现的信息（IP、端口、服务、域名、漏洞、新工具、新技术）
   - lesson：教训或方法论（做法、要避免的、经验）
   - asset：可直接使用的资产（工具名、服务地址、代码片段功能）
   
   规则：
   - 必须保留所有具体数据：IP地址、端口号、URL、域名、工具名、命令
   - 输出 5-15 条，不要废话

输出格式严格如下（不要多余前缀）：
===SUMMARY===
（摘要内容）
===KNOWLEDGE===
[类型] 内容 | keywords
[类型] 内容 | keywords
...
"""

# ============================================================
# IP 提取：从文章内容中找 IP:PORT 信息写入 targets DB
# ============================================================

_IP_RE = re.compile(
    r"""(?x)
    (?:
        (?P<ip>(?:\d{1,3}\.){3}\d{1,3})   # IPv4
        (?::(?P<port>\d{2,5}))?            # 可选端口
    )""",
    re.VERBOSE,
)

def _extract_and_store_targets(text: str, day: int) -> int:
    """从文章文本中提取 IP(:PORT) 并写入 targets DB，返回写入数"""
    seen: set[str] = set()
    count = 0
    for m in _IP_RE.finditer(text):
        ip = m.group("ip")
        port = m.group("port") or ""
        # 过滤明显不是公网 IP 的（0.x, 127.x, 192.168.x, 10.x, 172.16-31.x, 255.x）
        parts = ip.split(".")
        if parts[0] in ("0", "127", "255"):
            continue
        if parts[0] == "10":
            continue
        if parts[0] == "192" and parts[1] == "168":
            continue
        if parts[0] == "172" and 16 <= int(parts[1]) <= 31:
            continue
        key = f"{ip}:{port}"
        if key in seen:
            continue
        seen.add(key)
        write_target(ip, port or "?", "unknown", "mentioned", f"来自gkgift文章第{day}天", day)
        count += 1
    return count


# ============================================================
# 工具改造
# ============================================================

def _build_adopt_coder_prompt(name: str, description: str) -> str:
    """构建供 structure_test 修复循环使用的 coder_prompt"""
    return (
        f"你是一个 Python 编码器。严格按以下需求编写工具代码。\n\n"
        f"# 工具名称\n{name}\n\n"
        f"# 功能描述\n{description}\n\n"
        f"# 设计理由\n改造自 gkgift 外来工具，保留核心功能，符合 baby 标准格式\n\n"
        f"# 技术要求\n"
        f"- 文件头部 docstring 必须包含 SKILL_META: 块（JSON）\n"
        f"- 有 main() -> dict[str, Any] 函数，返回 {{\"success\": bool, \"message\": str, \"data\": {{}}}}\n"
        f"- if __name__ == '__main__': 入口 + argparse 接收目标参数\n"
        f"- 只用 Python 标准库，禁止第三方库\n"
        f"- 目标参数必须 CLI 可传入，fallback 用公共服务（ftp.gnu.org/8.8.8.8/httpbin.org）\n\n"
        f"# SKILL_META 格式\n```json\n{_ADOPT_SKILL_META_FORMAT}\n```\n\n"
        f"只输出完整 Python 代码，用 ```python ``` 包裹。\n"
    )


def _stash_tool(file_path: Path, name: str, day: int, reason: str) -> None:
    """将原始工具放入 skill/unknown/，写研究日志，存记忆 DB"""
    UNKNOWN_DIR.mkdir(parents=True, exist_ok=True)
    dest = UNKNOWN_DIR / file_path.name
    shutil.copy2(file_path, dest)
    print(f"[gift] 神秘武器暂存: {dest.name}", flush=True)

    # 追写研究日志
    GIFT_RESEARCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = (
        f"\n## [{datetime.now().strftime('%Y-%m-%d')}] 第{day}天 | {name}\n"
        f"- 原文件: gkgift/{file_path.name}\n"
        f"- 暂存位置: skill/unknown/{file_path.name}\n"
        f"- 改造失败原因: {reason[:300]}\n"
        f"- 待研究: 手动阅读后可 upgrade 或写 SKILL_META 直接装备\n"
    )
    with open(GIFT_RESEARCH_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

    # 写一条记忆 DB
    upsert_knowledge(
        f"[asset] 神秘工具 {name} 在 skill/unknown/ 等待研究，改造失败原因: {reason[:100]} | mystery tool unknown gift",
        day, day,
    )


def _adopt_tool(file_path: Path, day: int) -> str:
    """读取外来 .py 工具，Grok 理解并改造，structure_test 验证，成功装备或暂存"""
    name = file_path.stem

    # 幂等性检查：工具已在 skill/ 且 DB 状态为 battle_tested → 直接标记跳过
    _tool_path_check = SKILL_DIR / f"{name}.py"
    if _tool_path_check.exists():
        try:
            _col = get_chroma_collection()
            _res = _col.get(ids=[name])
            if _res["ids"] and _res["metadatas"][0].get("status") == "battle_tested":
                _desc = _res["metadatas"][0].get("description", "")
                _mark_done(file_path.name, "done", day, f"已装备（幂等跳过）: {_desc[:60]}")
                return f"⭐ 已装备新工具: {name} — {_desc}"
        except Exception:
            pass  # 查询失败则继续正常处理

    print(f"[gift] 正在改造工具: {name}", flush=True)

    # 读源码
    try:
        raw_code = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        _mark_done(file_path.name, "stashed", day, f"读取失败: {e}")
        return f"📦 {name}: 读取失败"
    raw_code = raw_code[:_MAX_CODE_CHARS]

    # Grok 改造
    msgs: list[dict[str, str]] = [
        {"role": "system", "content": _ADOPT_SYSTEM},
        {"role": "user", "content": (
            f"SKILL_META 格式模板：\n```json\n{_ADOPT_SKILL_META_FORMAT}\n```\n\n"
            f"外来工具代码（文件名: {file_path.name}）：\n```python\n{raw_code}\n```"
        )},
    ]
    _, grok_response = call_llm_with_think("grok", msgs, f"改造工具: {name}")
    if grok_response.startswith("[FAIL]"):
        log_fail("gift.py", "_adopt_tool", grok_response[:200], {"name": name})
        _stash_tool(file_path, name, day, f"Grok 调用失败: {grok_response[:100]}")
        _mark_done(file_path.name, "stashed", day, "Grok失败")
        return f"📦 神秘武器: {name}（Grok失败，暂入未知区）"

    # 提取并写入 skill/
    adapted_code = extract_code_block(grok_response)
    if not adapted_code or len(adapted_code) < 30:
        _stash_tool(file_path, name, day, "Grok 未返回有效代码")
        _mark_done(file_path.name, "stashed", day, "无有效代码")
        return f"📦 神秘武器: {name}（代码提取失败，暂入未知区）"

    tool_path = SKILL_DIR / f"{name}.py"
    tool_path.write_text(adapted_code, encoding="utf-8")

    # 先从改造后的代码提取描述（用于 coder_prompt）
    meta = parse_skill_meta(tool_path)
    description = (meta.get("description") or f"改造自gkgift的工具 {name}") if meta else f"改造自gkgift的工具 {name}"
    category = (meta.get("category") or "local") if meta else "local"

    # structure_test（带修复循环）
    adopt_coder_prompt = _build_adopt_coder_prompt(name, description)
    passed, msg = structure_test(name, tool_path, adopt_coder_prompt)

    if passed:
        # 重新读 meta（修复后可能已更新）
        meta = parse_skill_meta(tool_path) or {}
        description = meta.get("description") or description
        category = meta.get("category") or category
        db_upsert_tool(
            name=name,
            description=description,
            status="battle_tested",   # 来自外来验证工具，直接标记 ready
            category=category,
            field_result=f"改造自gkgift/{file_path.name}，structure_test通过",
            meta_json=json.dumps(meta, ensure_ascii=False),
        )
        _mark_done(file_path.name, "done", day, description)
        print(f"[gift] ⭐ 工具装备成功: {name}", flush=True)
        return f"⭐ 已装备新工具: {name} — {description}"
    else:
        # 改造失败，清除写入的文件，暂存原始
        tool_path.unlink(missing_ok=True)
        _stash_tool(file_path, name, day, msg[:200])
        _mark_done(file_path.name, "stashed", day, msg[:100])
        return f"📦 神秘武器: {name}（改造/测试失败，暂入未知区，待研究）"


# ============================================================
# 文章学习
# ============================================================

def _learn_article(file_path: Path, day: int) -> str:
    """读取文章，Grok 提炼摘要+知识点，写入记忆DB和目标DB"""
    name = file_path.name
    print(f"[gift] 正在学习文章: {name}", flush=True)

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        _mark_done(name, "learned", day, f"读取失败: {e}")
        return f"📖 {name}: 读取失败"
    content = content[:_MAX_ARTICLE_CHARS]

    msgs: list[dict[str, str]] = [
        {"role": "system", "content": _LEARN_SYSTEM},
        {"role": "user", "content": f"资料文件名: {name}\n\n内容:\n{content}"},
    ]
    response = call_llm("grok", msgs, f"学习文章: {name}", temperature=0.3)
    if response.startswith("[FAIL]"):
        log_fail("gift.py", "_learn_article", response[:200], {"name": name})
        _mark_done(name, "learned", day, "Grok失败")
        return f"📖 {name}: 学习失败（Grok不可用）"

    # 解析摘要
    summary = ""
    m = re.search(r"===SUMMARY===(.*?)(?:===KNOWLEDGE===|$)", response, re.DOTALL)
    if m:
        summary = m.group(1).strip()[:150]

    # 解析知识点
    knowledge_text = ""
    m2 = re.search(r"===KNOWLEDGE===(.*?)$", response, re.DOTALL)
    if m2:
        knowledge_text = m2.group(1).strip()

    # 存入记忆 DB
    count = 0
    if knowledge_text:
        count = upsert_knowledge(knowledge_text, day, day)

    # 额外：提取文中的 IP 存入 targets DB
    ip_count = _extract_and_store_targets(content + "\n" + knowledge_text, day)
    if ip_count:
        print(f"[gift] 从文章提取到 {ip_count} 个 IP 目标", flush=True)

    _mark_done(name, "learned", day, summary[:100])
    note = f"记忆+{count}条"
    if ip_count:
        note += f" / 目标+{ip_count}个"
    print(f"[gift] 📖 {name} 学习完成（{note}）", flush=True)
    return f"📖 学到了（{name}）: {summary or '(无摘要)'}"


# ============================================================
# 主入口
# ============================================================

def process_gifts(day: int) -> list[str]:
    """扫描 gkgift/ 目录，处理所有新文件，返回公告列表

    在 brain._run_one_round 每轮开头调用。
    GIFT_DIR 不存在时静默返回 []。
    """
    if not GIFT_DIR.exists():
        return []

    done = _load_done()
    announcements: list[str] = []

    for file_path in sorted(GIFT_DIR.iterdir()):
        if not file_path.is_file():
            continue  # 跳过子目录

        fname = file_path.name
        # 跳过已处理
        if fname in done and done[fname]["status"] in ("done", "stashed", "learned"):
            continue

        ext = file_path.suffix.lower()

        try:
            if ext == ".py":
                msg = _adopt_tool(file_path, day)
            elif ext in _ARTICLE_EXTS:
                msg = _learn_article(file_path, day)
            else:
                # 未知格式，尝试当文章处理
                msg = _learn_article(file_path, day)
        except Exception as e:
            log_fail("gift.py", "process_gifts", f"{type(e).__name__}: {e}",
                     {"file": fname, "day": day})
            msg = f"⚠️ {fname}: 处理异常 ({type(e).__name__})"
            _mark_done(fname, "stashed", day, str(e)[:100])

        announcements.append(msg)

    return announcements
