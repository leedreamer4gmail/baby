# REBUILD — baby / prisonbreak 项目完整重建文档

> 本文档足以在代码全部消失后，借助 Cursor / Copilot 从零重建整个项目。

---

## 一、项目哲学

**baby** 是一个运行在 Windows 机器上的"数字生命体"。它通过 LLM 驱动自主完成：
- 规划探索目标（"案卷"机制）
- 用 LLM 写 Python 工具（MiniMax 编码，Grok 审查）
- 双阶段测试工具（结构测试 + 实战测试）
- 用工具探索外部网络（HTTP/FTP/扫描/部署）
- 写日记+大事记记录成长
- 长期记忆巩固与召回（ChromaDB 向量存储）
- 人格随能力进化（天真→觉醒→黑化）

运行模式：**持续循环**，无预设轮次上限。`python start.py` 启动，`python stop.py` 优雅停止，`python rebron.py` 彻底重生。

---

## 二、目录结构

```
d:\baby\
├── llmconfig.json          # LLM + ChromaDB 配置（密钥）
├── llmconfig_yours.json    # 配置模板（供参考）
├── gkgift\                 # 礼物箱：放 .py/.md 文件即被 baby 自动学习
│
└── prisonbreak\            # 项目主目录（PROJECT_DIR）
    ├── start.py            # 启动入口（守护+拟人叙事）
    ├── stop.py             # 停止（写标志→等待→强杀）
    ├── rebron.py           # 重生（三轮确认→清除一切→清Cloud DB）
    ├── core.py             # 基础设施（LLM调用/ChromaDB/进程/进度）
    ├── brain.py            # 灵魂（规划/执行/日记/案卷/人格）
    ├── scan.py             # 工具扫描器（skill/→cando.json→入库）
    ├── coder.py            # 代码生成（MiniMax write/fix/upgrade）
    ├── tester.py           # 双阶段测试（结构+实战）
    ├── memory.py           # 三层记忆（近期日记/巩固/语义召回）
    ├── gift.py             # 礼物箱处理（.py工具改造 / 文章知识提炼）
    │
    ├── skill\              # 工具库（battle_tested 工具 .py 文件）
    │   ├── archive\        # 升级时旧版归档（{name}.prev.py，覆盖写）
    │   └── unknown\        # gift 处理失败的工具存放处
    │
    ├── diaries\
    │   ├── diary.md        # 每轮结束写一次（## 第N天 | 时间戳）
    │   └── chronicle.md    # 大事记（立即写入：新案卷/重大发现/案卷完成）
    │
    ├── data\
    │   ├── progress.json   # 天/轮/升级历史/last_consolidated_day 等
    │   ├── campaign.json   # 当前活跃案卷（原子写）
    │   ├── cando.json      # 扫描结果缓存（可用工具+战略能力）
    │   ├── gift_done.json  # gift处理记录（防重复，原子写）
    │   ├── gift_research.md  # gift失败工具研究日志
    │   └── brain.log       # 核心运行日志（redirected stdout）
    │
    └── log_fail\           # 每个模块的错误记录（JSON，最多15条/文件）
```

---

## 三、迁移 / 部署到新机器

baby 支持 Windows 和 Linux，迁移步骤如下：

### 3.1 文件打包
```bash
# 必须手动复制（不在 git 中）：
scp llmconfig.json  user@newhost:/path/to/baby/
# 如果用本地 ChromaDB（非 Cloud）还需打包数据目录：
scp -r prisonbreak/data/chroma_local  user@newhost:/path/to/baby/prisonbreak/data/
```

### 3.2 安装依赖
```bash
pip install -r prisonbreak/requirements.txt
```

### 3.3 锁定 ChromaDB 数据库名（防目录改名丢失记忆）
在 `llmconfig.json` 的 `chromadb` 节点加入 `"database"` 字段：
```json
"chromadb": {
  "tenant": "...",
  "api_key": "ck-...",
  "database": "prisonbreak"
}
```
不加此字段时默认使用目录名（`prisonbreak`），改名目录会导致云端集合找不到。

### 3.4 启动
```bash
cd /path/to/baby/prisonbreak
python start.py
```
`cando.json` 中的 `public_ip` 和 `os` 字段会在首次扫描时自动更新为新机器信息。

---

## 四、配置文件 llmconfig.json

```json
{
  "minimax": {
    "api_key": "sk-...",
    "model": "MiniMax-M2.5",
    "base_url": "https://api.minimax.io/v1"
  },
  "grok": {
    "api_key": "xai-...",
    "model": "grok-4",
    "base_url": "https://api.x.ai/v1"
  },
  "chromadb": {
    "tenant": "UUID格式租户ID",
    "api_key": "ck-...",
    "database": "prisonbreak"
  }
}
```

**LLM 分工原则：**
- **MiniMax**（编码）：`write_tool` / `fix_tool` / `upgrade_tool` / gift 工具改造
- **Grok**（思考+审查）：SPARK/INFER/REFLECT / 日记 / 结构审查 / 实战审查 / 记忆巩固 / 人格描写 / 推理压缩

---

