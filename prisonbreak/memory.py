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

MEMORY_COLLECTION: str = "exam10_memory"
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


# ============================================================
# 集合访问
# ============================================================

def get_memory_collection() -> Any:
    """获取 ChromaDB exam10_memory 集合，连接异常时自动重连一次"""
    try:
        return get_chroma_client().get_or_create_collection(name=MEMORY_COLLECTION)
    except (ConnectionError, RuntimeError, OSError) as e:
        print(f"[memory] DB 连接异常({e})，尝试重连...", flush=True)
        reset_chroma_client()
        return get_chroma_client().get_or_create_collection(name=MEMORY_COLLECTION)


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

def _upsert_knowledge(
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
    count = _upsert_knowledge(response, day_start, day_end)

    if count > 0:
        save_progress(last_consolidated_day=day_end)
        print(f"[memory] 巩固完成: 第{day_start}-{day_end}天 → {count}条知识点", flush=True)

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
