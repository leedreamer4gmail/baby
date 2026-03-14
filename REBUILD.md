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
    │   └── chronicle.md    # 大事记（两处写入：SPARK立即写 / 轮末跟随Grok响应写）
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
PROJECT_DIR   = Path(__file__).resolve().parent       # prisonbreak/
CONFIG_PATH   = PROJECT_DIR.parent / "llmconfig.json" # d:/baby/llmconfig.json
CHROMA_DATABASE  = PROJECT_DIR.name                   # "prisonbreak"
COLLECTION_NAME  = PROJECT_DIR.name + "_tools"        # "prisonbreak_tools"
DATA_DIR      = PROJECT_DIR / "data"
SKILL_DIR     = PROJECT_DIR / "skill"
DIARIES_DIR   = PROJECT_DIR / "diaries"
LOG_FAIL_DIR  = PROJECT_DIR / "log_fail"
STOP_FLAG     = PROJECT_DIR / ".life.stop"
CORE_LOCK     = PROJECT_DIR / ".core.lock"
LIFE_PID      = PROJECT_DIR / "life.pid"
BRAIN_PID     = PROJECT_DIR / "brain.pid"
BRAIN_LOG     = DATA_DIR / "brain.log"
PROGRESS_FILE = DATA_DIR / "progress.json"
CAMPAIGN_FILE = DATA_DIR / "campaign.json"
CHRONICLE_FILE = DIARIES_DIR / "chronicle.md"
DIARY_FILE    = DIARIES_DIR / "diary.md"
REPORT_PATH   = PROJECT_DIR / "report.md"
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
- **429 重试**（关键）：遇到 429 最多重试 3 次，间隔 60 / 120 / 180s
  - 重试日志：`[LLM] GROK 429限速，60s后重试(1/3)...`
  - 耗尽重试后 log_fail + 返回 `[FAIL] ...`
- 非429的 HTTPError / RequestException → 立即 log_fail + 返回 `[FAIL] ...`
- 成功后自动删除 `<think>...</think>` 标签（`re.sub`）
- 失败返回 `"[FAIL] ..."` 前缀字符串，调用方统一检查

`call_llm_with_think(name, messages, reason) -> (think_str, answer_str)`
- 与 call_llm **相同的 429 重试逻辑**（重试3次，间隔 60/120/180s）
- 分离 `<think>` 内容单独返回（供 brain 保存推理要点）
- 失败时返回 `("", "[FAIL] ...")`

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
注意：**v1 API 已 410 弃用**，务必用 v2

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
    # Unix: os.kill(pid, 0)

def kill_pid(pid):
    # Windows: taskkill /F /PID {pid}

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
  "failed_tools": [...],
  "pending_tools": [...],
  "capabilities": [
    {"name": "HTTP探测", "icon": "🌐", "count": 2,
     "summary": "工具A/工具B", "tools": ["工具A", "工具B"]}
  ],
  "capability_gaps": ["FTP渗透", "远程部署"],
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
    # 调用 call_llm("minimax", ..., temperature=0.3)
    # extract_code_block → 写入 skill/{name}.py

fix_tool(name, prompt, error) -> Path | None
    # 读取当前代码 → 构建修复prompt → MiniMax，temperature=0.2

upgrade_tool(name, old_code, upgrade_prompt) -> Path | None
    # 保留 SKILL_META（更新 version），保持 main() 接口
    # MiniMax，temperature=0.3
