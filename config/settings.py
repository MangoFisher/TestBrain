"""
Django settings for test_brain project.
"""

import os
import sys
from pathlib import Path

# 采用北京时间
TIME_ZONE = 'Asia/Shanghai'
USE_TZ = False

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 确保项目根目录在Python路径中
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '172.16.32.88',
    '172.16.56.57',
]

# 是否启用Milvus
ENABLE_MILVUS = False

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
    # 'apps.agents',
    'apps.ai_agents',
    'apps.knowledge',
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
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'test_brain_db',
        'USER': 'root',
        'PASSWORD': 'test123456',
        'HOST': 'localhost',
        'PORT': '3306',
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
STATIC_URL = 'static/'
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
        'model': 'deepseek-chat', #可以切换, deepseek-reasoner即【深度思考】模式, 可能会稍微慢一些
        # 'model': 'deepseek-reasoner',
        'api_base': 'https://api.deepseek.com/v1',
        'temperature': 1.0,
        'max_tokens': 8192,  #deepseek-chat的max_tokens为8192
        # 'max_tokens': 64000, #deepseek-reasoner的max_tokens为64000
    },
    'qwen': {
        'name': '通义千问',
        'model': 'qwen-max',
        'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'temperature': 1.0,
        'max_tokens': 8192,
    },
    'openai': {
        'name': 'OpenAI',
        'model': 'gpt-3.5-turbo',
        'temperature': 0.7,
        'max_tokens': 200000,
    }
}

# # 默认大模型提供商
# DEFAULT_LLM_PROVIDER = 'deepseek'

# 向量数据库配置
VECTOR_DB_CONFIG = {
    'host': 'localhost',
    'port': '19530',
    'collection_name': 'vv_knowledge_collection',
}

# 嵌入模型配置
EMBEDDING_CONFIG = {
    'model': 'bge-m3',
    'api_key': 'your_huggingface_api_key',
    'api_url': 'https://api-inference.huggingface.co/models/BAAI/bge-m3',
}

# java源码分析服务调用地址
JAVA_ANALYZER_SERVICE_URL = "http://localhost:8089"

# Hugging Face 的tokenizers库使用了多进程机制;
# 在自己的逻辑中使用时，需要注意在进程fork之前不要使用tokenizers库,否则可能会引起死锁
# 在Django启动时设置环境变量为false,禁止tokenizers库使用多进程
os.environ["TOKENIZERS_PARALLELISM"] = "false" 


