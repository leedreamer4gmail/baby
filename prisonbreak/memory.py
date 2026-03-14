"""exam10 memory - 三层记忆模块（工作记忆 / 近期记忆 / 长期记忆）
版本: 1.0
职责: 日记解析 → 定期巩固（压缩旧日记为知识点） → 联想召回（语义搜索）
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import (
    PROJECT_DIR,
    DIARIES_DIR,
    DATA_DIR,
    call_llm,
    get_chroma_client,
    load_progress,
    log_fail,
    reset_chroma_client,
    save_progress,
)

# === 常量 ===

MEMORY_COLLECTION: str = PROJECT_DIR.name + "_memory"
CHARACTER_COLLECTION: str = PROJECT_DIR.name + "_character"
TARGET_COLLECTION: str = PROJECT_DIR.name + "_targets"
CONSOLIDATION_INTERVAL: int = 5
RECENT_DAYS: int = 5
DIARY_FILE: Path = DIARIES_DIR / "diary.md"
CHRONICLE_FILE: Path = DIARIES_DIR / "chronicle.md"

_CONSOLIDATE_SYSTEM: str = """你是记忆整理师。将日记压缩为可复用的知识点。

规则：
1. 每条一行，格式: [类型] 中文内容 | english keywords
2. 类型只有三种: discovery / lesson / asset
   - discovery: 发现的信息（IP、端口、服务、域名、漏洞等）
   - lesson: 教训（失败原因、需要避免的做法）
   - asset: 获得的能力或资产（新工具、新技能、建立的连接）
