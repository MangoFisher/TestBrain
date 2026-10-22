# TestBrain

> 基于大语言模型的智能测试平台，聚焦手工&接口测试用例生成、评审与知识复用、java源码分析，帮助测试团队打造高效、可扩展的“AI 测试助手”。

## 🧭 项目概览

TestBrain 通过 Django + LangChain + 多模型接入的方式，提供以下核心能力：

- **多 Agent 协同**：针对不同测试场景提供专用智能体（测试用例生成、评审、PRD 分析、接口用例生成、Java 代码分析等）。
- **多 LLM 供应商**：支持 DeepSeek、Qwen 等模型，并可按 Agent 维度配置默认模型/参数，前端也可手动切换。
- **知识库加持**：集成 Milvus 向量数据库与 BGEM3 Embedding和阿里云嵌入模型，支持文档解析、入库、向量检索与上下文增强。
- **可扩展架构**：模块化的 LLM 工厂、Agent 封装、知识库服务，便于新增模型、Agent 或自定义流程。

## 🛠️ 功能模块

| 模块 | 功能 | 关键实现 |
| --- | --- | --- |
| **AI Agents** | - `test_case_generator`：根据需求生成用例（支持同步/异步调用 LLM）<br>- `test_case_reviewer`：对生成的用例进行评审与打分<br>- `prd_analyzer`：解析 PRD，提炼测试点/场景（内置 JSON 修复兜底）<br>- `iface_case_generator`：基于接口描述生成测试用例<br>- `java_code_analyzer`：分析 Java 代码并梳理潜在测试点,依赖自封装java源码分析服务https://github.com/MangoFisher/java-analyzer | `apps/ai_agents/*`，配合统一的 Prompt 管理与服务调用 |
| **LLM 集成** | - `LLMServiceFactory` 动态创建模型客户端<br>- `get_agent_llm_configs()` 返回 Agent 默认模型与 Provider 列表<br>- 支持同步 `invoke` 与异步 `ainvoke` | `apps/llm/base.py` / `apps/llm/utils.py` |
| **知识库** | - `KnowledgeConfig.ready()` 预热 Milvus + 嵌入模型单例<br>- `KnowledgeService` 封装向量入库、检索、相似度匹配<br>- 支持多格式文档解析、批量嵌入与检索 | `apps/knowledge/*` |
| **核心应用** | - Web 页面与 API（Django View）<br>- 用例管理（`TestCase` 模型）<br>- 配置管理、日志、权限预留 | `apps/core/*` |

## 🏗️ 技术栈 & 服务依赖

- **运行框架**：Python 3.12+、Django 6.0.2、LangChain
- **数据库**：MySQL 8.x（通过 `mysqlclient` 连接，**本地运行必须准备**）
- **向量数据库**：Milvus 2.x（**可选**，默认关闭，见「可选依赖」）
- **Embedding 模型**：阿里云 `text-embedding-v4`（默认）或本地 `BAAI/bge-m3`（可选，通过 `sentence-transformers`）
- **完整依赖清单**：见 `requirements.txt`

> 说明：向量库与嵌入模型只在 `ENABLE_MILVUS=true` 时初始化。未部署 Milvus 的机器上项目仍可正常启动，仅知识库相关接口不可用。

## 📁 项目结构

```
TestBrain/
├── apps/
│   ├── ai_agents/            # 各类智能体实现
│   │   ├── test_case_generator/
│   │   ├── test_case_reviewer/
│   │   ├── prd_analyzer/
│   │   ├── iface_case_generator/
│   │   └── java_code_analyzer/
│   ├── core/                 # 公共视图、模型、页面
│   ├── knowledge/            # Milvus & Embedding 服务
│   ├── llm/                  # LLM 工厂、Provider 定义
│   └── utils/                # 日志、SSE 等公共工具
├── config/                   # Django 配置（INSTALLED_APPS、数据库、LLM 设置等）
├── templates/                # 页面模板
├── static/                   # 静态资源
├── .env.example              # 环境变量样例（复制为 .env 使用）
├── requirements.txt          # 依赖列表
└── manage.py
```

## 🚀 快速开始（本地运行）

> 下面是一条**从零到启动**的完整路径，按顺序执行即可。所有命令都在项目根目录下直接复制运行。

### 0. 前置要求

- **Python 3.12 及以上**（`Django==6.0.2` 要求 Python ≥ 3.12，不支持 3.10/3.11）
- **MySQL 8.x**（必需）
- **Docker**（可选，仅用于启动 Milvus，见「可选依赖」）
- **仅 macOS 需要**：`mysqlclient` 需要 MySQL 客户端库与 pkg-config

  ```bash
  brew install mysql-client pkg-config
  export PKG_CONFIG_PATH="$(brew --prefix mysql-client)/lib/pkgconfig"
  ```