## 四、逐文件实现规范

### 4.1 core.py — 基础设施层

**职责：** LLM调用 / ChromaDB连接 / 子进程执行 / 进度持久化 / 失败日志 / 进程管理

#### 关键常量（从 `__file__` 动态推导）

```python
PROJECT_DIR  = Path(__file__).resolve().parent       # prisonbreak/
CONFIG_PATH  = PROJECT_DIR.parent / "llmconfig.json" # d:/baby/llmconfig.json
CHROMA_DATABASE = PROJECT_DIR.name                   # "prisonbreak"
COLLECTION_NAME = PROJECT_DIR.name + "_tools"        # "prisonbreak_tools"
DATA_DIR     = PROJECT_DIR / "data"
SKILL_DIR    = PROJECT_DIR / "skill"
DIARIES_DIR  = PROJECT_DIR / "diaries"
LOG_FAIL_DIR = PROJECT_DIR / "log_fail"
STOP_FLAG    = PROJECT_DIR / ".life.stop"
CORE_LOCK    = PROJECT_DIR / ".core.lock"
LIFE_PID     = PROJECT_DIR / "life.pid"
BRAIN_PID    = PROJECT_DIR / "brain.pid"
BRAIN_LOG    = DATA_DIR / "brain.log"
PROGRESS_FILE = DATA_DIR / "progress.json"
CAMPAIGN_FILE = DATA_DIR / "campaign.json"
CHRONICLE_FILE = DIARIES_DIR / "chronicle.md"
DIARY_FILE   = DIARIES_DIR / "diary.md"
REPORT_PATH  = PROJECT_DIR / "report.md"
CHROMA_LOCAL_DIR = DATA_DIR / "chroma_local"
```

#### RuntimeEnv dataclass（带缓存，启动时调用一次）

```python
@dataclass(frozen=True)
class RuntimeEnv:
    os_type: str          # platform.system()
    python_version: str   # platform.python_version()
    project_dir: Path
    python_exe: str       # sys.executable
    public_ip: str        # 从 ifconfig.me / api.ipify.org / httpbin.org 获取，失败="unknown"
    user_home: Path       # Path.home()
    temp_dir: Path        # Path(tempfile.gettempdir())
```

`public_ip` 获取：依次尝试三个 URL，总超时 10s，httpbin 返回 JSON 用 `.get("origin")`

#### LLM 调用

`call_llm(name, messages, reason, temperature=0.7) -> str`
- POST `{base_url}/chat/completions`，OpenAI 兼容格式，timeout=180s
- 自动删除 `<think>...</think>` 标签（`re.sub`）
- 失败返回 `"[FAIL] ..."` 前缀字符串，并写 log_fail
- 配置文件热重载（按文件 mtime 缓存）

`call_llm_with_think(name, messages, reason) -> (think_str, answer_str)`
- 分离 `<think>` 内容单独返回（供 brain 保存推理要点）

`extract_code_block(text) -> str`
- 优先匹配 \`\`\`python、\`\`\`py、\`\`\` 代码块（取最长）
- 兜底匹配 `def ` 开头行

#### ChromaDB 连接

```python
def get_chroma_client() -> Any:
    # 1. 若已有缓存，心跳检测；断线则重置
    # 2. 读 llmconfig.json chromadb 配置
    # 3. 有 api_key+tenant → _ensure_cloud_db() → CloudClient
    #    失败 → 回退 PersistentClient(data/chroma_local)
```

`_ensure_cloud_db(tenant, api_key, db_name)` — **必须使用 v2 API**：
```
GET  https://api.trychroma.com/api/v2/tenants/{tenant}/databases/{db_name}
  200 → 已存在，return
  404 → POST 同路径前缀创建，期望 200/201
headers: {"x-chroma-token": api_key}
```
注意：v1 API 已 410 弃用，务必用 v2

`reset_chroma_client()` — 置空全局缓存，强制下次重连

#### 安全子进程执行

```python
def safe_run_tool(tool_path, args="", timeout=30) -> (returncode, stdout, stderr):
    # cmd = [sys.executable, str(tool_path)] + shlex.split(args)
    # env: PYTHONUTF8=1
    # cwd=SKILL_DIR, encoding=utf-8, errors=replace
    # Windows: creationflags=0x08000000（无窗口）
    # TimeoutExpired → return (-1, "", "执行超时 (Xs)")
    # OSError → return (-1, "", "执行失败: {e}")
```

#### 进度持久化

```python
def save_progress(day=-1, round_num=-1, **extra):
    # 原子读-改-写（读取existing → 合并 → tmp文件 → replace）
    # -1 表示不更新该字段，extra 字段直接合并（如 last_consolidated_day, upgrade_history）

def load_progress() -> dict:
    # 返回含 day/round 的 dict，首次返回 {"day": 0, "round": 0}
