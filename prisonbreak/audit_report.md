# exam10 代码审计报告

> 审计时间: 2026-03-12 | 审计范围: cc/exam10 全部源文件  
> 审计依据: lawcode.md 编码法典  
> 当前状态: 运行中（第79天 → 第80天，PID 24828/25032）  
> 复核时间: 2026-03-12 | 复核结论: 6/13条误报已剔除，4项已修复

---

## 一、已修复的问题

### 1. ✅ 进度文件竞态写入（progress.json）— 已修复

**修复**: `consolidate_memories()` 不再独立读写 `PROGRESS_FILE`，改用 `load_progress()` 读取 + `save_progress()` 的原子合并写入。`load_progress()` 返回完整字段（含 `last_consolidated_day`）。

### 2. ✅ PID 复用导致误判进程存活 — 已修复

**修复**: `acquire_lock()` 调用 `is_pid_alive(old_pid, expect_cmd="python")`，验证进程命令行含 "python" 才认定存活，防止 Windows PID 复用误判。

### 3. ✅ ChromaDB 无重连机制 — 已修复

**修复**: `memory.py` 的 `get_memory_collection()` 增加异常捕获 + `reset_chroma_client()` 自动重连；`core.py` 的 `_reset_chroma_client()` 改为公开函数 `reset_chroma_client()`。

### 4. ✅ brain.py 动作解析无互斥 — 已修复

**修复**: `_parse_think_response()` 的 TOOL/EXPLORE/UPGRADE 解析从 `if...if...if` 改为 `if...elif...elif`，防止 LLM 同时返回多个动作块时产生冲突覆盖。

---

## 二、原报告误报项（代码已正确，无需修改）

| # | 原报告声称 | 实际代码 |
|---|-----------|---------|
| 3 | `shlex.split(args)` 无 Windows 适配 | `shlex.split(args, posix=(env.os_type != "Windows"))` 已正确处理 |
| 4 | `_daemon_loop` 文件句柄泄漏 | `try/finally` + `brain_log_f = None` 已完整保护 |
| 6 | `verify=False` 全局禁用 SSL | `_SSL_VERIFY` 默认 True，所有请求用 `verify=_SSL_VERIFY` |
| 8 | 日记/大事记无大小限制 | `_rotate_if_needed()` + `_LOG_MAX_BYTES = 512*1024` 已实现轮转 |
| 9 | `stop.py` 不清理 STOP_FLAG | 末尾已有 `STOP_FLAG.unlink(missing_ok=True)` |
| 12 | `extract_code_block()` 只取第一个 | 已用 `max(matches, key=len)` 取最长 |

---

## 三、仍存在的中等问题（建议近期修复）

### 3. 🔴 `shlex.split(args)` 在 Windows 上行为不正确

**文件**: core.py `safe_run_tool()`  
**问题**: `shlex.split()` 默认使用 POSIX 模式解析，会将 `\` 视为转义符。在 Windows 路径或参数中包含反斜杠时会导致参数解析错误。

```python
# 当前代码
cmd.extend(shlex.split(args))  # POSIX 解析，Windows 路径中 \ 会出问题
```

**违反 lawcode**: "跨平台 - 所有平台差异封装成统一接口"

**修复方案**:
- **方案A**: `shlex.split(args, posix=(env.os_type != "Windows"))`
- **方案B**: 封装为 `safe_split_args(args: str) -> list[str]`，内部根据 OS 选择解析方式

---

### 4. 🔴 文件句柄泄漏风险（守护进程日志）

**文件**: core.py `_start_brain()` / `_monitor_brain()` / `_daemon_loop()`  
**问题**: `_start_brain()` 打开 `brain_log_f` 并返回给 `_monitor_brain()` 关闭。如果在 `_start_brain` 和 `_monitor_brain` 之间发生异常，文件句柄泄漏。

```python
# 当前代码 (_daemon_loop)
brain_pid, brain_log_f = _start_brain(env, child_env, log_mode)
# ↑ 如果这里之后、_monitor_brain 之前出异常，brain_log_f 泄漏
if _monitor_brain(brain_pid, brain_log_f):
    return
