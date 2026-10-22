"""
Django settings for test_brain project.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载项目根目录下的 .env（文件不存在时静默跳过）。
# 必须放在读取任何环境变量之前，否则下方的数据库、Milvus、模型 Key
# 等配置会读不到 .env 中填写的值。
load_dotenv(BASE_DIR / ".env")

# 配置 Hugging Face 国内镜像，用于 SentenceTransformer 模型下载
# 如需换源，在 .env 中设置 HF_ENDPOINT 覆盖即可
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# 采用北京时间
TIME_ZONE = 'Asia/Shanghai'
USE_TZ = False

# 确保项目根目录在Python路径中
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    '*'
]

# 是否启用Milvus向量库与向量模型。
# 默认关闭，使项目在没有 Milvus / 嵌入模型 Key 的机器上也能正常启动；
# 需要知识库检索功能时，在 .env 中设置 ENABLE_MILVUS=true 并配置 MILVUS_* 与 QWEN_API_KEY。
ENABLE_MILVUS = os.getenv("ENABLE_MILVUS", "false").strip().lower() in ("1", "true", "yes", "on")

# 添加上传测试用例文件目录配置
MEDIA_ROOT = os.path.join(BASE_DIR, 'uploads')
MEDIA_URL = '/uploads/'

# 允许所有域名跨域（开发环境用，生产环境需调整）
CORS_ORIGIN_ALLOW_ALL = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 自定义应用
    'apps.core',
    'apps.llm',
    # 'apps.knowledge',
    'apps.knowledge.apps.KnowledgeConfig',
    'apps.ai_agents.iface_case_generator.apps.IfaceCaseGeneratorConfig',
    'apps.ai_agents.java_code_analyzer.apps.JavaCodeAnalyzerConfig',
    'apps.ai_agents.prd_analyzer.apps.PrdAnalyzerConfig',
    'apps.ai_agents.test_case_generator.apps.TestCaseGeneratorConfig',
    'apps.ai_agents.test_case_reviewer.apps.TestCaseReviewerConfig',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# 数据库连接信息全部来自环境变量（见项目根目录 .env.example）。
# 首次运行前需先创建好数据库，例如：
#   CREATE DATABASE test_brain_db DEFAULT CHARACTER SET utf8mb4;
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQL_DB', 'test_brain_db'),
        'USER': os.getenv('MYSQL_USER', 'root'),
        'PASSWORD': os.getenv('MYSQL_PASSWORD', ''),
        'HOST': os.getenv('MYSQL_HOST', '127.0.0.1'),
        'PORT': os.getenv('MYSQL_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
USE_I18N = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# LLM提供商配置
LLM_PROVIDERS = {
    'default_provider': 'deepseek',
    'deepseek': {
        'name': 'DeepSeek',
        # 'model': 'deepseek-chat', #可以切换, deepseek-reasoner即【深度思考】模式, 可能会稍微慢一些
        # 'api_base': 'https://api.deepseek.com/v1', #deepseek官网base_url

        # ----使用AI团队部署在阿里云上的deepseek相关配置信息----
        'model': 'deepseek-v3.1',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1', #AI团队使用的阿里云base_url
        # ----使用AI团队部署在阿里云上的deepseek相关配置信息----
        
        'temperature': 0.7,
        'max_tokens': 128000,
    },
    'qwen': {
        'name': '通义千问',
        'model': 'qwen3-max-2025-09-23',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'temperature': 0.7,
        'max_tokens': 65000,  # 修正为不超过65536的值
    },
}
# AI Agent LLM提供商配置, 每个AI Agent可定制LLM提供商
AGENT_LLM_DEFAULTS = {
    "test_case_generator":  {"provider": "deepseek"},
    "test_case_reviewer":   {"provider": "deepseek"},
    "prd_analyzer":         {"provider": "deepseek"},
    "java_code_analyzer":   {"provider": "deepseek"},
    "iface_case_generator": {"provider": "deepseek"},
}

# 向量数据库配置（来自环境变量，默认指向本机 Milvus）
VECTOR_DB_CONFIG = {
    'host': os.getenv('MILVUS_HOST', '127.0.0.1'),
    'port': os.getenv('MILVUS_PORT', '19530'),
    'db_name': os.getenv('MILVUS_DB', 'default'),
    'collection_name': os.getenv('MILVUS_COLLECTION', 'vv_knowledge_collection'),
}

# java源码分析服务调用地址（独立部署的外部服务，默认指向本机）
# 该服务不在本仓库内，详见 README「可选依赖」章节
JAVA_ANALYZER_SERVICE_URL = os.getenv('JAVA_ANALYZER_SERVICE_URL', 'http://127.0.0.1:8089')

# Java 项目配置
JAVA_PROJECTS_BASE_DIR = "../"  # Java 项目基础目录
PROJECT_ID_REPO_MAPPING = {
    
    # 可以继续添加更多项目
}

# Git 凭据配置（用于内部GitLab）
GIT_CREDENTIALS = {
    'username': '',  # 替换为实际用户名
    'password': '',  # 替换为实际密码或访问令牌
    # 或者使用访问令牌（推荐）
    # 'token': 'your_gitlab_access_token',
}

# Hugging Face 的tokenizers库使用了多进程机制;
# 在自己的逻辑中使用时，需要注意在进程fork之前不要使用tokenizers库,否则可能会引起死锁
# 在Django启动时设置环境变量为false,禁止tokenizers库使用多进程
os.environ["TOKENIZERS_PARALLELISM"] = "false" 


# 向量模型提供商配置: "local"(本地BGE-M3) | "aliyun"(阿里云text-embedding-v4)
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "aliyun")

# 阿里云向量模型配置
ALIYUN_EMBEDDING_CONFIG = {
    'api_key': os.getenv('QWEN_API_KEY', ''),
    'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings',
    'model': 'text-embedding-v4',
    'batch_size': 10,  # 阿里云限制最大10条  # 阿里云限制每次最多25条
}