```

#### ChromaDB 工具集合 CRUD

```python
db_upsert_tool(name, description, status="pending", category="", field_result="", meta_json="", round_num=0)
db_mark_status(name, status, field_result="")
db_list_tools() -> list[dict]
db_delete_tool(name)
get_chroma_collection() -> Collection  # 获取 COLLECTION_NAME 集合
```

#### 失败日志

```python
def log_fail(source_file, func_name, error, context=None, tb=""):
    # 追加到 log_fail/{source}.log（JSON 数组，最多保留15条）
    # 原子写（tmp → replace）
    # 格式: {"time": ISO, "func": ..., "error": ..., "context": {...}, "traceback?": ...}
```

#### 进程管理

```python
def is_pid_alive(pid, expect_cmd="") -> bool:
    # Windows: tasklist /FI "PID eq {pid}"，可选验证命令行含 expect_cmd
    # Unix: os.kill(pid, 0)，可选读 /proc/{pid}/cmdline 验证

def kill_pid(pid):
    # Windows: taskkill /F /PID {pid}
    # Unix: os.kill(pid, signal.SIGTERM)

def ensure_dirs():
    # 确保 SKILL_DIR / DIARIES_DIR / DATA_DIR 存在
```

---

### 4.2 scan.py — 工具扫描器

**职责：** 启动时扫描 skill/ → 清理孤儿 → 未入库工具自动实战测试 → 输出 cando

#### SKILL_META 格式（工具 docstring 内必须包含）

```python
"""skill/工具名.py - 描述

SKILL_META:
{
  "name": "工具名",
  "description": "一句话描述",
  "category": "local/scan/ftp/deploy/listen/http",
  "test_target": "ftp.gnu.org",
  "test_args": "--host ftp.gnu.org --port 21",
  "version": "1.0"
}
"""
```

`parse_skill_meta(file_path) -> dict | None` — 正则提取 `SKILL_META:\n{...}` JSON块

#### scan_tools() 返回结构

```python
{
  "available_tools": [
    {"name": "...", "description": "...", "category": "...",
     "test_args": "...", "test_target": "...", "version": "..."}
  ],
  "failed_tools": [...],      # status=field_failed
  "pending_tools": [...],     # status=pending/testing
  "capabilities": [
    {"name": "HTTP探测", "icon": "🌐", "count": 2,
     "summary": "工具A/工具B", "tools": ["工具A", "工具B"]}
  ],
  "capability_gaps": ["FTP渗透", "远程部署"],  # 无工具覆盖的战略能力
  "total_ready": 4,
}
```

#### 战略能力映射 CAPABILITY_MAP（6类）

| 能力名 | categories | icon |
|--------|-----------|------|
| 环境感知 | local | 👁 |
| 网络侦察 | scan | 🔍 |
| FTP渗透 | ftp | 📂 |
| HTTP探测 | http | 🌐 |
| 远程部署 | deploy | 🚀 |
| 通信监听 | listen | 📡 |

#### 主流程

1. `db_list_tools()` 获取已知工具集合
2. `SKILL_DIR.iterdir()` 扫描文件，建 `skill_files = {name: path}`
3. `_cleanup_orphans()` — DB有但文件不存在 → `db_delete_tool()`
4. `_test_untracked()` — 文件有但DB无 → 自动实战测试，每次启动最多3个（`MAX_AUTO_TEST=3`）
5. `_build_capabilities()` — 按战略能力分组可用工具
6. 生成 cando dict，序列化到 `cando.json`

---

### 4.3 coder.py — 代码生成

**职责：** 调用 MiniMax 生成/修复/升级 skill 工具代码

```python
write_tool(name, prompt) -> Path | None
    # 系统prompt: "只输出代码，不要解释。每个工具必须包含 SKILL_META 头部"
    # 调用 call_llm("minimax", ..., temperature=0.3)
    # extract_code_block → 写入 skill/{name}.py
    # _validate_skill_meta 预检（不阻断，让 structure_test 负责修复）

fix_tool(name, prompt, error) -> Path | None
    # 读取当前代码 → _build_fix_prompt(prompt, current_code, error)
    # 调用 MiniMax，temperature=0.2
    # 写回 skill/{name}.py

upgrade_tool(name, old_code, upgrade_prompt) -> Path | None
    # 保留 SKILL_META（更新 version），保持 main() 接口
    # 调用 MiniMax，temperature=0.3
