# Baby / Prisonbreak

This is a set of questions to test how well a programming tool works.

---

## 如何获取 Personal Access Token（API 密钥）

本项目需要三个服务的 API 密钥才能运行，配置文件为项目根目录下的 `llmconfig.json`（参考模板 `llmconfig_yours.json`）。

### 1. MiniMax API Key

MiniMax 用于代码生成（`write_tool` / `fix_tool` / `upgrade_tool`）。

1. 访问 [MiniMax 开放平台](https://www.minimaxi.com/user-center/basic-information/interface-key)
2. 注册或登录账号
3. 进入「用户中心」→「接口密钥」
4. 点击「创建新密钥」，复制生成的 API Key（格式类似 `eyJh...`）
5. 将其填入 `llmconfig.json` 的 `minimax.api_key` 字段

### 2. Grok (xAI) API Key

Grok 用于决策、规划和工具质量评审。

1. 访问 [xAI 开发者平台](https://console.x.ai/)
2. 注册或登录 xAI 账号
3. 进入「API Keys」页面
4. 点击「Create API Key」，复制生成的 API Key（格式为 `xai-...`）
5. 将其填入 `llmconfig.json` 的 `grok.api_key` 字段

### 3. ChromaDB API Key（云端向量数据库）

ChromaDB 用于存储工具知识库、角色记忆和目标信息。

1. 访问 [ChromaDB Cloud](https://www.trychroma.com/)
2. 注册或登录账号
3. 创建一个新的 Tenant（租户），记录 **Tenant ID**（UUID 格式）
4. 在 Tenant 设置中创建 API Key（格式为 `ck-...`）
5. 将 Tenant ID 填入 `llmconfig.json` 的 `chromadb.tenant` 字段
6. 将 API Key 填入 `llmconfig.json` 的 `chromadb.api_key` 字段

---

## 配置示例

将以下内容保存为项目根目录的 `llmconfig.json`，替换 `<...>` 部分为你的实际密钥：

```json
{
  "minimax": {
    "api_key": "<你的 MiniMax API Key>",
    "model": "MiniMax-M2.5",
    "base_url": "https://api.minimax.io/v1"
  },
  "grok": {
    "api_key": "<你的 xAI Grok API Key>",
    "models": {
      "default": "grok-4.20-beta-0309-reasoning",
      "review": "grok-4.20-multi-agent-beta-0309",
      "fast": "grok-4.20-beta-0309-non-reasoning",
      "cheap": "grok-4-1-fast-reasoning"
    },
    "base_url": "https://api.x.ai/v1"
  },
  "chromadb": {
    "tenant": "<你的 ChromaDB Tenant ID>",
    "api_key": "<你的 ChromaDB API Key>",
    "database": "prisonbreak"
  }
}
```

> ⚠️ **注意**：`llmconfig.json` 包含敏感密钥，已被 `.gitignore` 排除，请勿提交到版本库。

---

## 快速启动

配置完成后，进入 `prisonbreak` 目录并启动：

```bash
cd prisonbreak
python start.py
```

停止运行：

```bash
python stop.py
```

详细部署说明参见 [REBUILD_prisonbreak.md](REBUILD_prisonbreak.md)。