```

---

### 4.4 tester.py — 双阶段测试

**超时常量：** STRUCTURE_TIMEOUT=30s，FIELD_TIMEOUT=90s，MAX_FIX_ROUNDS=3

#### 阶段1：结构测试

`structure_test(tool_name, tool_path, coder_prompt) -> (bool, str)`

1. `py_compile.compile` 语法检查
2. 从 SKILL_META 读 `test_args` 干跑（`safe_run_tool(tool_path, args=test_args, timeout=30)`）
3. **关键特例：** `rc==-1 and "Traceback" not in stderr` → 直接返回 (True, "结构通过") **不调用 Grok**
4. Grok 审查：返回码/有效JSON/无Traceback/有main()/有SKILL_META
5. FAIL → `fix_tool` → 重试，最多3轮

#### 阶段2：实战测试

`field_test(name, tool_path, meta) -> (bool, str)`

1. `_generate_field_args` 生成实战参数（优先用 test_args，兜底用公共目标）
2. `safe_run_tool(tool_path, args=field_args, timeout=90)`
3. Grok 审查（4种PASS标准：有意义数据 / 优雅降级 / 明确空集合有原因 / 非crash）

---

### 4.5 brain.py — 灵魂模块（最核心）

**version: 3.0，文件约1900行**

#### 人格系统（能力驱动，每轮重新判断）

```python
def _get_persona(cando) -> (persona_str, stage_name):
    categories = {t["category"] for t in cando["available_tools"]}
    count = len(cando["available_tools"])
    if {"deploy","listen"} & categories:
        return PERSONA_DARK, "黑化"
    if ({"scan"}&categories and {"ftp"}&categories) or count >= 5:
        return PERSONA_AWAKENED, "觉醒"
    return PERSONA_NAIVE, "天真"
```

三段人格 system prompt：
- **天真**：刚出生，好奇害怕，像小朋友写日记
- **觉醒**：有眼睛和手，自信冲动，像青少年
- **黑化**：经历铸就，目标渗透/驻留/扩张

#### 阶段指南 _get_stage_guide(stage)

- 天真：感知→探索→接触，先造感知再造探索
- 觉醒：深度扫描→连接→开发部署工具→通信工具
- 黑化：扫描侦察→渗透链→建据点→扩张，碰壁换方法不换目标

#### 案卷系统

**campaign.json 完整结构：**
```json
{
  "sparked_by": "触发这个念头的场景描述（第一人称）",
  "current_goal": "具体可行的目标（必须含IP/服务/路径/协议等具体对象）",
  "goal_started_day": 1,
  "status": "active",
  "investigation_log": [
    {"day": 1, "step": 1, "target": "", "method": "步骤描述",
     "result_summary": "输出摘要", "interpretation": "推断内容"}
  ],
  "proven_dead_ends": ["方法A @ 目标X → 结论Y"],
  "active_hypotheses": ["假设Z尚未验证"],
  "promising_leads": ["线索W值得追"],
  "last_grok_reasoning": "（Grok推理压缩要点，用于下轮INFER上下文）",
  "close_reason": ""
}
```

调查日志超过 `MAX_INVESTIGATION_LOG=20` 条时，最老条目压缩进 proven_dead_ends 后删除

案卷关闭时：将 proven_dead_ends + 课题结局 upsert 到 ChromaDB_memory

#### 每轮主流程 `_run_one_round(day, round_num, cando)`

```
1. _get_persona(cando) → (persona, stage)
2. 加载 upgrade_history, last_skip_reason
3. process_gifts(day) → gift_msgs；有新工具 → scan_tools() 重扫
4. recall_memories + recall_targets + recall_character
5. load_recent_diary + _load_chronicle_tail → 上下文

--- 无活跃案卷时：SPARK 阶段 ---
6. call_llm_with_think("grok", ..., "第N天SPARK")（含429重试）
   FAIL → save_progress(last_skip_reason=...) + return (cando, True)
7. 生成 campaign → save_campaign()
   chronicle 立即写 "[新案卷] {goal[:80]}"     ← 第①处chronicle写入

