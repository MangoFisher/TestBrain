# TestBrain

一个基于LLM的智能测试用例生成平台(功能慢慢丰富中，未来可能将测试相关的所有活动集成到一起)，具有多模型支持、知识库管理和向量检索等功能。

# 最佳实践
想要使用AI大模型生成的测试用例更全面、更具体、更准确，应该将跟需求有关的相关文档如需求文档、设计文档、接口文档、过往具有参考价值的老用例、UI设计图等上传到知识库中，这样AI大模型通过学习生成的测试用例就会更符合实际需求。

## 功能特点

- 🤖 多模型支持
  - Deepseek
  - Qwen
  - 易于扩展的模型接入架构

- 📚 知识库管理
  - 文档导入与解析(目前测试用例excel文件、需求文档doc文件、pdf、和常见的纯文本文件类型都已支持，其它暂未详细测试)
  - 向量化存储
  - 智能检索匹配

- 🔍 向量检索
  - 基于 Milvus 的高性能向量数据库
  - 语义相似度搜索
  - 智能文本匹配

- 🎯 智能代理(TODO)
  - 自动问答
  - 内容审核
  - 知识推理

## 系统要求

- Python 3.12
- Django 4.x
- Milvus 2.x
- mysql

## 项目结构

```bash

project/
├── apps/
│ ├── agents/ # AI 代理模块
│ ├── core/ # 核心应用
│ ├── knowledge/ # 知识库模块
│ └── llm/ # 语言模型集成
├── config/ # 项目配置
├── static/ # 静态资源
├── templates/ # HTML 模板
├── utils/ # 工具类
└── logs/ # 日志文件
├── manage.py # 项目管理脚本
├── requirements.txt # 项目依赖
├── README.md # 项目说明
├── main.py # 项目入口
└── .env # 环境变量
```

## 快速开始

1.克隆项目
```bash
git clone https://github.com/yourusername/testbrain.git
cd testbrain
```

2.安装依赖
```bash
pip install -r requirements.txt
```


3.在.env文件中添加大模型api_key
```plaintext
    DEEPSEEK_API_KEY=""
```



4.启动项目
```bash
python manage.py runserver
```


5.访问项目
```bash
http://127.0.0.1:8000/
```


6.AI测试用例生成(TODO:目前prompt效果还可以但仍有优化空间, 未来可能会支持prompt配置文件化, 这样方便个人定制)
--/videos/测试用例生成.mp4
 

7.AI测试用例评审(TODO:优化prompt)
--/videos/测试用例评审.mp4

8.知识库文件上传
--/videos/知识库文档上传.mp4

<img src="videos/赞赏码.jpg" alt="请我喝杯咖啡" title="请我喝杯咖啡" width="400" height="400">