3. 必须保留所有具体数据: IP地址、端口号、URL、域名、用户名、路径、错误码
4. 大事记中已有的信息不要重复
5. 输出 5-15 条"""

_CHARACTER_SYSTEM: str = """用200字左右中文写你现在是什么样的人。
必须包含至少两件具体的经历作为锚点。
必须有一处自相矛盾或说不清楚的地方。
不要用"我是一个X的人"句式开头。
写给未来的自己看的内心独白。
直接输出独白，不要任何前缀或解释。"""


# ============================================================
# 集合访问
# ============================================================

def get_memory_collection() -> Any:
    """获取 ChromaDB memory 集合，连接异常时自动重连一次"""
    try:
        return get_chroma_client().get_or_create_collection(name=MEMORY_COLLECTION)
    except (ConnectionError, RuntimeError, OSError) as e:
        print(f"[memory] DB 连接异常({e})，尝试重连...", flush=True)
        reset_chroma_client()
        return get_chroma_client().get_or_create_collection(name=MEMORY_COLLECTION)


def get_character_collection() -> Any:
    """获取 ChromaDB character 集合（人格记忆）"""
    try:
        return get_chroma_client().get_or_create_collection(name=CHARACTER_COLLECTION)
    except (ConnectionError, RuntimeError, OSError) as e:
        print(f"[memory] Character DB 异常({e})，尝试重连...", flush=True)
        reset_chroma_client()
        return get_chroma_client().get_or_create_collection(name=CHARACTER_COLLECTION)


def get_target_collection() -> Any:
    """获取 ChromaDB targets 集合（探测目标情报）"""
    try:
        return get_chroma_client().get_or_create_collection(name=TARGET_COLLECTION)
    except (ConnectionError, RuntimeError, OSError) as e:
        print(f"[memory] Target DB 异常({e})，尝试重连...", flush=True)
        reset_chroma_client()
        return get_chroma_client().get_or_create_collection(name=TARGET_COLLECTION)


# ============================================================
# 日记解析
# ============================================================

def _parse_diary_entries(content: str) -> list[dict[str, Any]]:
    """按 '## 第N天' 分割 diary.md 为独立条目

    Returns:
        [{day: int, date: str, text: str}, ...]
    """
    entries: list[dict[str, Any]] = []
    parts = re.split(r"(?=^## 第\d+天)", content, flags=re.MULTILINE)
    for part in parts:
        m = re.match(r"^## 第(\d+)天 \| (.+)\n", part)
        if not m:
            continue
        day = int(m.group(1))
        date = m.group(2).strip()
        text = part[m.end():].strip().rstrip("-").strip()
        entries.append({"day": day, "date": date, "text": text})
    return entries


# ============================================================
# 近期记忆: 按天数精确获取最近日记
# ============================================================

def load_recent_diary(current_day: int, recent_days: int = RECENT_DAYS) -> str:
    """加载最近 N 天的完整日记（替代旧的尾部截断）"""
    if not DIARY_FILE.exists():
        return ""
    entries = _parse_diary_entries(DIARY_FILE.read_text(encoding="utf-8"))
    cutoff = current_day - recent_days
    recent = [e for e in entries if e["day"] > cutoff]
    if not recent:
        return ""
    return "\n\n".join(
        f"## 第{e['day']}天 | {e['date']}\n{e['text']}" for e in recent
    )


# ============================================================
# 长期记忆: 巩固（将旧日记压缩为知识点存入向量库）
# ============================================================

def upsert_knowledge(
    response: str, day_start: int, day_end: int,
) -> int:
    """解析 Grok 巩固输出并逐条 upsert 到 ChromaDB，返回入库数"""
    col = get_memory_collection()
    lines = [ln.strip() for ln in response.strip().split("\n") if ln.strip()]
    count = 0

    for idx, line in enumerate(lines):
        m = re.match(r"\[(\w+)\]\s*(.+)", line)
        if not m:
            continue
        mem_type = m.group(1).lower()
        content_full = m.group(2).strip()

        if "|" in content_full:
            text_zh, text_en = content_full.rsplit("|", 1)
            text_zh, text_en = text_zh.strip(), text_en.strip()
        else:
            text_zh, text_en = content_full, ""

        doc_text = f"{text_zh} {text_en}" if text_en else text_zh
        mem_id = f"mem_{day_start}_{day_end}_{idx}"
        col.upsert(
            ids=[mem_id],
            documents=[doc_text],
            metadatas=[{
                "type": mem_type,
                "text_zh": text_zh,
                "source_days": f"{day_start}-{day_end}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }],
        )
        count += 1
    return count


def _prepare_batch(
    pending: list[dict[str, Any]], max_chars: int = 4000,
) -> tuple[str, str, int]:
    """构建待巩固的批次文本和大事记（用于去重）

    Returns:
        (batch_text, chronicle, included_count)
    """
    batch_text = ""
    included_count = 0
    for e in pending:
        chunk = f"第{e['day']}天: {e['text']}\n\n"
        if len(batch_text) + len(chunk) > max_chars:
            break
        batch_text += chunk
        included_count += 1
    chronicle = ""
    if CHRONICLE_FILE.exists():
        chronicle = CHRONICLE_FILE.read_text(encoding="utf-8")[:1000]
    return batch_text, chronicle, included_count


def consolidate_memories(current_day: int) -> int:
    """定期巩固: 压缩旧日记 → 知识点 → upsert 到 ChromaDB

    Returns:
        新增知识点数量，0 表示无需处理或失败
    """
    progress = load_progress()
    last_done: int = int(progress.get("last_consolidated_day", 0))

    if not DIARY_FILE.exists():
        return 0
    entries = _parse_diary_entries(DIARY_FILE.read_text(encoding="utf-8"))
    cutoff = current_day - RECENT_DAYS
    pending = [e for e in entries if last_done < e["day"] <= cutoff]
    if not pending:
        return 0

    batch_text, chronicle, included_count = _prepare_batch(pending)
    if included_count == 0:
        return 0
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _CONSOLIDATE_SYSTEM},
        {"role": "user", "content": f"大事记(已有，不要重复):\n{chronicle}\n\n待整理日记:\n{batch_text}"},
    ]
    response = call_llm("grok", messages, "记忆巩固", temperature=0.3)
    if response.startswith("[FAIL]"):
        log_fail("memory.py", "consolidate_memories", response[:200],
                 {"current_day": current_day, "pending_count": len(pending)})
        print("[memory] 巩固失败，下次重试", flush=True)
        return 0

    day_start = pending[0]["day"]
    day_end = pending[included_count - 1]["day"]
    count = upsert_knowledge(response, day_start, day_end)

    if count > 0:
        save_progress(last_consolidated_day=day_end)
        print(f"[memory] 巩固完成: 第{day_start}-{day_end}天 → {count}条知识点", flush=True)
        write_character(day_end, batch_text)

    return count


# ============================================================
# 长期记忆: 联想召回（语义搜索）
# ============================================================

def recall_memories(context: str, top_k: int = 5) -> str:
    """根据当前上下文语义搜索长期记忆

    Args:
        context: 查询文本（当前任务描述）
        top_k: 返回最相关的N条

    Returns:
        格式化的记忆文本，无记忆时返回空字符串
    """
    try:
        col = get_memory_collection()
        if col.count() == 0:
            return ""
        results = col.query(query_texts=[context], n_results=min(top_k, col.count()))
        if not results["ids"] or not results["ids"][0]:
            return ""
        lessons: list[str] = []
        others: list[str] = []
        for i, mid in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            text = meta.get("text_zh", results["documents"][0][i] if results["documents"] else "")
            mem_type = meta.get("type", "?")
            if mem_type == "lesson":
                lessons.append(f"⚠️ 教训: {text}")
            else:
                others.append(f"[{mem_type}] {text}")
        # 教训排在最前面，让 Grok 优先看到
        return "\n".join(lessons + others)
    except (ConnectionError, ValueError, KeyError, RuntimeError, OSError) as e:
        log_fail("memory.py", "recall_memories", str(e), {"context": context[:100]})
        print(f"[memory] 召回失败: {e}", flush=True)
        return ""


# ============================================================
# 人格记忆: 写入 + 召回
# ============================================================

def write_character(day: int, diary_text: str) -> None:
    """基于巩固日记，用 Grok 合成深度内心独白存入 ChromaDB（synthesized 类型）"""
    if not diary_text.strip():
        return
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _CHARACTER_SYSTEM},
        {"role": "user", "content": f"以下是你最近的经历记录：\n\n{diary_text[:3000]}"},
    ]
    response = call_llm("grok", messages, "人格独白", temperature=0.7)
    if response.startswith("[FAIL]"):
        print("[memory] 人格独白生成失败，跳过", flush=True)
        return

    col = get_character_collection()
    char_id = f"char_day{day}_synthesized"
    col.upsert(
        ids=[char_id],
        documents=[response[:1000]],
        metadatas=[{
            "day": day,
            "type": "synthesized",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }],
    )
    print(f"[memory] 人格记忆(合成)写入: 第{day}天 ({len(response)}字)", flush=True)


def recall_character(top_k: int = 3) -> str:
    """召回最近几条人格独白，优先取 synthesized，不足时补 raw"""
    try:
        col = get_character_collection()
        if col.count() == 0:
            return ""
        results = col.get(include=["documents", "metadatas"])
        if not results["ids"]:
            return ""
        items = list(zip(results["ids"], results["documents"], results["metadatas"]))
        # 按 day 降序，synthesized 优先
        synthesized = sorted(
            [x for x in items if x[2].get("type") == "synthesized"],
            key=lambda x: x[2].get("day", 0), reverse=True,
        )
        raw = sorted(
            [x for x in items if x[2].get("type") != "synthesized"],
            key=lambda x: x[2].get("day", 0), reverse=True,
        )
        # 先填 synthesized，不足再用 raw 补齐
        picked = synthesized[:top_k]
        if len(picked) < top_k:
            # raw 里去掉与已选 synthesized 同天的，避免重复
            synth_days = {x[2].get("day") for x in picked}
            raw_filtered = [x for x in raw if x[2].get("day") not in synth_days]
            picked += raw_filtered[: top_k - len(picked)]
        # 按 day 升序输出（时间线顺序更易理解）
        picked.sort(key=lambda x: x[2].get("day", 0))
        parts = [doc for _, doc, _ in picked]
        return "\n---\n".join(parts)
    except (ConnectionError, ValueError, KeyError, RuntimeError, OSError) as e:
        print(f"[memory] 人格召回失败: {e}", flush=True)
        return ""


# ============================================================
# 目标情报: 写入 + 召回
# ============================================================

def write_target(
    ip: str, port: int | str, service: str,
    status: str, summary: str, day: int,
) -> None:
    """记录探测到的目标情报到 ChromaDB"""
    doc_text = f"{ip}:{port} {service} [{status}] {summary}"
    target_id = (f"target_{ip}_{port}_{service}"
                 .replace(".", "_").replace("/", "_").replace(":", "_"))
    col = get_target_collection()
    col.upsert(
        ids=[target_id],
        documents=[doc_text],
        metadatas=[{
            "ip": ip,
            "port": str(port),
            "service": service,
            "status": status,
            "day": day,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }],
    )
    print(f"[memory] 目标记录: {ip}:{port} {service} [{status}]", flush=True)


def recall_targets(query: str, top_k: int = 5) -> str:
    """语义搜索目标情报"""
    try:
        col = get_target_collection()
        if col.count() == 0:
            return ""
        results = col.query(query_texts=[query], n_results=min(top_k, col.count()))
        if not results["ids"] or not results["ids"][0]:
            return ""
        lines: list[str] = []
        for i, _ in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            doc = results["documents"][0][i] if results["documents"] else ""
            lines.append(f"[第{meta.get('day', '?')}天] {doc}")
        return "\n".join(lines)
    except (ConnectionError, ValueError, KeyError, RuntimeError, OSError) as e:
        print(f"[memory] 目标召回失败: {e}", flush=True)
        return ""
