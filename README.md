# MusicLore

基于知识图谱的小众音乐发掘 AI Agent。围绕 Post-Punk、Shoegaze、Krautrock 三个拥有深厚地下根基和丰富影响网络的流派构建，帮助用户探索流派谱系、发现被遗忘的小众乐队、理解音乐之间的影响脉络。

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Wikidata   │     │ MusicBrainz  │     │   Last.fm    │
│  (SPARQL)   │     │    (API)     │     │    (API)     │
└──────┬──────┘     └──────┬───────┘     └──────┬───────┘
       │                   │                    │
       └───────────┬───────┴────────────────────┘
                   ▼
          ┌────────────────┐
          │ Entity Resolver│  ← 合并 + 去重
          └───────┬────────┘
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
┌─────────────┐     ┌───────────────┐     ┌───────────┐
│  NetworkX   │     │   ChromaDB    │     │ Wikipedia  │
│  Knowledge  │     │   (RAG Index) │     │   Texts    │
│    Graph    │     │ all-MiniLM-L6 │     │           │
└──────┬──────┘     └───────┬───────┘     └───────────┘
       │                    │
       └────────┬───────────┘
                ▼
        ┌───────────────┐
        │  LangGraph    │  ← 4 tools: KG query, RAG search,
        │  Agent (Qwen) │    web search, YouTube embed
        └───────┬───────┘
                ▼
        ┌───────────────┐     ┌───────────────┐
        │  FastAPI       │────▶│   Streamlit   │
        │  /chat         │     │   Frontend    │
        └───────────────┘     └───────────────┘
```

**技术栈概览：**

- **知识图谱**：NetworkX 有向图，持久化为 JSON，存储艺术家、流派、厂牌及其影响关系
- **RAG**：ChromaDB 本地向量数据库 + all-MiniLM-L6-v2 embedding，对 Wikipedia 语料做语义检索
- **LLM Agent**：LangGraph 构建的工具调用循环，使用通义千问（Qwen）作为推理引擎
- **前端**：Streamlit 对话界面，支持时间线图表、推荐卡片、知识微课等可视化渲染

## Data Sources

| 数据源 | License | 获取内容 |
|--------|---------|----------|
| [Wikidata](https://www.wikidata.org/) | CC0 | 艺术家 QID、流派归属、影响关系、成立年份 |
| [MusicBrainz](https://musicbrainz.org/) | CC0 | 艺术家类型、活跃年份、所属地区、标签、厂牌与成员关系 |
| [Last.fm](https://www.last.fm/) | API Terms | 听众数量、播放次数、用户生成标签 |
| [Wikipedia](https://en.wikipedia.org/) | CC BY-SA | 流派与艺术家的百科文本（用于 RAG 语义检索） |

## Quick Start

### 1. 创建 conda 环境

```bash
conda create -n musiclore python=3.11 -y
conda activate musiclore
```

### 2. 安装依赖

```bash
pip install musicbrainzngs SPARQLWrapper httpx networkx chromadb \
    sentence-transformers langchain langchain-openai langgraph \
    langchain-community fastapi uvicorn wikipedia python-dotenv \
    streamlit streamlit-agraph plotly ddgs
```

### 3. 配置 `.env`

编辑 `musiclore/.env`，填入你的 API Key：

```
QWEN_API_KEY=sk-your-key-here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
LASTFM_API_KEY=your-lastfm-key
```

- `QWEN_API_KEY`：阿里云百炼平台的 API Key，用于调用通义千问模型
- `LASTFM_API_KEY`：Last.fm API Key，用于获取艺术家听众数据

### 4. 初始化数据（一次性，约 40 分钟）

```bash
python scripts/seed_data.py
```

该脚本按顺序执行：从 Wikidata 抓取流派与艺术家 → MusicBrainz 补充详情 → Last.fm 获取听众数据 → 合并去重 → 构建知识图谱 → 抓取 Wikipedia 文本 → 构建 RAG 向量索引。

中间步骤的原始数据和处理结果均缓存在 `data/cache/` 目录下，重跑时已缓存的 API 请求不会重复发送。

### 5. 启动应用

终端 1 — API 服务：
```bash
python api/server.py
```

终端 2 — 前端界面：
```bash
streamlit run frontend/app.py --server.port 8501
```

浏览器打开 http://localhost:8501 即可使用。

## Project Structure

```
musiclore/
├── data/                    # 数据抓取与处理
│   ├── cache/               # 缓存的 API 响应与处理后的数据
│   ├── wikidata.py          # Wikidata SPARQL 查询
│   ├── musicbrainz.py       # MusicBrainz API 客户端
│   ├── lastfm.py            # Last.fm API 客户端
│   ├── wikipedia_text.py    # Wikipedia 文章抓取
│   ├── entity_resolver.py   # 多源数据合并与去重
│   └── seed_genres.json     # 种子流派 QID
├── graph/                   # 知识图谱（NetworkX）
│   ├── build_graph.py       # 从合并数据构建图谱
│   ├── queries.py           # 4 种查询函数（时间线、影响链、上下文、子图）
│   └── schema.py            # 节点/边类型常量
├── rag/                     # 检索增强生成（RAG）
│   ├── chunker.py           # LangChain 文本分块
│   └── retriever.py         # ChromaDB 向量检索
├── agent/                   # LLM Agent
│   ├── llm_config.py        # 通义千问 LLM 配置
│   ├── tools.py             # 4 个 LangChain 工具
│   ├── prompts.py           # System Prompt
│   └── graph_agent.py       # LangGraph Agent 循环
├── api/
│   └── server.py            # FastAPI POST /chat 端点
├── frontend/
│   └── app.py               # Streamlit 对话界面
├── scripts/
│   └── seed_data.py         # 一键数据初始化
├── .env                     # API Keys（不提交到 Git）
└── .gitignore
```

## License

MIT
