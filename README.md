# RAG Knowledge QA

本地运行的知识库检索问答应用（RAG）。所有能力本地闭环：FastEmbed 生成 dense + sparse 混合向量，Qdrant（本地持久化）存储与检索，Ollama 提供大模型推理。无任何云端依赖。

## 特性

- **混合检索**：dense（bge-m3 向量相似度）+ 关键词（Text 匹配加权）双路召回
- **文件级去重**：top-k 检索保证「不同文件数 ≤ k」，同一文件最多保留 `chunks_per_file` 个高分 chunk，避免单个长文档垄断上下文
- **流式问答**：`/api/query` SSE 流式输出，回答强制带 `[来源: 文件名]` 引用
- **停止回答**：生成中可随时中断（`/api/query/cancel`），保留已生成的部分内容并释放模型算力
- **增量导入**：按文件内容哈希去重（重复导入秒过），支持删除已删除文件、全量重建（recreate）
- **导入进度**：导入/嵌入进度 SSE 轮询、取消导入
- **集合管理**：多知识库切换、重命名、删除（本地 sqlite 持久化）
- **在线模型切换**：右上角下拉切换 Ollama 模型（当前会话实时生效）
- **Web UI**：对话/导入/知识库管理/状态/导入记录五个页面，Tab 与会话栏可拖拽排序（顺序本地持久化），明暗主题

## 技术栈

| 组件 | 说明 |
| --- | --- |
| Python 3.9+ | 运行环境 |
| FastAPI + Uvicorn | Web 服务（SSE 流式） |
| Qdrant | 向量库（本地 `path=` 模式，sqlite 持久化） |
| FastEmbed (bge-m3) | dense (1024 维) + sparse 混合向量 |
| Ollama | 本地 LLM 推理 |
| LangChain Text Splitters | 文档分块 |
| PyMuPDF | PDF 解析 |
| Alpine.js | 前端交互 |

## 目录结构

```
├── run_server.py            # 启动入口（uvicorn，端口 8000）
├── rag.py                   # CLI 入口（typer，等价于 -m src.main）
├── pyproject.toml           # 依赖与 pytest/ruff 配置
├── .env                     # 运行配置
├── src/
│   ├── api/                 # FastAPI 路由与 schema（routes.py, app.py）
│   ├── ingest/              # 文档加载 / 分块 / 导入管线 / 进度
│   ├── retrieval/hybrid.py  # 混合检索与文件级去重
│   ├── qa/                  # chain（上下文组装 + Ollama 调用）、模型状态
│   ├── vectorstore/         # store（写入/集合操作）、embedder、naming
│   └── config.py            # 配置（.env 驱动）
├── static/                  # 前端（index.html + app.css，Alpine.js CDN）
├── data/                    # 知识库源文件（备忘录/ 等，支持 md/txt/pdf）
├── qdrant_data/             # 本地向量库持久化（storage, imports.db, 别名）
├── scripts/                 # 数据构建工具（Go 标准库文档等）
└── tests/                   # pytest（31 项）
```

## 安装

```bash
python3 -m pip install -e ".[dev]"
```

> macOS 自带 `/usr/bin/python3`（3.9.6）即可；如使用 Homebrew 的更新版本 Python 需重装依赖（`qdrant-client`、`fastembed`、`pymupdf` 等）。

### 前置依赖

- **Ollama**：`ollama serve` 后 `ollama pull qwen3:8b`（任意支持 OpenAI chat 的模型均可，如 qwen2.5）
- 首次运行会自动下载 bge-m3 嵌入模型（FastEmbed），需要联网一次

## 配置（.env）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `QDRANT_URL` | `http://localhost:6333` | 本地模式填目录路径（如 `./qdrant_data`），内存模式填 `:memory:`，也可连远程 qdrant server |
| `QDRANT_COLLECTION` | `knowledge_base` | 当前激活集合（存储名，中文会自动映射为安全文件名） |
| `DENSE_EMBEDDING_MODEL` | `BAAI/bge-m3` | 嵌入模型（1024 维 dense） |
| `OLLAMA_MODEL` | `qwen2.5` | 兜底 LLM（实际以运行时切换/`llm_model.json` 为准） |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 地址 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | 分块参数 |
| `TOP_K` | `3` | 检索目标：不同的文件数上限 |
| `CHUNKS_PER_FILE` | `3` | 每个选中文件最多保留的 chunk 数 |
| `RERANK_TOP_K` / `RRF_K` | `5` / `60` | 预留的粗排参数 |

> 切换集合时集合名经 `storage_name()` 映射为 Qdrant 合法存储名，显示名与存储名通过集合别名文件关联，重启后保持。

## 启动

```bash
/usr/bin/python3 run_server.py
```

打开 http://localhost:8000 即可使用。

服务重启期间的注意事项（本地模式）：

```bash
kill -9 $(lsof -tnP -iTCP:8000 -sTCP:LISTEN)   # 停旧进程
rm -f qdrant_data/.lock                         # 清残留锁
nohup /usr/bin/python3 run_server.py > /tmp/rag_server.log 2>&1 &
```

## 使用

### Web UI