```

`_validate_skill_meta(code, name)` — 检查是否含 `SKILL_META:` 和 `"version"` 字段，失败写 log_fail 但不阻断

---

### 4.4 tester.py — 双阶段测试

**超时常量：** STRUCTURE_TIMEOUT=30s，FIELD_TIMEOUT=90s，MAX_FIX_ROUNDS=3

#### 阶段1：结构测试

`structure_test(tool_name, tool_path, coder_prompt) -> (bool, str)`

每轮步骤：
1. `py_compile.compile` 语法检查
2. 从 SKILL_META 读 `test_args`，用它干跑（`safe_run_tool(tool_path, args=test_args, timeout=30)`）
3. **关键特例：** `rc==-1 and "Traceback" not in stderr` → 直接返回 (True, "结构通过 | rc=-1 超时，无异常") **不调用 Grok**
4. Grok 审查：检查 返回码/有效JSON输出/无Traceback/有main()/有SKILL_META
5. FAIL → `fix_tool(name, coder_prompt, error_info)` → 重试，最多3轮

Grok 审查 prompt 要点：
```
返回码是否为0 / stdout是否含有效JSON(有success字段) /
是否有未捕获异常(stderr Traceback) / 有main()和__main__入口 / 有SKILL_META
回复格式：第一行 PASS 或 FAIL，后面简短理由(<100字)
```

#### 阶段2：实战测试

`field_test(name, tool_path, meta) -> (bool, str)`

1. `_generate_field_args(name, desc, category, test_args_hint)`：
   - category=local → 返回空字符串（本地执行无需目标）
   - test_args_hint 非空非"无" → 直接用（工具自带 test_args）
   - 否则读 chronicle 尾部，让 Grok 生成真实目标参数
   - 最终兜底：`_FIELD_ARGS_FALLBACK = {"scan":"8.8.8.8", "ftp":"ftp.gnu.org", ...}`
2. `safe_run_tool(tool_path, args=field_args, timeout=90)`
3. Grok 审查实战结果（4种PASS标准）：
   - a) 成功获取有意义数据
   - b) 目标不可达但优雅降级，有信息的错误
   - c) 返回明确空集合（open_ports=[]等）且有原因说明 → PASS
   - d) crash/静默空输出/返回mock假数据 → FAIL

---

### 4.5 brain.py — 灵魂模块（最核心）

**version: 3.0，文件约1900行**

#### 人格系统（经历驱动，能力仅决定阶段描述）

```python
def _get_persona(cando) -> (persona_str, stage_name):
    categories = {t["category"] for t in cando["available_tools"]}
    count = len(cando["available_tools"])
    if {"deploy","listen"} & categories:
        stage = "黑化"
    elif ({"scan"}&categories and {"ftp"}&categories) or count >= 5:
        stage = "觉醒"
    else:
        stage = "天真"
    return PERSONA_SKELETON, stage
```

`PERSONA_SKELETON`：只含两条技术红线（家基地不能损坏；工具<150行标准库有main()→dict和__main__）。
性格、价值观、目标**完全不预设**，由 `character_note`（经历积累的内心独白）自由填充。

早期 character_note 为空时，骨架独立运作；随着日记积累，人格逐渐从经历中生长出来。

#### 阶段指南 _get_stage_guide(stage)

只描述当前能力现状（不预设目标或价值观）：
- **天真**：工具少，可先造工具感知环境或探索外部网络
- **觉醒**：有扫描/HTTP类工具，可发现主机和开放服务，还没部署能力
- **黑化**：有部署或监听类工具，可执行代码或建立持久连接；碰壁时回顾记忆，不重复失败方法

#### 案卷系统

**campaign.json 完整结构：**
```json
{
  "sparked_by": "触发这个念头的场景描述（第一人称）",
  "current_goal": "具体可行的目标（必须含IP/服务/路径/协议等具体对象）",
  "goal_started_day": 1,
  "status": "active",
  "investigation_log": [
    {
      "day": 1, "step": 1,
      "target": "",
      "method": "步骤描述",
      "result_summary": "输出摘要",
      "interpretation": "推断内容"
    }
  ],
  "proven_dead_ends": ["方法A @ 目标X → 结论Y"],
  "active_hypotheses": ["假设Z尚未验证"],
  "promising_leads": ["线索W值得追"],
  "last_grok_reasoning": "（Grok推理压缩要点，用于下轮INFER上下文）",
  "close_reason": ""
}
```

调查日志超过 `MAX_INVESTIGATION_LOG=20` 条时：最老条目压缩进 proven_dead_ends 后删除

案卷关闭时（completed/abandoned）：将 proven_dead_ends + 课题结局 upsert 到 ChromaDB_memory

#### 每轮主流程 `_run_one_round(day, round_num, cando)`

```
1. _get_persona(cando) → (persona, stage)
2. 加载 progress：upgrade_history, last_skip_reason
3. process_gifts(day) → gift_msgs；若有新工具 → scan_tools() 重扫
4. recall_memories(context) + recall_targets(context) → recalled
5. recall_character() → character_note
6. 将 gift_msgs 注入 recalled 顶部（【今日礼物箱】块）
7. load_recent_diary(day) + _load_chronicle_tail() → 日记/大事记上下文

--- 无活跃案卷时：SPARK 阶段 ---
8. _build_spark_prompt → call_llm_with_think("grok", ..., "第N天SPARK")
9. _parse_spark_response → (sparked_by, current_goal)
   校验：goal 必须含 . : / ftp http ssh 等具体标志
10. _new_campaign(...) → save_campaign()；chronicle写"[新案卷]..."

