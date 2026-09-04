# RAG+LangChain构造科研知识库
构建企业级技术知识库 RAG 系统，支持多格式文档解析、语义检索、混合检索、重排、引用回答与离线评测，并通过实验对 Chunk 策略、Retriever 和 Reranker 进行效果对比。
核心目的是为了更方便地检索最新论文，了解计算机各领域最新研究、进展。
## 配置环境
```shell
# 我用的是uv来管理环境
brew install uv

# 验证uv
uv --version

# 在目录下初始化项目
uv init

# 创建python3.11环境
uv venv --python 3.11
# 激活环境 
source .venv/bin/activate

# 安装依赖
uv add sentence-transformers
uv add faiss-cpu
uv add pypdf
uv add numpy
uv add python-dotenv
uv add openai
```

也可以根据 `pyproject.toml` + `uv.lock`来复现程序

down下github仓库后，直接 `uv sync`就同步环境了