- **💬 对话**：提问 → 流式回答，来源为 `[文件名]`；左侧会话多开、可重命名、拖拽排序
- **📥 导入**：选择目录/文件导入；同文件重复导入自动跳过；打开「重建」可全量重建当前集合
- **📖 知识库管理**：文件列表、集合（切换/重命名/删除）、向量点数
- **📊 状态**：集合、点数与模型信息
- **📚 导入记录**：历史导入会话详情

右上角下拉切换 Ollama 模型；右上角按钮切换明暗主题。

### API 要点

| 方法 & 路径 | 说明 |
| --- | --- |
| `POST /api/query` | 流式问答（SSE：`{"type":"chunk","text":...}` / 结束时 `{"type":"done","stopped":bool,...}`），body: `{question, top_k?, collection?, session_id?}`；`session_id` 用于定位/取消本次生成 |
| `POST /api/query/cancel` | 停止正在生成中的回答，body: `{session_id}`，返回 `{cancelled: bool}`；保留已输出的部分内容 |
| `POST /api/ingest` | 导入，body: `{path?, paths?, recreate?, delete_missing?}`（阻塞至完成，返回统计） |
| `GET /api/ingest/progress` / `POST /api/ingest/cancel` | 导入进度 / 取消 |
| `GET /api/status` / `GET /api/config` | 状态 / 配置 |
| `GET|POST /api/models` | 模型列表 / 切换模型 |
| `GET /api/files` / `GET /api/files/content` | 已索引文件 / 内容 |
| `POST /api/collections/switch` · `/rename` · `/delete` | 集合切换 / 重命名 / 删除 |
| `GET /api/imports` · `GET /api/imports/{id}` | 导入记录列表 / 详情 |

## 检索与问答原理

1. **召回**：`top_k` 目标文件数，候选池扩至 `max(top_k*4, 24)`；
   密集检索（bge-m3 余弦）+ 关键词匹配（`MatchText`，命中加权 `×1.1`）合并
2. **文件级去重**：按分数贪心先定 `top_k` 个**不同文件**（每个文件以其最佳 chunk 代表参选）；
   再从候选里为每个选中文件保留至多 `chunks_per_file` 个高分 chunk
3. **上下文组装**（`src/qa/chain.py`）：chunk 按分数降序拼入，总字符预算 `MAX_CONTEXT_CHARS=4000` 截断（约 2000 token，防超 `num_ctx=8192`）；`chunks_used` 反映实际喂入数
4. **回答**：仅基于检索到的 chunk 片段回答（不读整文件），`temperature=0`，强制标注 `[来源: 文件名]`

### 停止回答

- 回答生成期间，输入框发送按钮变为红色「⏹ 停止」；点击后前端调用 `POST /api/query/cancel`
- 服务端维护生成注册表（`src/qa/cancel.py`）：每路生成（按 `session_id`）进入时就登记，拿到流式响应后挂载连接句柄；取消即置位「已取消」事件并关闭对 Ollama 的连接
- Ollama 在客户端断开流时立即中止生成（不白白算完），前端收到终帧 `{"type":"done","stopped":true}` 后保留已生成的部分文本并标注「已手动停止」
- 生成结束/异常时注册表自动释放；取消不存在的生成返回 `cancelled:false`

> 说明：当前回复只使用检索到的 chunk 片段，不使用整文件内容。

## 数据与存储

- `data/`：源文档（支持 `.md` / `.txt` / `.pdf`），导入时按目录递归发现
- `qdrant_data/`：本地 qdrant 持久化（每集合一个 sqlite）、`imports.db`（导入历史/文档哈希）、`collection_aliases.json`（显示名 ↔ 存储名）、`llm_model.json`（当前模型）
- PDF 按页切分，chunk 携带 `source`（相对路径）、`filename`、`page`、`chunk_index` 元数据

## 测试与检查

```bash
/usr/bin/python3 -m pytest -q    # 31 passed
ruff check src/
```

日常修改后建议两者都跑一遍。

## 已知实现细节

- 本地 sqlite 模式（macOS sqlite 编译为 `THREADSAFE=2`）跨线程写入曾触发 `check_same_thread` 报错；`store.py` 已对所有写操作开启 `force_disable_check_same_thread=True` 并用模块级 `RLock` 串行化，导入与集合操作可并发触发
- 大模型推理串行排队：同一时间只有一个会话在生成，其余会话的输入不阻塞（每会话瞬态 `busy` 状态）
- 本机 qwen3:8b 首个 token 延迟约 20+ 秒（prefill 慢），回答生成流畅后取消可即时中断
- `src/qa/cancel.py` 的注册表/取消逻辑有独立单元测试（`tests/test_cancel.py`）

## 脚本

- `scripts/build_stdlib.py`：抓取 Go 标准库中文文档（studygolang pkgdoc + `go doc -all` 英文补洞），生成 `data/go/go-docs/00-标准库/`
- `scripts/fetch_go_docs.py`：抓取 golang.ac.cn 中文文档，生成可导入的 markdown
- `export_notes.py`：通过 AppleScript 把 Apple 备忘录按文件夹导出为 markdown 到 `data/备忘录/`