### 1. 获取代码

```bash
git clone https://github.com/MangoFisher/TestBrain.git
cd TestBrain
```

### 2. 创建并激活虚拟环境

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows 使用 .venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

然后编辑 `.env`，**至少**填写数据库信息：

```dotenv
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的MySQL密码
MYSQL_DB=test_brain_db
```

如需使用 AI 生成/评审功能，再填写大模型 Key（见 `.env.example` 注释）：

```dotenv
DEEPSEEK_API_KEY=你的Key
QWEN_API_KEY=你的Key
```

### 5. 创建数据库

```bash
mysql -uroot -p -e "CREATE DATABASE test_brain_db DEFAULT CHARACTER SET utf8mb4;"
```

> 没有本地 MySQL 时，也可以用 Docker 起一个：
> ```bash
> docker run -d --name testbrain-mysql \
>   -e MYSQL_ROOT_PASSWORD=your_password \
>   -e MYSQL_DATABASE=test_brain_db \
>   -p 3306:3306 mysql:8
> ```
> 此时 `.env` 中 `MYSQL_PASSWORD` 填上面设置的 `your_password`。

### 6. 初始化数据表

```bash
python manage.py check      # 配置自检，预期输出：System check identified no issues
python manage.py migrate    # 建表
```

### 7. 启动服务

```bash
python manage.py runserver 0.0.0.0:8000
```

### 8. 验证启动成功

- 终端出现：`Starting development server at http://0.0.0.0:8000/`
- 浏览器访问 <http://127.0.0.1:8000/> → 打开首页仪表盘（统计卡片 + 最近用例列表）
- 浏览器访问 <http://127.0.0.1:8000/admin/> → 打开 Django 管理后台登录页
- 打开任一 Agent 页面（如 <http://127.0.0.1:8000/test_case_generator/>）→ 表单正常渲染

### 常见启动问题

| 现象 | 原因与处理 |
| --- | --- |
| `ModuleNotFoundError: No module named 'django'` | 虚拟环境没激活，先执行第 2 步的 `source .venv/bin/activate` |
| 安装依赖时 `mysqlclient` 编译失败 | macOS 未装 MySQL 客户端库，见第 0 步 |
| `django.db.utils.OperationalError: (2002, "Can't connect to MySQL server")` | MySQL 没启动，或 `.env` 中 `MYSQL_*` 填写不正确 |
| `(1049, "Unknown database 'test_brain_db'")` | 跳过第 5 步未建库，先创建数据库再执行 `migrate` |
| 调用 AI 接口报 `api_key` 相关错误 | `.env` 未填写对应 provider 的 Key（`DEEPSEEK_API_KEY` / `QWEN_API_KEY`）。首页与页面渲染不受影响 |

## ⚙️ 配置说明

所有可配置项集中在项目根目录的 `.env` 文件中，变量名与含义以 `.env.example` 为准；`config/settings.py` 启动时会自动加载该文件（无需额外设置 `DJANGO_SETTINGS_MODULE`）。