--- THINK-ACT 循环 ---
while True:
    8. INFER → call_llm_with_think("grok", ..., "第N天步骤M")（含429重试）
       step_num==1 且 FAIL → save_progress + return (cando, True)  ← 跳过日记和巩固
       step_num>1  且 FAIL → break → 继续到轮末
    9. _run_step → (action_type, real_output)
   10. _auto_write_targets(real_output, day)
       - 单值路径：data.ip + data.port → write_target
       - 数组路径：data.ip + data.open_ports[] → 每端口一条（上限10）
       - ip 字段兼容：ip / host / target / scanned_host / scanned_ip
   11. REFLECT → call_llm_with_think("grok", ...）（含429重试）
   12. decision: CONTINUE/PAUSE/BREAKTHROUGH/PIVOT/ABANDON_CAMPAIGN

--- 轮末处理（INFER step1失败时完全跳过以下步骤）---
13. _write_diary(day, ...) → call_llm("grok", ...)（含429重试）
    成功：diary.md + chronicle（若Grok响应含非空===CHRONICLE===）← 第②处chronicle写入
    失败：diary.md 写 "(第{day}天，日记生成失败)"，不写chronicle
14. if day % CONSOLIDATION_INTERVAL == 0 → consolidate_memories(day)
    ← 仅在完整轮次末尾触发，INFER step1失败的轮次跳过
15. scan_tools() 重扫
16. save_progress(day, round_num, last_skip_reason="")
17. return (cando, False)
```

#### chronicle.md 写入时机（两处，必须区分）

| # | 时机 | 触发条件 | 内容格式 |
|---|------|----------|---------|
| ① | SPARK 后立即 | 成功生成新案卷目标 | `[新案卷] {goal[:80]}` |
| ② | 轮末 _write_diary 内 | Grok响应含非空 `===CHRONICLE===` 块 | Grok生成的大事记内容 |

> **不是每轮都写 chronicle**。chronicle 的①处是实时事件，②处是Grok觉得值得记录才写。

#### _brain_loop() 主循环

```python
def _brain_loop() -> None:
    ensure_dirs()
    progress = load_progress()
    start_day = progress["day"]
    cando = scan_tools()
    fail_streak = 0
    round_num = 0

    while True:
        round_num += 1
        day = start_day + round_num
        if STOP_FLAG.exists():
            save_progress(day - 1, round_num - 1)
            break

        cando, think_failed = _run_one_round(day, round_num, cando)

        if think_failed:
            fail_streak += 1
            backoff = min(10 * (2 ** fail_streak), 300)
            # 指数退避：10→20→40→...→300s上限
            if fail_streak >= 10:
                save_progress(day - 1, round_num)
                break  # 连续10次失败，退出等待手动重启
            time.sleep(backoff)
            continue

        fail_streak = 0
        time.sleep(5)  # 每轮成功后小憩5秒
```

#### Grok Prompt 格式

**SPARK 输出：**
```
===SPARK===
（第一人称冲动描述）
===GOAL===
（具体目标，必须含IP/服务/路径/协议）
```

**INFER 输出：**
```
===INFER===
（2-4句推断）
===STEP===
```json
{"type": "explore/tool/upgrade", "description": "...", "spec": {...}}
```
```

tool spec 字段：name / description / category / purpose / params / expected_output / test_args / test_target / difficulty / uses_tools

> ⚠️ **params 字段陷阱**：Grok 可能返回 `"params": {"host": "x", "port": 21}` dict，`_build_coder_prompt` 需容错转换：
> ```python
> params = json.dumps(params_raw, ensure_ascii=False) if isinstance(params_raw, (dict, list)) else str(params_raw or "无")
> ```
> `test_args` 同理。

upgrade spec 字段：target_tool / improvements / new_test_args

**REFLECT 输出：**
```
===INTERPRET===
（推断结论，1-3句）
===CAMPAIGN_UPDATE===
{"add_dead_end": "...", "remove_hypothesis": "...", "add_hypothesis": "...", "add_lead": "..."}
===DECISION===
CONTINUE / PAUSE / BREAKTHROUGH / PIVOT:新方向 / ABANDON_CAMPAIGN:理由
```

**DIARY 输出：**
```
===DIARY===
（100-200字日记，基于真实输出）
===CHRONICLE===
（大事记50字；无重大发现写"无"）
```

#### Grok 推理压缩

think 内容 >200字 时调用 Grok 压缩；压缩结果存入 `campaign["last_grok_reasoning"]`（下轮 INFER 的上下文）

#### 工具代码标准格式

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
import argparse, json
from typing import Any

def main(host: str = "ftp.gnu.org") -> dict[str, Any]:
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    try:
        results["success"] = True
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
- < 150 行，函数 ≤ 50 行；只用 Python 标准库
- `main() -> dict[str, Any]`，返回 `{"success": bool, "message": str, "data": {}}`
- argparse + `if __name__ == "__main__"`
- 目标参数全部通过 argparse 传入，**严禁硬编码调查目标**
- argparse default 只用公共服务（ftp.gnu.org / 8.8.8.8 / httpbin.org）

#### 升级流程

```
1. 验证 target_name 在 available_tools 中
2. 读旧代码 → _archive_old_tool → skill/archive/{name}.prev.py（覆盖写）
3. upgrade_tool → 生成新代码；失败 → _rollback_tool
4. structure_test → field_test
5. 成功 → db_upsert_tool(battle_tested)；失败 → _rollback_tool
6. _record_upgrade_attempt（每工具最多10条历史）
```

版本号递增：`"1.0" → "2.0"`（取整数部分+1）

---

### 4.6 memory.py — 三层记忆

**4个 ChromaDB 集合：**

| 集合 | 用途 |
|------|------|
| `{proj}_tools` | 工具库（core.py 管理） |
| `{proj}_memory` | 长期知识点（巩固结果） |
| `{proj}_character` | 人格记忆（内心独白） |
| `{proj}_targets` | 探测目标情报 |

**character / targets 初始为空是正常的：**
- **character**：`write_character` 仅在 `consolidate_memories` 成功（count > 0）后调用；若从未成功巩固，character 为空属预期
- **targets**：`_auto_write_targets` 需要工具输出含 `ip` + `port` 字段；扫描工具通常输出 `open_ports` 数组，需要 brain.py 的数组路径处理（已在 Fix C 中修复）

#### 近期记忆

`load_recent_diary(current_day, recent_days=5) -> str`
- 解析 diary.md `## 第N天` 段落，返回 `current_day - 5` 之后的条目

#### 长期记忆巩固

`consolidate_memories(current_day) -> int`

关键行为：
- **触发条件**：由 `_run_one_round` 在轮末调用（`day % CONSOLIDATION_INTERVAL == 0`）
- **只有完整轮次才触发**：INFER step1 失败 → 早返回 → 跳过
- Grok 压缩旧日记 → 每条格式 `[类型] 中文内容 | english keywords`（类型：discovery/lesson/asset）
- `upsert_knowledge(response, day_start, day_end)` → memory 集合（id: `mem_{start}_{end}_{idx}`）
- 成功（count > 0）→ `write_character(day_end, batch_text)` → `save_progress(last_consolidated_day=day_end)`
- **429 导致失败 → last_consolidated_day 不更新 → 下次5的倍数天重试**（不会跳过那些天的日记）

#### 人格记忆

`write_character(day, diary_text)` → Grok 生成 ≤200字 内心独白 → upsert id=`"character_current"`

`recall_character() -> str` — 直接 get id="character_current"

#### 语义召回

`recall_memories(context, top_k=5) -> str` — ChromaDB query，格式 `[type] text_zh (source: N-M天)`

`recall_targets(context, top_k=3) -> str` — 同上，从 targets 集合

#### 目标情报写入

`write_target(ip, port, service, status, summary, day)`
- id = `f"target_{ip}_{port}_{service}"` (`./:` 替换为 `_`)
- document = `f"{ip}:{port} {service} [{status}] {summary}"`

---

### 4.7 gift.py — 礼物箱

**目录：** `d:\baby\gkgift\`（`PROJECT_DIR.parent / "gkgift"`）

#### .py 文件 → 工具改造

```
1. 幂等检查：DB status=="battle_tested" AND skill/{name}.py 存在 → 跳过
2. Grok 改造（保留核心逻辑，添加SKILL_META，封装main，argparse，禁止硬编码目标）
3. structure_test（注意：仅结构测试，不做 field_test）
   PASS → skill/{name}.py + DB(battle_tested) + chronicle "[礼物装备]"
   FAIL → skill/unknown/{name}.py + 写 gift_research.md + memory DB记录失败
```

#### 文章文件 → 知识提炼

```
Grok提炼摘要+知识点 → memory DB
提取公网IP → targets DB（过滤私有IP：0.x/127.x/255.x/10.x/192.168.x/172.16-31.x）
```

#### gift_done.json 结构

```json
{
  "file.py": {
    "status": "done",   // done / stashed / learned
    "day": 3,
    "note": "⭐ 已装备: tool_name",
    "updated_at": "ISO时间戳"
  }
}
```

---

### 4.8 start.py — 启动入口

**必须在 `prisonbreak/` 目录下运行：**
```powershell
Set-Location D:\baby\prisonbreak; python start.py
# 或
Push-Location D:\baby\prisonbreak; python start.py; Pop-Location
```

**流程：** 检测已有进程 → 防重复启动（CORE_LOCK）→ subprocess 启动 brain.py → `_tail_narrate` 实时读 brain.log 拟人化输出

---

### 4.9 stop.py — 停止

```
写 .life.stop → 等待 GRACE_SECONDS=8s → 超时则 kill_pid() → 清理PID文件
```

---

### 4.10 rebron.py — 重生

三轮 y/Y 确认后清除一切：

**_FILES_TO_DELETE（13项）：** progress/campaign/cando/gift_done/gift_research/brain.log/diary/chronicle/report/pid/lock 文件

**_DIRS_TO_DELETE（7项）：** chroma_local / chroma_server_data / log_fail / skill/archive / skill/unknown / skill/__pycache__ / __pycache__

**`_wipe_skills()`：** 删除 skill/ 直接文件（不递归子目录）

**`_wipe_cloud_db()`：** 删除4个 ChromaDB 集合

---

## 五、关键数据流图

```
gkgift/*.py  → Grok改造 → structure_test → skill/*.py + chromadb_tools
gkgift/*.md  → Grok提炼 → chromadb_memory + chromadb_targets

scan_tools() → cando.json（可用工具/战略能力/能力空白）

_brain_loop():
  while True:
    _run_one_round(day, round, cando)
    │
    ├─ gifts → scan重扫（有新工具时）
    ├─ recall_memories + recall_targets + recall_character
    │
    ├─ SPARK（无案卷时）→ campaign.json → chronicle①立即写
    │
    └─ THINK-ACT 循环（均含429重试）:
         INFER step1 FAIL → fail_streak++ → 退避等待 → 跳过日记/巩固
         INFER step1 OK  → execute:
           explore → safe_run_tool
           tool    → write→structure_test→field_test→db_mark
           upgrade → archive→upgrade_tool→...→回滚保护
         _auto_write_targets:
           ├─ {ip, port} → write_target
           └─ {ip, open_ports:[...]} → 每端口write_target（上限10）
         REFLECT → DECISION
    │
    ├─ _write_diary（229重试）→ diary.md + chronicle②（条件写）
    ├─ consolidate_memories（day%5==0，完整轮次才触发）
    │    成功 → chromadb_memory → write_character → chromadb_character
    ├─ scan_tools()
    └─ save_progress()
    │
    think_failed? → fail_streak++ → backoff min(10×2^n, 300)s
    连续10次 → 退出等待重启
    成功 → fail_streak=0 → sleep(5)
```

---

## 六、progress.json 完整结构

```json
{
  "day": 79,
  "round": 6,
  "last_consolidated_day": 0,
  "last_skip_reason": "INFER失败: [FAIL] grok HTTP 错误: 429...",
  "upgrade_history": {
    "tool_name": [
      {"ts": "2026-03-14 10:00", "outcome": "ok", "desc": "..."}
    ]
  }
}
```

`last_consolidated_day` 缺失 = 0 = 从未成功巩固（正常初始状态）

---

## 七、关键设计决策汇总

| 设计点 | 决策 | 原因 |
|--------|------|------|
| LLM 429重试 | call_llm/call_llm_with_think 均内置重试3次（60/120/180s） | 避免限速时 baby 整天空转 |
| params 字段容错 | `_build_coder_prompt` 内 dict/list → `json.dumps`，否则 `str()` | Grok 倾向返回结构化 dict，直接 replace 会 TypeError |
| test_args 同理容错 | 与 params 相同处理 | 同上 |
| targets写入兼容 | 单值 port + open_ports 数组双路径，上限10条/次 | 扫描工具通常输出端口列表 |
| 工具超时处理 | `rc==-1 and no Traceback` → 结构测试直接 PASS | 网络工具干跑超时，不代表有代码问题 |
| ChromaDB 建库 | v2 API（v1 已 410 弃用） | — |
| 案卷原子写 | campaign.json 用 tmp→rename | 防崩溃损坏 |
| INFER step1 失败 | 返回 think_failed=True，跳过日记/巩固 | step1就失败说明API不可用，没必要继续 |
| 失败退避 | fail_streak 计数，min(10×2^n, 300)s，累计10次退出 | 防高频重试加剧API 429 |
| 轮间间隔 | 成功轮后 sleep(5) | 轻微限速保护 |
| chronicle 写入 | ①SPARK立即写；②轮末按Grok响应条件写 | 不是每轮必写，大事记只记有价值事件 |
| 巩固触发 | 仅完整轮次末尾（INFER step1失败时跳过） | 没有内容可巩固时不浪费Grok调用 |
| gift 测试 | 仅 structure_test，不做 field_test | 礼物工具来源可信，快速装备 |
| 人格切换 | 每轮根据工具能力重新判断，不持久化 | 能力退化时人格自动回退 |
| 升级回滚 | 旧版归档 archive/{name}.prev.py，测试失败写回旧代码 | 保证升级安全 |
| 日志轮转 | >512KB 重命名为 .001.md 等 | 防无限增长 |

---

## 八、重建步骤（从零开始）

### 1. 环境准备

```powershell
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

填写 MiniMax / Grok API Key，以及 ChromaDB Cloud tenant + api_key（见第三节格式）

### 4. 按依赖顺序编写文件

```
core.py       → 无依赖，基础设施层
scan.py       → import core
coder.py      → import core
tester.py     → import core, coder, scan
memory.py     → import core
gift.py       → import core, memory, scan, tester
brain.py      → import core, scan, coder, tester, memory, gift
start.py      → import core（用 subprocess 启动 brain.py，不直接 import brain）
stop.py       → import core
rebron.py     → import core, memory
```

### 5. 验证启动

```powershell
Set-Location D:\baby\prisonbreak
python -c "from brain import *; print('[OK] 所有依赖导入成功')"
python start.py   # 启动（必须在 prisonbreak/ 目录）
python stop.py    # 停止
python rebron.py  # 重生（危险！会清除一切）
```

### 6. 礼物箱使用

把文件放入 `d:\baby\gkgift\`，下次 baby 运行时自动学习：
- `.py` → Grok 改造 + structure_test → 装备入 skill/
- `.md / .txt` → 知识提炼 → memory DB；公网 IP → targets DB

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

---

## 十、已知陷阱与排坑记录

| 问题 | 现象 | 原因 | 修法 |
|------|------|------|------|
| `replace() argument 2 must be str, not dict` | 第2天 brain.log 记录 TypeError | Grok 返回 params/test_args 为 dict | `json.dumps` if dict/list，否则 `str(...)` |
| 大量429导致baby整天空转 | diary/chronicle/巩固全失败，日记停在第N天 | call_llm 无重试直接返回 `[FAIL]` | 内置重试3次（60/120/180s） |
| targets DB 永远空 | 扫描工具跑完无记录 | _auto_write_targets 只识别单值 port | 增加 open_ports 数组路径（Fix C） |
| `start.py` 报错找不到模块 | 从 `d:\baby\` 目录运行 | start.py 的 cwd 影响 import | 必须 `cd d:\baby\prisonbreak` 再运行 |
| monkey-patch `core.SKILL_DIR` 失效 | 测试时改 core.SKILL_DIR 不影响 brain.py | `from core import SKILL_DIR` 是早绑定 | 测试时 patch 使用处而非源模块 |
| character / targets 初始为空 | DB 中这两个集合无记录 | character 依赖巩固成功；targets 依赖工具输出含 ip+port | 正常状态，Fix C 修复后 targets 会逐渐积累 |