```

**违反 lawcode**: "生产就绪 - 异常要具体，优雅降级"

**修复方案**:
- 用 `try/finally` 包裹 `_daemon_loop` 中的循环体，确保 `brain_log_f.close()`
- 或者让 `_start_brain` 内部管理文件句柄生命周期（用 context manager）

---

## 二、中等问题（建议近期修复）

### 5. 🟡 全局可变缓存违反无状态原则

**文件**: core.py `_ENV_CACHE` / `_CONFIG_CACHE`  
**问题**: `_CONFIG_CACHE` 配置文件修改后不自动刷新，必须重启进程。  
**建议**: 增加文件 mtime 检测（当前已有 `_CONFIG_MTIME` 但间隔可能过短导致 stale）

---

### 10. 🟡 scan.py `MAX_AUTO_TEST` 限制导致工具永远待测

**文件**: scan.py `_test_untracked()`  
**问题**: 每次扫描最多自动测试 3 个未入库工具。大量新增工具时需多轮消化。  
**建议**: brain 感知到待测工具过多时主动增加测试规模

---

### 11. 🟢 `_detect_public_ip()` 在无网络时阻塞 24 秒

**文件**: core.py  
**问题**: 尝试 3 个 URL × 8s timeout = 24s，无网时延迟启动。  
**建议**: 限制总超时为 10s 或并发检测

---

### 13. 🟢 `_build_coder_prompt` 模板占位符碰撞风险

**文件**: brain.py `_SKILL_CODE_TEMPLATE`  
**问题**: `__NAME__` / `__DESC__` 等占位符通过 `.replace()` 替换，LLM 生成内容含同样模式时会意外替换。  
**建议**: 替换后增加残留占位符检查

---

## 四、Lawcode 合规性检查清单

| 法则 | 状态 | 说明 |
|------|------|------|
| 类型安全（annotations + typing） | ✅ 合格 | 所有模块有 `from __future__ import annotations`，函数有类型注解 |
| 单一职责（函数 ≤50 行） | ✅ 合格 | 所有函数均在 50 行以内 |
| 最小依赖 | ✅ 合格 | 第三方库: requests, chromadb（有充分理由） |
| 生产就绪（异常具体） | ⚠️ 基本合格 | 大部分异常具体，但 ChromaDB 无重连降级 |
| 跨平台 | ⚠️ 需改进 | `shlex.split` 未区分平台（问题#3） |
| 简洁文档 | ✅ 合格 | 模块/函数均有 docstring，逻辑块用 `# ===` 分隔 |
| 代码生成 | ⚠️ 需改进 | 占位符替换后无残留检查（问题#13） |
| 环境检测 | ✅ 合格 | `get_runtime_env()` 返回 frozen dataclass |
| 平台抽象 | ⚠️ 需改进 | `shlex.split` 未封装（问题#3） |
| 多进程协调 | ⚠️ 需改进 | progress.json 竞态（问题#1） |
| 子进程隔离 | ✅ 合格 | PID 文件、cwd 显式指定、平台分离 |
| 状态幂等性 | ✅ 合格 | 进度文件可恢复，目录 mkdir(exist_ok=True) |
| 自愈型日志 | ✅ 合格 | brain.py 失败日志包含 Context/Action/Error/Suggestion |
| 无状态执行 | ⚠️ 需改进 | 全局缓存违反原则（问题#5） |
| 全局变量禁用 | ❌ 不合格 | 3 个全局可变缓存（问题#5） |
| 测试文件清理 | ⚠️ 需改进 | 临时文件清理不在 finally 中（问题#14） |

---

## 五、运行状态快照

```
进程状态:               3 个 Python 进程运行中
PID 映射:               life.pid=24828(core.py)  brain.pid=25032(brain.py)
锁文件:                 .core.lock 存在（正常）
停止标志:               .life.stop 不存在（正常）
当前进度:               第 79 天，最后巩固到第 70 天
可用工具:               15 个实战通过
失败工具:               9 个（含刚失败的 improved_http_dir_enum_http）
人格阶段:               黑化
最新活动:               第80天思考中...
```

---

## 六、修复优先级建议

| 优先级 | 问题编号 | 修复项 |
|--------|----------|--------|
| P0 紧急 | #1 | progress.json 竞态写入 |
| P0 紧急 | #4 | 文件句柄泄漏 |
| P1 高   | #2 | PID 复用误判 |
| P1 高   | #3 | shlex.split 跨平台 |
| P1 高   | #6 | SSL 验证禁用 |
| P2 中   | #5 | 全局缓存重构 |
| P2 中   | #7 | ChromaDB 重连 |
| P2 中   | #8 | 日志轮转 |
| P2 中   | #9 | stop.py 清理标志 |
| P3 低   | #10-#15 | 其余优化项 |

---

*报告完毕。以上问题均基于静态审查和 lawcode 逐条比对，未修改任何代码。*