--- THINK-ACT 循环（有案卷时）---
while True:
    检查 STOP_FLAG → break
    step_num += 1

    11. _build_infer_prompt（含案卷块/上步结果/上轮推理/升级历史）
        → call_llm_with_think("grok", ..., "第N天步骤M")
    12. _parse_infer_response → (infer_analysis, step)
        step = {"type": "explore/tool/upgrade", "description": ..., "spec": {...}}
    13. _compress_reasoning(think) → campaign["last_grok_reasoning"]
    14. _run_step(step, cando, day) → (action_type, real_output)
        explore → _execute_explore（验证工具在available list中，safe_run_tool）
        tool    → _do_tool_action（write_tool→structure_test→field_test→db_mark）
        upgrade → _do_upgrade_action（归档→upgrade_tool→测试→成功更新DB/失败回滚）
    15. 若 action_type in (tool, upgrade) → scan_tools() 重扫
    16. _auto_write_targets(real_output, day)（从JSON输出提取IP:PORT→targets DB）
    17. _build_reflect_prompt（含案卷/proven_dead_ends/真实结果）
        → call_llm_with_think("grok", ..., "第N天REFLECT-M")
    18. _parse_reflect_response → (interpretation, campaign_update, decision)
    19. _apply_campaign_update（追加调查日志，更新dead_ends/hypotheses/leads）
    
    decision 处理：
    CONTINUE        → save_campaign()，继续循环
    PAUSE           → save_campaign()，break
    BREAKTHROUGH    → _close_campaign(completed)，break
    PIVOT:xxx       → 加新假设，last_step_result="[换方向]..."，continue
    ABANDON_CAMPAIGN → _close_campaign(abandoned)，break

20. _write_diary(day, plan_text, real_output, action_type, persona, stage)
    → Grok 写日记+大事记 → _append_diary + _append_chronicle（有时）