| 变量 | 作用 | 是否必填 |
| --- | --- | --- |
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DB` | MySQL 连接信息，对应 `settings.py` 的 `DATABASES` | 必填 |
| `DEEPSEEK_API_KEY` / `QWEN_API_KEY` | 大模型调用密钥，变量名规则为 `<PROVIDER 名称大写>_API_KEY` | 使用 AI 功能时必填 |
| `ENABLE_MILVUS` | 是否启用 Milvus 向量库与嵌入模型，默认 `false` | 可选 |
| `MILVUS_HOST` / `MILVUS_PORT` / `MILVUS_DB` / `MILVUS_COLLECTION` | Milvus 连接与集合配置，对应 `settings.py` 的 `VECTOR_DB_CONFIG` | 启用 Milvus 时必填 |
| `EMBEDDING_PROVIDER` | 嵌入模型来源：`aliyun`（阿里云 text-embedding-v4，默认）或 `local`（本地 BGE-M3） | 可选 |
| `JAVA_ANALYZER_SERVICE_URL` | Java 源码分析服务地址 | 可选 |

另外两项配置在 `config/settings.py` 中维护：

- `LLM_PROVIDERS`：可用的模型供应商及其 `model` / `base_url` / `temperature` 等参数，`default_provider` 指定全局默认供应商。
- `AGENT_LLM_DEFAULTS`：按 Agent 指定默认供应商（如 `test_case_generator` 使用 `deepseek`）。前端下拉列表由 `providers` 渲染，可手动切换；后端通过 `get_agent_llm_configs(agent_name)` 读取。

知识库单例的初始化位于 `apps/knowledge/apps.py` 的 `KnowledgeConfig.ready()`，仅在 `ENABLE_MILVUS=true` 时创建 `embedder` 与 `vector_store`（初始化失败只记录告警，不阻断启动）；业务侧通过 `KnowledgeService()` 复用该单例。

## 🔌 可选依赖

以下两项为可选能力，未部署时对应功能不可用，但**不影响项目启动和其余页面**。

### Milvus 向量库（知识库检索）

1. 启动 Milvus（需 Docker，脚本会拉取并启动 `milvusdb/milvus:v2.5.7`，监听 19530 端口）：

   ```bash
   bash standalone_embed.sh start      # 停止用 stop，删除容器与数据用 delete
   ```

2. 在 `.env` 中开启并配置：

   ```dotenv
   ENABLE_MILVUS=true
   MILVUS_HOST=127.0.0.1
   MILVUS_PORT=19530
   MILVUS_DB=default
   MILVUS_COLLECTION=vv_knowledge_collection
   ```

3. 若 `EMBEDDING_PROVIDER=aliyun`，还需填写 `QWEN_API_KEY`；改为 `local` 则首次运行会自动下载 `BAAI/bge-m3` 模型。

### Java 源码分析服务

`java_code_analyzer` 页面依赖一个独立部署的服务（**不在本仓库内**），仓库地址：<https://github.com/MangoFisher/java-analyzer>。

- 本地启动该服务后，在 `.env` 中设置 `JAVA_ANALYZER_SERVICE_URL=http://127.0.0.1:8089`（默认值即是它）。
- 未部署该服务时，仅 `java_code_analyzer` 相关页面不可用。

## 🧠 Agent 详情

| Agent | 入口页面 | 描述 |
| --- | --- | --- |
| 测试用例生成 | `/test_case_generator/` | 根据需求文本生成结构化测试用例列表，支持自定义设计方法、测试类型、生成条数，并可保存到数据库。 |
| 测试用例评审 | `/test_case_reviewer/` | 对既有用例进行评审，输出风险 & 改进建议。 |
| PRD 分析 | `/prd_analyzer/` | 解析 PRD Markdown，产出测试点与测试场景；内置 JSON 修复逻辑以提升容错。 |
| 接口用例生成 | `/iface_case_generator/` | 根据接口定义生成测试思路，支持模型切换。 |
| Java 代码分析 | `/java_code_analyzer/` | 静态分析 Java 源码，输出潜在缺陷与测试关注点。 |

## 📚 知识库最佳实践

为了让 LLM 生成的测试用例更加贴合业务，建议：

1. 上传与需求相关的文档：PRD、设计文档、API 文档、过往测试用例、UI 设计稿等。
2. 确保文件命名规范、内容清晰，便于向量检索与上下文匹配。
3. 使用知识库检索功能，确认相关内容已写入 Milvus 并能搜索到。

## 📼 演示视频

测试用例生成、测试用例评审、知识库文档上传的功能演示视频由作者本地保留，**未纳入版本库**（以控制仓库体积）。如需体验，按上面的「快速开始」启动项目后直接操作页面即可。

## 🧪 常见问题（FAQ）

**Q1. 为什么日志里多次出现 “正在加载 BGE-M3 模型…”？**  
使用本地嵌入模型（`EMBEDDING_PROVIDER=local`）时，默认 `runserver` 会启动监视进程 + 工作进程，两次初始化属正常现象。上线部署（Gunicorn/Uvicorn）或使用 `--noreload` 可验证单例。

**Q2. LLM 输出的 JSON 仍解析失败怎么办？**  
系统已内置 `_basic_json_fix()` 处理未转义换行、中文引号、缺逗号等常见问题。如仍失败，建议检查 Prompt 或手动修正模型输出。

**Q3. 如何新增模型供应商？**  
在 `LLM_PROVIDERS` 中新增配置，并在 `LLMServiceFactory` 里实现创建逻辑。随后可在 `AGENT_LLM_DEFAULTS` 或前端下拉中引用，API Key 通过 `<PROVIDER 名称大写>_API_KEY` 环境变量提供。

**Q4. 是否支持异步调用？**  
`TestCaseGeneratorAgent` 已支持 `async_generate`，可在异步视图或任务中直接 `await` 调用，LangChain 内部使用 `ainvoke`。