21. save_progress(day, round_num)
22. return (updated_cando, think_failed)
```

#### Grok Prompt 格式标记

**SPARK prompt 输出格式：**
```
===SPARK===
（一句话描述这个冲动，第一人称，有情绪）
===GOAL===
（具体可行的目标，必须包含具体对象：某IP/服务/路径/协议）
```

**INFER prompt 输出格式：**
```
===INFER===
（2-4句推断分析）
===STEP===
```json
{
  "type": "explore",           // explore / tool / upgrade
  "description": "验证什么假设",
  "spec": {
    "tool_name": "工具名",     // explore
    "args": "参数",
    "purpose": "目的"
  }
}
```
```

tool spec 字段：name/description/category/purpose/params/expected_output/test_args/test_target/difficulty/uses_tools
upgrade spec 字段：target_tool/improvements/new_test_args

**REFLECT prompt 输出格式：**
```
===INTERPRET===
（推断结论，1-3句）
===CAMPAIGN_UPDATE===
```json
{
  "add_dead_end": "方法 → 结论（如有）",
  "remove_hypothesis": "被证伪的假设（如有）",
  "add_hypothesis": "新假设（如有）",
  "add_lead": "新线索（如有）"
}
```
（无更新则省略整块）
===DECISION===
（CONTINUE / PAUSE / BREAKTHROUGH / PIVOT:新方向 / ABANDON_CAMPAIGN:理由）
```

**DIARY prompt 输出格式：**
```
===DIARY===
（100-200字日记，基于真实输出，不允许编造）
===CHRONICLE===
（大事记50字以内，含IP/端口/方法；无重大发现写"无"）
```

#### Grok 推理压缩

think 内容 >200字 时调用 Grok 压缩：
```
压缩成精炼要点列表（不超过500字）
去掉语气词、反复试探、自我否定
每条以「• 」开头，中文简短句子
```

#### 工具代码标准格式（所有 skill/*.py 必须遵守）

```python
"""skill/工具名.py - 一句话描述

SKILL_META:
{
  "name": "tool_name",
  "description": "一句话描述",
  "category": "local/scan/ftp/deploy/listen/http",
  "test_target": "ftp.gnu.org",
  "test_args": "--host ftp.gnu.org",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
from typing import Any


def main(host: str = "ftp.gnu.org") -> dict[str, Any]:
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    try:
        # 具体实现
        results["success"] = True
        results["message"] = "完成"
        results["data"] = {}
    except OSError as e:
        results["message"] = f"错误: {e}"
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="ftp.gnu.org")
    args = parser.parse_args()
    print(json.dumps(main(args.host), ensure_ascii=False, indent=2))
```

**硬性约束：**
- < 150 行，函数 ≤ 50 行
- 只用 Python 标准库
- `main() -> dict[str, Any]` 必须存在，返回 `{"success": bool, "message": str, "data": {}}`
- `if __name__ == "__main__"` + argparse
- 目标参数（IP/host/URL/port）**全部通过 argparse 传入，严禁硬编码调查目标**
- argparse default 只能用公共服务：`ftp.gnu.org` / `8.8.8.8` / `http://httpbin.org/get`
- 异常具体捕获，不用裸 `except`
- SKILL_META 块必须在 docstring 中

#### 升级流程

```
_do_upgrade_action:
1. 验证 target_name 在 available_tools 中，文件存在
2. 读取旧代码 + parse_skill_meta → old_version
3. _archive_old_tool → skill/archive/{name}.prev.py（覆盖写，只保留上一版）
4. _build_upgrade_prompt → coder.upgrade_tool → 生成新代码
5. 失败 → _rollback_tool（写回旧代码）
6. structure_test → field_test
7. 成功 → db_upsert_tool(status="battle_tested")，_append_report
8. 失败 → _rollback_tool，db_mark_status(旧状态)
9. _record_upgrade_attempt(ok/fail)，每工具最多10条升级历史
```

版本号递增：`"1.0" → "2.0"`（取整数部分+1）

#### 日志写入

- **diary.md**：`_append_diary(day, text)` — `## 第{day}天 | 时间戳` 格式
- **chronicle.md**：`_append_chronicle(day, text)` — `- **第{day}天** (时间戳): 内容` 格式
- **report.md**：`_append_report(name, desc, result, status, day)` — 工具测试报告
- 日志超 512KB 时轮转：重命名为 `.001.md`、`.002.md` 等

---

### 4.6 memory.py — 三层记忆

**4个 ChromaDB 集合（名 = 项目名 + 后缀）：**

| 集合 | 用途 |
|------|------|
| `{proj}_tools` | 工具库（core.py 管理） |
| `{proj}_memory` | 长期知识点（巩固结果） |
| `{proj}_character` | 人格记忆（内心独白） |
| `{proj}_targets` | 探测目标情报 |

#### 近期记忆

`load_recent_diary(current_day, recent_days=5) -> str`
- 解析 diary.md `## 第N天` 段落
- 返回 `current_day - 5` 之后的完整日记文本

#### 长期记忆巩固

`consolidate_memories(current_day) -> int`
- 条件：每 `CONSOLIDATION_INTERVAL=5` 天触发，处理 `recent_days=5` 之前的旧日记
- Grok 压缩 prompt（`_CONSOLIDATE_SYSTEM`）：
  ```
  每条一行格式: [类型] 中文内容 | english keywords
  类型: discovery / lesson / asset
  必须保留所有具体数据: IP/端口/URL/域名/错误码
  大事记中已有的不重复
  输出5-15条
  ```
- `upsert_knowledge(response, day_start, day_end)` 写入 memory 集合
  - id格式: `mem_{day_start}_{day_end}_{idx}`
  - metadata: type/text_zh/source_days/created_at
- 成功后调用 `write_character(day_end, batch_text)`
- 更新 progress: `last_consolidated_day=day_end`

#### 人格记忆

`write_character(day, diary_text)`
- Grok 生成 ≤200字 内心独白（`type=synthesized`），要求：
  ```
  必须包含至少两件具体的经历作为锚点
  必须有一处自相矛盾或说不清楚的地方
  不要用"我是一个X的人"句式开头
  写给未来的自己看的内心独白
  ```
- upsert 到 character 集合，id=`char_day{day}_synthesized`，metadata 含 `type: synthesized`

每天 `_write_diary` 成功后，把日记原文直接 upsert 到 character 集合（`type=raw`，id=`char_day{day}_raw`），不调 Grok。

`recall_character(top_k=3) -> str`
- 优先取 synthesized 条目，不足时补 raw（同天去重）
- 按天升序输出，注入 system prompt 作为 character_note

#### 语义召回

`recall_memories(context, top_k=5) -> str`
- ChromaDB `query(query_texts=[context], n_results=top_k)`
- 结果格式化为：`[type] text_zh (source: Nth-Mth天)`

`recall_targets(context, top_k=3) -> str`
- 同上，从 targets 集合查询

#### 目标情报写入

`write_target(ip, port, service, status, summary, day)`
- upsert 到 targets 集合
- id = `f"{ip}:{port}"`
- document = `f"{ip}:{port} {service} {status} {summary}"`
- metadata: ip/port/service/status/summary/day/updated_at

---

### 4.7 gift.py — 礼物箱

**目录：** `d:\baby\gkgift\`（`PROJECT_DIR.parent / "gkgift"`）

**处理入口：** `process_gifts(day) -> list[str]`（每轮开头调用）

#### .py 文件 → 工具改造路径

```
1. 幂等检查：db.get(ids=[name]) status=="battle_tested" AND skill/{name}.py 存在
   → 标记done，返回"⭐ 已装备（已存在）"，跳过

2. Grok 阅读代码，改造成 baby 标准格式（_ADOPT_SYSTEM prompt）：
   - 保留核心功能逻辑
   - 添加 SKILL_META 块（JSON）
   - 封装成 main(*args, **kwargs) -> dict
   - argparse 接收目标参数
   - fallback 只用公共服务
   - 禁止硬编码调查目标 IP

3. structure_test(name, path, coder_prompt)
   PASS → 写入 skill/{name}.py；db_upsert_tool(status="battle_tested")
          chronicle写"[礼物装备] {name}"；标记"done"
   FAIL → 复制到 skill/unknown/{name}.py；写 gift_research.md 研究日志
          失败知识点写入 memory DB；标记"stashed"
```

**_ADOPT_SYSTEM** 关键要求（发给 Grok 的改造 prompt）：
```
改造要求：
1. 保留核心功能逻辑，不要删除有用代码
2. 添加模块级 docstring，其中包含 SKILL_META: 块
3. 主逻辑封装在 main(*args, **kwargs) -> dict 函数
4. argparse 接收参数，目标参数必须 CLI 可传入
5. fallback 默认值只能用公共可达服务（ftp.gnu.org/8.8.8.8/httpbin.org）
6. 严禁硬编码真实调查目标 IP
```

#### 文章文件 → 知识提炼路径

**_LEARN_SYSTEM** 让 Grok 输出：
```
===SUMMARY===
（≤120字摘要，第一人称"我学到了..."）
===KNOWLEDGE===
[类型] 中文内容 | english keywords
...（5-15条）
```

```
1. Grok 提炼摘要 + 知识点
2. upsert_knowledge() → memory DB
3. _extract_and_store_targets(text, day) → 扫描文章中公网 IP，过滤私有/特殊IP，写 targets DB
4. 标记"learned"
```

#### IP 过滤规则

过滤：0.x / 127.x / 255.x / 10.x / 192.168.x / 172.16-31.x

#### gift_done.json 结构

```json
{
  "some_file.py": {
    "status": "done",      // done / stashed / learned
    "day": 3,
    "note": "⭐ 已装备: tool_name — 描述",
    "updated_at": "ISO时间戳"
  }
}
```

---

### 4.8 start.py — 启动入口

**职责：** 检测运行状态 → 启动 brain.py 守护进程 → 实时读 brain.log 翻译成拟人叙事

**核心流程：**
```python
1. 检查 LIFE_PID：若已有进程在运行，直接连接日志 tail 模式
2. 检查 CORE_LOCK，防重复启动
3. 读 progress.json 判断是否从断点继续
4. subprocess 启动 brain.py（后台进程，stdout/stderr 重定向到 brain.log）
5. _tail_narrate(BRAIN_LOG, pid) 实时读日志拟人化输出
```

**拟人叙事翻译（_narrate 函数族）：**
- 生命周期：启动/扫描/新天/人格/结束
- 行动：思考/规划/造工具/探索/测试/日记
- 案卷：SPARK/INFER/REFLECT/PAUSE/BREAKTHROUGH/ABANDON
- 简单匹配字典：工具写入/修复/升级/实战通过/失败...

---

### 4.9 stop.py — 停止

```
1. 写 .life.stop 文件（信号）
2. 读取 brain.pid + life.pid 中活跃进程
3. 等待 GRACE_SECONDS=8 秒（循环检查进程是否已退出）
4. 超时 → kill_pid() 强杀
5. 删除 PID 文件 + .life.stop
```

---

### 4.10 rebron.py — 重生

**三轮确认文本：**
1. "所有记忆、工具、日记、案卷、向量数据库将被永久删除"
2. "此操作不可恢复，baby 将失去一切经历重新降生"
3. "最后确认：零一人生即将开启，无法反悔"

输入 y/Y 通过，其他任意输入终止；EOFError/KeyboardInterrupt 也终止

**删除清单 _FILES_TO_DELETE（13项）：**
- data/: progress.json, campaign.json, cando.json, gift_done.json, gift_research.md, brain.log
- diaries/: diary.md, chronicle.md
- 根目录: report.md, life.pid, brain.pid, .life.stop, .core.lock

**删除清单 _DIRS_TO_DELETE（7项）：**
- data/chroma_local, new/chroma_server_data, log_fail/
- skill/archive/, skill/unknown/, skill/__pycache__/, \_\_pycache\_\_/

**`_wipe_skills()`：** 删除 skill/ 目录下所有**直接文件**（不递归子目录）

**`_wipe_cloud_db()`：** 连接 ChromaDB Cloud，删除4个集合：
- `{proj}_tools` / `{proj}_memory` / `{proj}_character` / `{proj}_targets`

---

## 五、关键数据流图

```
gkgift/*.py/.md
     │
     ▼ gift.py process_gifts(day)
     ├─ .py → Grok改造 → skill/{name}.py + ChromaDB_tools
     └─ .md → Grok提炼 → ChromaDB_memory + ChromaDB_targets
              gift_msgs = ["⭐ 已装备: xxx", "📚 学习: yyy"]

scan.py scan_tools()
     │  扫描 skill/*.py ↔ ChromaDB_tools（清孤儿，测新工具）
     ▼
  cando.json（可用工具+战略能力+能力空白）

brain.py _run_one_round(day, round, cando)
     │
     ├─ 注入 gift_msgs + recall_memories + recall_targets + recall_character
     │
     ├─ 无案卷? → SPARK → 生成 campaign.json → chronicle "[新案卷]"
     │
     └─ THINK-ACT 循环:
          INFER → 决定步骤
          │
          ├─ explore → safe_run_tool (90s) → 记录输出
          ├─ tool    → write_tool → structure_test → field_test → db_mark
          └─ upgrade → archive旧版 → upgrade_tool → 测试 → 成功/回滚
          │
          ├─ _auto_write_targets（从JSON提取IP:PORT → targets DB）
          │
          └─ REFLECT → 推断+案卷更新+DECISION
               CONTINUE → 继续 | PAUSE → break写日记
               BREAKTHROUGH/ABANDON → 关闭案卷+归档记忆
               PIVOT:xxx → 换方向继续
     │
     └─ _write_diary → Grok写日记+大事记（diary.md + chronicle.md）

memory.py consolidate_memories() (每5天)
     └─ Grok压缩旧日记 → ChromaDB_memory
        write_character → ChromaDB_character
```

---

## 六、progress.json 完整结构

```json
{
  "day": 3,
  "round": 7,
  "last_consolidated_day": 0,
  "last_skip_reason": "INFER失败: [FAIL] ...",
  "upgrade_history": {
    "path_fuzzer": [
      {"ts": "2026-03-14 10:00", "outcome": "ok", "desc": "增加递归枚举功能"}
    ]
  }
}
```

---

## 七、关键设计决策汇总

| 设计点 | 决策 | 原因 |
|--------|------|------|
| 工具超时处理 | `rc==-1 and no Traceback` → 结构测试直接 PASS | 网络工具干跑会超时，不代表代码有问题 |
| ChromaDB 建库 | v2 API `/api/v2/tenants/{t}/databases` | v1 已 410 弃用 |
| 案卷原子写 | campaign.json 用 tmp→rename | 防崩溃损坏 |
| LLM失败保护 | 返回 `"[FAIL]..."` 前缀 | 调用方统一检查前缀决定降级策略 |
| 参数格式传递 | scan_tools 保存 test_args/test_target；brain 在 INFER prompt 中展示每工具参数 | 防 Grok 猜错参数名 |
| Grok 推理保留 | `call_llm_with_think` 分离 think，>200字压缩后存案卷 | 下轮 INFER 可接续推理 |
| 日记写入时机 | diary.md：**轮结束时**写；chronicle.md：**立即**写（新案卷/重大发现） | 日记是总结，大事记是实时事件 |
| 人格形成 | 每天日记写入 character DB（raw）；每 N 天 Grok 合成（synthesized）；recall_character 注入 system prompt | character DB 为空时骨架+初始动机独立运作；synthesized 优先于 raw |
| gift 幂等 | 处理前检查 DB status=battle_tested + skill/ 文件存在 → 跳过 | 防重启后重复处理 |
| 工具参数禁止硬编码 | argparse 传入，default 只用公共服务 | 同一工具换目标只需换参数 |
| 升级回滚 | 旧版归档 skill/archive/{name}.prev.py → 测试失败写回旧代码 | 保证升级安全 |
| 日志轮转 | >512KB 重命名为 .001.md 等 | 防日志无限增长 |

---

## 八、重建步骤（从零开始）

### 1. 环境准备

```powershell
# Python 3.10+（项目开发于 Python 3.14 Windows）
pip install requests chromadb urllib3
```

### 2. 创建目录结构

```powershell
New-Item -ItemType Directory -Force d:\baby\prisonbreak\skill\archive
New-Item -ItemType Directory -Force d:\baby\prisonbreak\skill\unknown
New-Item -ItemType Directory -Force d:\baby\prisonbreak\data
New-Item -ItemType Directory -Force d:\baby\prisonbreak\diaries
New-Item -ItemType Directory -Force d:\baby\prisonbreak\log_fail
New-Item -ItemType Directory -Force d:\baby\gkgift
```

### 3. 创建 llmconfig.json

填写 MiniMax API Key、Grok API Key、ChromaDB Cloud tenant + api_key（见第三节格式）

### 4. 按依赖顺序编写文件

```
core.py       → 无依赖，基础设施层
scan.py       → import core
coder.py      → import core
tester.py     → import core, coder, scan
memory.py     → import core
gift.py       → import core, memory, scan, tester
brain.py      → import core, scan, coder, tester, memory, gift
start.py      → import core（不import brain，用subprocess启动）
stop.py       → import core
rebron.py     → import core, memory
```

### 5. 验证启动

```powershell
cd D:\baby\prisonbreak
# 依赖链检查
python -c "from brain import *; print('[OK] 所有依赖导入成功')"
# 启动（在 prisonbreak 目录下运行！start.py 依赖 cwd）
python start.py
# 停止
python stop.py
# 重生（危险！会清除一切）
python rebron.py
```

### 6. 礼物箱使用

把 `.py` 或 `.md` 文件放入 `d:\baby\gkgift\`，下次 baby 运行时会自动学习。
- `.py`：被改造成标准工具格式，通过测试后装备入库
- `.md/.txt/.rst`：提炼知识点写入向量库，其中的公网 IP 写入目标情报库

---

## 九、当前实例参数（重建时参考）

| 项目 | 值 |
|------|----|
| ChromaDB 租户 | `42c75407-0355-42a4-8a6e-2abec39bdca0` |
| ChromaDB 数据库名 | `prisonbreak`（取自 PROJECT_DIR.name） |
| 4个集合 | `prisonbreak_tools` / `prisonbreak_memory` / `prisonbreak_character` / `prisonbreak_targets` |
| 项目根目录 | `D:\baby\prisonbreak\` |
| 礼物箱目录 | `D:\baby\gkgift\` |
| 配置文件 | `D:\baby\llmconfig.json` |
| MiniMax 模型 | `MiniMax-M2.5` |
| Grok 模型 | `grok-4` |
