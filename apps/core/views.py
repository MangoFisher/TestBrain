from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods
import json

from .models import TestCase, TestCaseReview, KnowledgeBase
from .forms import TestCaseForm, TestCaseReviewForm, KnowledgeBaseForm
from apps.ai_agents.agents.test_case_generator.generator import TestCaseGeneratorAgent
from apps.ai_agents.agents.test_case_reviewer.reviewer import TestCaseReviewerAgent
from apps.ai_agents.agents.prd_analyzer.analyser import PrdAnalyserAgent
from apps.ai_agents.agents.api_case_generator.api_case_generator import APITestCaseGeneratorAgent, parse_api_definitions,generate_test_cases_for_apis
from apps.ai_agents.agents.java_code_analyzer.java_code_analyzer_agent import JavaCodeAnalyzerAgent
from apps.ai_agents.agents.java_code_analyzer.tools import GitTools
from apps.ai_agents.agents.api_case_generator.prompts import APITestCaseGeneratorPrompt
from apps.utils.progress_registry import get_progress as get_task_progress
from ..knowledge.service import KnowledgeService

# 初始化服务
from django.conf import settings
from apps.llm import LLMServiceFactory
from ..knowledge.vector_store import MilvusVectorStore
from ..knowledge.embedding import BGEM3Embedder
from apps.utils.logger_manager import get_logger, set_task_context, clear_task_context

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
from datetime import datetime
from pathlib import Path
import time
from .milvus_helper import get_embedding_model, init_milvus_collection, process_singel_file

import hashlib
import numpy as np
import gc
import xlwt
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.utils.file_transfer import word_to_markdown

logger = get_logger(__name__)

# 获取LLM配置
llm_config = getattr(settings, 'LLM_PROVIDERS', {})

# 获取默认提供商
DEFAULT_PROVIDER = llm_config.get('default_provider', 'deepseek')

# 创建提供商字典，排除'default_provider'键
PROVIDERS = {k: v for k, v in llm_config.items() if k != 'default_provider'}

# 获取默认提供商的配置
DEFAULT_LLM_CONFIG = PROVIDERS.get(DEFAULT_PROVIDER, {})

# 创建LLM服务实例
llm_service = LLMServiceFactory.create(
    provider=DEFAULT_PROVIDER,
    **DEFAULT_LLM_CONFIG
)

vector_store = MilvusVectorStore(
    host=settings.VECTOR_DB_CONFIG['host'],
    port=settings.VECTOR_DB_CONFIG['port'],
    collection_name=settings.VECTOR_DB_CONFIG['collection_name']
)

embedder = BGEM3Embedder(
    model_name="BAAI/bge-m3"
)

knowledge_service = KnowledgeService(vector_store, embedder)
# test_case_generator = TestCaseGeneratorAgent(llm_service, knowledge_service)
#test_case_reviewer = TestCaseReviewerAgent(llm_service, knowledge_service)

# @login_required 先屏蔽登录
def index(request):
    """页面-首页视图"""
    # 获取测试用例统计数据
    total_test_cases = TestCase.objects.count()
    pending_count = TestCase.objects.filter(status='pending').count()
    approved_count = TestCase.objects.filter(status='approved').count()
    rejected_count = TestCase.objects.filter(status='rejected').count()
    
    # 获取最近的测试用例
    recent_test_cases = TestCase.objects.order_by('-created_at')[:10]
    
    context = {
        'total_test_cases': total_test_cases,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'recent_test_cases': recent_test_cases,
    }
    
    return render(request, 'index.html', context)

# @login_required 先屏蔽登录
def generate(request):
    """
    页面-测试用例生成页面视图函数
    """
    logger.info("===== 进入generate视图函数 =====")
    logger.info(f"请求方法: {request.method}")
    context = {
        'llm_providers': PROVIDERS,
        'llm_provider': DEFAULT_PROVIDER,
        'requirement': '',
        # 'api_description': '',
        'test_cases': None  # 初始化为 None
    }
    
    if request.method == 'GET':
        return render(request, 'generate.html', context)
    
    # POST 请求参数解析
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("JSON解析错误", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    
    # 参数获取和验证
    requirements = data.get('requirements', '')
    if not requirements:
        return JsonResponse({
            'success': False,
            'message': '需求描述不能为空'
        })
        
    llm_provider = data.get('llm_provider', DEFAULT_PROVIDER)
    case_design_methods = data.get('case_design_methods', [])  # 获取测试方法
    case_categories = data.get('case_categories', [])         # 获取测试类型
    case_count = int(data.get('case_count', 10))            # 获取生成用例条数
    
    logger.info(f"接收到的数据: {json.dumps(data, ensure_ascii=False)}")
    
    try:
        # 使用工厂创建选定的LLM服务
        logger.info(f"使用 {llm_provider} 生成测试用例")
        llm_service = LLMServiceFactory.create(llm_provider, **PROVIDERS.get(llm_provider, {}))
        
        
        generator_agent = TestCaseGeneratorAgent(llm_service=llm_service, knowledge_service=knowledge_service, case_design_methods=case_design_methods, case_categories=case_categories, case_count=case_count)
        logger.info(f"开始生成测试用例 - 需求: {requirements}...")
        logger.info(f"选择的测试用例设计方法: {case_design_methods}")
        logger.info(f"选择的测试用例类型: {case_categories}")
        logger.info(f"需要生成的用例条数: {case_count}")
        
        # 生成测试用例
        #mock数据
        # test_cases = [{'description': '测试系统对用户输入为纯文本时的处理', 'test_steps': ['1. 打开应用程序', "2. 在输入框中输入纯文本，例如：'肥肥的'", '3. 提交输入'], 'expected_results': ['1. 应用程序成功启动', "2. 输入框正确显示输入的文本：'肥肥的'", '3. 系统正确识别并处理为纯文本输入，不进行代码段处理']}, {'description': '测试系统对用户输入为代码段时的处理', 'test_steps': ['1. 打开应用程序', '2. 在输入框中输入代码段，例如：\'print("Hello, World!")\'', '3. 提交输入'], 'expected_results': ['1. 应用程序成功启动', '2. 输入框正确显示输入的代码段：\'print("Hello, World!")\'', '3. 系统正确识别并处理为代码段输入，进行相应的代码处理']}, {'description': '测试系统对用户输入为空时的处理', 'test_steps': ['1. 打开应用程序', '2. 在输入框中不输入任何内容', '3. 提交输入'], 'expected_results': ['1. 应用程序成功启动', '2. 输入框保持为空', '3. 系统提示输入不能为空，要求重新输入']}, {'description': '测试系统对用户输入为混合内容（文本和代码）时的处理', 'test_steps': ['1. 打开应用程序', '2. 在输入框中输入混合内容，例如：\'肥肥的 print("Hello, World!")\'', '3. 提交输入'], 'expected_results': ['1. 应用程序成功启动', '2. 输入框正确显示输入的混合内容：\'肥肥的 print("Hello, World!")\'', '3. 系统正确识别并处理为混合内容，分别对文本和代码段进行相应处理']}, {'description': '测试系统对用户输入为特殊字符时的处理', 'test_steps': ['1. 打开应用程序', "2. 在输入框中输入特殊字符，例如：'@#$%^&*()'", '3. 提交输入'], 'expected_results': ['1. 应用程序成功启动', "2. 输入框正确显示输入的特殊字符：'@#$%^&*()'", '3. 系统正确识别并处理为特殊字符输入，不进行代码段处理']}]
        test_cases = generator_agent.generate(requirements, input_type="requirement")
        logger.info(f"测试用例生成成功 - 生成数量: {len(test_cases)}")
        
        context.update({
            'test_cases': test_cases
        })
        
        return JsonResponse({
            'success': True,
            'test_cases': test_cases
        })
            
    except Exception as e:
        logger.error(f"生成测试用例时出错: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

def format_test_cases_to_html(test_cases):
    """将测试用例格式化为HTML"""
    html = ""
    for i, test_case in enumerate(test_cases):
        html += f"<div class='test-case mb-4'>"
        html += f"<h4>测试用例 #{i+1}: {test_case.get('description', '无描述')}</h4>"
        
        # 测试步骤
        html += "<div class='test-steps mb-3'>"
        html += "<h5>测试步骤:</h5>"
        html += "<ol>"
        for step in test_case.get('test_steps', []):
            html += f"<li>{step}</li>"
        html += "</ol>"
        html += "</div>"
        
        # 预期结果
        html += "<div class='expected-results'>"
        html += "<h5>预期结果:</h5>"
        html += "<ol>"
        for result in test_case.get('expected_results', []):
            html += f"<li>{result}</li>"
        html += "</ol>"
        html += "</div>"
        
        html += "</div>"
    
    return html



# @login_required 先屏蔽登录
@require_http_methods(["POST"])
def save_test_case(request):
    """保存测试用例"""
    try:
        data = json.loads(request.body)
        requirement = data.get('requirement')
        test_cases_list = data.get('test_cases', [])
        llm_provider = data.get('llm_provider')
        
        # logger.info(f"接收到的保存请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        if not test_cases_list:
            return JsonResponse({
                'success': False,
                'message': '测试用例数据为空'
            }, status=400)
        
        # 准备批量创建的测试用例列表
        test_cases_to_create = []
        
        # 遍历测试用例数据，创建TestCase实例
        for index, test_case in enumerate(test_cases_list, 1):
            test_case_instance = TestCase(
                title=f"测试用例-{index}",  # 可以根据需求调整标题格式
                description=test_case.get('description', ''),
                test_steps='\n'.join(test_case.get('test_steps', [])),
                expected_results='\n'.join(test_case.get('expected_results', [])),
                requirements=requirement,
                llm_provider=llm_provider,
                status='pending'  # 默认状态为待评审
                # created_by=request.user  # 如果需要记录创建用户，取消注释此行
            )
            test_cases_to_create.append(test_case_instance)
        
        # 批量创建测试用例
        created_test_cases = TestCase.objects.bulk_create(test_cases_to_create)
        
        logger.info(f"成功保存 {len(created_test_cases)} 条测试用例")
        
        return JsonResponse({
            'success': True,
            'message': f'成功保存 {len(created_test_cases)} 条测试用例',
            'test_case_id': [case.id for case in created_test_cases]
        })
        
    except json.JSONDecodeError:
        logger.error("JSON解析错误", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"保存测试用例时出错: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'保存失败：{str(e)}'
        }, status=500)

# @login_required 先屏蔽登录
def review_view(request):
    """页面-测试用例评审页面视图"""
    # 获取所有测试用例
    pending_cases = TestCase.objects.filter(status='pending').order_by('-created_at')
    approved_cases = TestCase.objects.filter(status='approved').order_by('-created_at')
    rejected_cases = TestCase.objects.filter(status='rejected').order_by('-created_at')
    
    # 每页显示15条数据
    page_size = 15
    
    # 处理待评审用例分页
    pending_paginator = Paginator(pending_cases, page_size)
    pending_page = request.GET.get('pending_page', 1)
    try:
        pending_test_cases = pending_paginator.page(pending_page)
    except PageNotAnInteger:
        pending_test_cases = pending_paginator.page(1)
    except EmptyPage:
        pending_test_cases = pending_paginator.page(pending_paginator.num_pages)
    
    # 处理已通过用例分页
    approved_paginator = Paginator(approved_cases, page_size)
    approved_page = request.GET.get('approved_page', 1)
    try:
        approved_test_cases = approved_paginator.page(approved_page)
    except PageNotAnInteger:
        approved_test_cases = approved_paginator.page(1)
    except EmptyPage:
        approved_test_cases = approved_paginator.page(approved_paginator.num_pages)
    
    # 处理未通过用例分页
    rejected_paginator = Paginator(rejected_cases, page_size)
    rejected_page = request.GET.get('rejected_page', 1)
    try:
        rejected_test_cases = rejected_paginator.page(rejected_page)
    except PageNotAnInteger:
        rejected_test_cases = rejected_paginator.page(1)
    except EmptyPage:
        rejected_test_cases = rejected_paginator.page(rejected_paginator.num_pages)
    
    context = {
        'pending_test_cases': pending_test_cases,
        'approved_test_cases': approved_test_cases,
        'rejected_test_cases': rejected_test_cases,
    }
    
    return render(request, 'review.html', context)

# @login_required 先屏蔽登录
@require_http_methods(["POST"])
def case_review(request):
    """测试用例评审API接口"""
    try:
        data = json.loads(request.body)
        test_case_id = data.get('test_case_id')
        
        logger.info(f"接收到评审请求,测试用例ID: {test_case_id}")
        
        # 检查test_case_id是否为空
        if not test_case_id:
            logger.error("测试用例ID为空")
            return JsonResponse({
                'success': False,
                'message': '测试用例ID不能为空'
            }, status=400)
            
        # 检查测试用例是否存在
        try:
            test_case = TestCase.objects.get(id=test_case_id)
            logger.info(f"找到测试用例: ID={test_case.id}")
        except TestCase.DoesNotExist:
            logger.error(f"找不到ID为 {test_case_id} 的测试用例")
            return JsonResponse({
                'success': False,
                'message': f'找不到ID为 {test_case_id} 的测试用例'
            }, status=404)
        
        # 调用测试用例评审Agent
        logger.info("开始调用评审Agent...")
        test_case_reviewer = TestCaseReviewerAgent(llm_service, knowledge_service)
        review_result = test_case_reviewer.review(test_case)
        logger.info(f"评审完成，结果: {review_result}")
        
        # 从AIMessage对象中提取内容
        review_content = review_result.content if hasattr(review_result, 'content') else str(review_result)
        
        return JsonResponse({
            'success': True,
            'review_result': review_content  # 只返回评审内容文本
        })
        
    except json.JSONDecodeError:
        logger.error("JSON解析错误", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"评审过程中出错: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'评审失败：{str(e)}'
        }, status=500)


# @login_required 先屏蔽登录
def knowledge_view(request):
    """知识库管理页面"""
    return render(request, 'knowledge.html')

# @login_required 先屏蔽登录
@require_http_methods(["POST"])
def add_knowledge(request):
    """添加知识条目"""
    try:
        data = json.loads(request.body)
        title = data.get('title')
        content = data.get('content')
        
        if not title or not content:
            return JsonResponse({
                'success': False,
                'message': '标题和内容不能为空'
            })
        
        # 添加到知识库
        knowledge_id = knowledge_service.add_knowledge(title, content)
        
        return JsonResponse({
            'success': True,
            'message': '知识条目添加成功',
            'knowledge_id': knowledge_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

# @login_required 先屏蔽登录
def knowledge_list(request):
    """获取知识库列表"""
    try:
        knowledge_items = KnowledgeBase.objects.all().order_by('-created_at')
        
        items = []
        for item in knowledge_items:
            items.append({
                'id': item.id,
                'title': item.title,
                'content': item.content,
                'created_at': item.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'knowledge_items': items
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

# @login_required 先屏蔽登录
@require_http_methods(["POST"])
def search_knowledge(request):
    """搜索知识库"""
    try:
        data = json.loads(request.body)
        query = data.get('query')
        
        if not query:
            return JsonResponse({
                'success': False,
                'message': '搜索关键词不能为空'
            })
        
        # 搜索知识库
        query_embedding = embedder.get_embeddings(query)[0]
        logger.info(f"查询文本: '{query}', 向量维度: {len(query_embedding)}, 前5个维度: {query_embedding[:5]}")
        results = knowledge_service.search_knowledge(query)
        
        return JsonResponse({
            'success': True,
            'results': results
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@csrf_exempt
def upload_single_file(request):
    """处理文件上传的视图函数"""
    if request.method == 'GET':
        return render(request, 'upload.html')
    elif request.method == 'POST':
        if 'single_file' in request.FILES:  # 修改这里匹配前端的 name 属性
            uploaded_file = request.FILES['single_file']  # 修改这里匹配前端的 name 属性
            file_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.name)
            
            # 先检查文件是否存在
            if os.path.exists(file_path):
                return JsonResponse({
                    'success': False,
                    'error': '文件已存在'
                })
                
            try:
                # 1. 接收文件
                logger.info(f"Uploaded file: {uploaded_file}")
                if not uploaded_file:
                    return JsonResponse({'success': False, 'error': '未接收到文件'})
                
                file_categories = {
                    "CSV": [".csv"],
                    "E-mail": [".eml", ".msg", ".p7s"],
                    "EPUB": [".epub"],
                    "Excel": [".xls", ".xlsx"],
                    "HTML": [".html"],
                    "Image": [".bmp", ".heic", ".jpeg", ".png", ".tiff"],
                    "Markdown": [".md"],
                    "Org Mode": [".org"],
                    "Open Office": [".odt"],
                    "PDF": [".pdf"],
                    "Plain text": [".txt"],
                    "PowerPoint": [".ppt", ".pptx"],
                    "reStructured Text": [".rst"],
                    "Rich Text": [".rtf"],
                    "TSV": [".tsv"],
                    "Word": [".doc", ".docx"],
                    "XML": [".xml"]
                }
                file_type = os.path.splitext(uploaded_file.name)[1]
                logger.info(f"上传文件类型: {file_type}")
                logger.info(f"上传文件名: {uploaded_file.name}")
                
                if not file_type:
                    logger.error("文件没有扩展名")
                    return JsonResponse({'success': False, 'error': '文件必须包含扩展名'})
                
                # 获取所有支持的文件扩展名
                supported_extensions = [ext.lower() for exts in file_categories.values() for ext in exts]

                if file_type not in supported_extensions:
                    return JsonResponse({'success': False, 'error': '不支持的文件类型'})
                
                # 2. 保存临时文件
                save_dir = 'uploads/'
                os.makedirs(save_dir, exist_ok=True)
                file_path = os.path.join(save_dir, f"{uploaded_file.name}")
                with open(file_path, 'wb+') as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                logger.info(f"临时文件保存成功, 文件保存路径: {file_path}")

                # 3. 处理文件
                chunks = process_singel_file(file_path)  # 获取原始数据和文本
                if not chunks:
                    return JsonResponse({'success': False, 'error': '文件中无有效内容'})

                # 提取所有chunk.text并记录日志
                if isinstance(chunks, list):
                    # 直接从chunks中提取text属性
                    text_contents = []
                    for i, chunk in enumerate(chunks):
                        if hasattr(chunk, 'text'):
                            text_contents.append(str(chunk.text))
                        else:
                            text_contents.append(str(chunk))
                
                    logger.info(f"共提取了 {len(text_contents)} 个文本内容")
                else:
                    # 单一文本块的情况
                    if hasattr(chunks, 'text'):
                        text_contents = [str(chunks.text)]
                    else:
                        text_contents = [str(chunks)]
                    logger.info(f"提取了单个文本内容: {text_contents[0][:100]}...")

                # 直接生成所有文本内容的向量
                logger.info("开始生成向量")
                start_time = datetime.now()

                try:
                    # 直接为所有文本内容生成向量
                    all_embeddings = embedder.get_embeddings(texts=text_contents, show_progress_bar=False)
                    logger.info(f"成功生成 {len(all_embeddings)} 个向量")
                    
                    # 确保embeddings是列表格式
                    embeddings_list = []
                    for emb in all_embeddings:
                        if hasattr(emb, 'tolist'):
                            emb = emb.tolist()
                        embeddings_list.append(emb)
                    
                    # 准备插入数据
                    data_to_insert = []
                    for i in range(len(text_contents)):
                        item = {
                            "embedding": embeddings_list[i],  # 单个embedding向量
                            "content": text_contents[i],      # 文本内容
                            "metadata": '{}',                 # 元数据
                            "source": file_path,              # 来源
                            "doc_type": file_type,            # 文档类型
                            "chunk_id": f"{hashlib.md5(os.path.basename(file_path).encode()).hexdigest()[:10]}_{i:04d}",  # 块ID
                            "upload_time": datetime.now().isoformat()  # 上传时间
                        }
                        data_to_insert.append(item)
                    
                    # 插入数据到Milvus
                    logger.info(f"开始往milvus中插入 {len(data_to_insert)} 条数据")
                    vector_store.add_data(data_to_insert)
                    logger.info("数据插入完成")
                    
                    total_time = (datetime.now() - start_time).total_seconds()
                    logger.info(f"向量生成和插入完成，总耗时: {total_time:.2f} 秒")
                    
                    return JsonResponse({
                        'success': True, 
                        'count': len(text_contents),
                        'message': f'成功导入文件到知识库'
                    })
                    
                except Exception as e:
                    logger.error(f"生成或插入向量时出错: {str(e)}", exc_info=True)
                    return JsonResponse({
                        'success': False, 
                        'error': str(e)
                    })
                
            except Exception as e:
                logger.error(f"处理上传文件时出错: {str(e)}", exc_info=True)
                return JsonResponse({
                    'success': False, 
                    'error': str(e)
                })
            finally:
                # 清理临时文件
                if os.path.exists(file_path):
                    pass
                    # os.remove(file_path)
        else:
            return JsonResponse({
                'success': False,
                'error': '未接收到文件'
            })
    
    return JsonResponse({
        'success': False,
        'error': '不支持的请求方法'
    })


def case_review_detail(request):
    return render(request, 'case_review_detail.html')

@require_http_methods(["GET"])
def get_test_case(request, test_case_id):
    """从mysql查询、获取单个测试用例"""
    try:
        test_case = TestCase.objects.get(id=test_case_id)
        return JsonResponse({
            'id': test_case.id,
            'description': test_case.description,
            'test_steps': test_case.test_steps,
            'expected_results': test_case.expected_results,
            'status': test_case.status
        })
    except TestCase.DoesNotExist:
        return JsonResponse({'error': '测试用例不存在'}, status=404)
    
    
def get_test_cases(request, test_case_ids: str):
    """从mysql查询、获取多个测试用例"""
    try:
        # 将逗号分隔的字符串转换为列表
        ids = test_case_ids.split(',')
        test_cases = TestCase.objects.filter(id__in=ids).values(
                    'id', 'title', 'description', 'test_steps', 
                    'expected_results', 'status', 'requirements', 'llm_provider'
                )
        logger.info(f"获取到的测试用例集合数据类型是: {type(test_cases)}")
        return JsonResponse({
            'success': True,
            'test_cases': list(test_cases)
        })
    except TestCase.DoesNotExist:
        return JsonResponse({'error': '测试用例集合不存在'}, status=404)
    

@require_http_methods(["POST"])
def update_test_case(request):
    data = json.loads(request.body)
    logger.info(f"更新测试用例数据: {data}")
    try:
        test_case = TestCase.objects.get(id=data['test_case_id'])
        test_case.status = data['status']
        test_case.description = data['description']
        test_case.test_steps = data['test_steps']
        test_case.expected_results = data['expected_results']
        test_case.save()
        return JsonResponse({'success': True})
    except TestCase.DoesNotExist:
        return JsonResponse({'success': False, 'message': '测试用例不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}) 


def copy_test_cases(request):
    """返回用户手动勾选、复制后的测试用例集合"""
    try:
        # 将逗号分隔的字符串转换为列表
        ids = request.GET.get('ids')
        response = get_test_cases(request,ids)
        response_data = json.loads(response.content)
        if response_data.get('success'):
            test_cases = response_data.get('test_cases')
            logger.info(f"获取到的测试用例集合数据类型是2222: {type(test_cases)}")
            return JsonResponse({
                'success': True,
                'test_cases': test_cases
            })
        else:
            return JsonResponse({
                'success': False,
                'message': response_data.get('message')
            })
    except TestCase.DoesNotExist:
        return JsonResponse({'error': '测试用例集合不存在'}, status=404)
    
def export_test_cases_excel(request):
    """将用例集合导出到excel"""
    try:
        ids = request.GET.get('ids')
        if not ids:
            return JsonResponse({'success': False, 'message': '未提供测试用例ID'})
            
        # 获取测试用例数据
        response = get_test_cases(request, ids)
        response_data = json.loads(response.content)
        
        if not response_data.get('success'):
            return JsonResponse({'success': False, 'message': '获取测试用例数据失败'})
            
        test_cases = response_data.get('test_cases')
        logger.info(f"获取到的测试用例集合数据类型是: {type(test_cases)}")
        
        # 创建Excel工作簿和工作表
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('测试用例')
        
        # 设置表头样式
        header_style = xlwt.XFStyle()
        header_font = xlwt.Font()
        header_font.bold = True
        header_style.font = header_font
        
        # 写入表头
        headers = ['序号', '用例描述', '测试步骤', '预期结果', '状态']
        for col, header in enumerate(headers):
            ws.write(0, col, header, header_style)
            # 设置列宽
            ws.col(col).width = 256 * 30  # 30个字符宽度
        
        # 写入数据
        for row, test_case in enumerate(test_cases, start=1):
            ws.write(row, 0, row)  # 序号
            ws.write(row, 1, test_case.get('description', ''))
            ws.write(row, 2, test_case.get('test_steps', ''))
            ws.write(row, 3, test_case.get('expected_results', ''))
            ws.write(row, 4, test_case.get('status', ''))
            
            # 自动调整行高
            ws.row(row).height_mismatch = True
            ws.row(row).height = 20 * 40  # 40行文本高度
        
        # 生成文件名
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')  # 格式：20240319_153021
        case_count = len(test_cases)
        filename = f"test_cases_{current_time}_{case_count}_cases.xls"
        
        # 生成响应
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # 保存Excel文件到响应
        wb.save(response)
        return response
        
    except Exception as e:
        logger.error(f"导出Excel失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'导出Excel失败: {str(e)}'
        }) 

@require_http_methods(["DELETE"])
def delete_test_cases(request):
    """删除选中的测试用例"""
    try:
        ids = request.GET.get('ids', '')
        if not ids:
            return JsonResponse({'success': False, 'message': '未提供测试用例ID'})
            
        test_case_ids = ids.split(',')
        TestCase.objects.filter(id__in=test_case_ids).delete()
        
        return JsonResponse({
            'success': True,
            'message': f'成功删除 {len(test_case_ids)} 条测试用例'
        })
    except Exception as e:
        logger.error(f"删除测试用例失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }) 
    
def prd_analyzer(request):
    """从PRD文件中提取测试点&测试场景"""
    if request.method == 'GET':
        return render(request, 'prd_analyzer.html')
    elif request.method == 'POST':
        if 'single_file' in request.FILES:  # 修改这里匹配前端的 name 属性
            uploaded_file = request.FILES['single_file']  # 修改这里匹配前端的 name 属性
            file_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.name)
            # 先检查文件是否存在
            if os.path.exists(file_path):
                return JsonResponse({
                    'success': False,
                    'error': '文件已存在'
                })
            logger.info(f"Uploaded file: {uploaded_file}")
            if not uploaded_file:
                return JsonResponse({'success': False, 'error': '未接收到文件'})
            file_type = os.path.splitext(uploaded_file.name)[1]
            # 判断文件类型目前只支持docx，其他类型不支持
            if file_type != '.docx':
                return JsonResponse({'success': False, 'error': '不支持的文件类型'})
            logger.info(f"上传文件类型: {file_type}")
            logger.info(f"上传文件名: {uploaded_file.name}")
             # 2. 保存临时文件
            save_dir = 'prd/'
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, f"{uploaded_file.name}")
            with open(file_path, 'wb+') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            logger.info(f"临时文件保存成功, 文件保存路径: {file_path}")
            #3. 处理文件
            word_to_markdown(file_path, file_path.replace('.docx', '.md'))
            #读取出转化后md文件的内容
            with open(file_path.replace('.docx', '.md'), 'r', encoding='utf-8') as f:
                prd_content = f.read()
            logger.info(f"PRD内容: {prd_content}")
            #调用PRD分析器
            analyser = PrdAnalyserAgent(llm_service=llm_service)
            result = analyser.analyse(prd_content)
            return JsonResponse({
                'success': True,
                'result': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '未接收到文件'
            })
        return JsonResponse({
        'success': False,
        'error': '不支持的请求方法'
    })





def download_file(request):
    """文件下载视图"""
    file_path = request.GET.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return JsonResponse({'error': '文件不存在'}, status=404)
    
    # 安全检查：确保文件在uploads目录内
    uploads_dir = os.path.abspath('uploads')
    file_abs_path = os.path.abspath(file_path)
    
    if not file_abs_path.startswith(uploads_dir):
        return JsonResponse({'error': '访问被拒绝'}, status=404)
    
    # 返回文件
    filename = os.path.basename(file_path)
    resp = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
    resp['Content-Type'] = 'application/octet-stream'
    resp['X-Content-Type-Options'] = 'nosniff'
    return resp


def api_case_generate(request):
    """
    页面-接口case生成页面视图函数
    """
    logger.info("===== 进入api_case_generate视图函数 =====")
    logger.info(f"请求方法: {request.method}")
    
    if request.method == 'GET':
        context = {
            'llm_providers': PROVIDERS,
            'llm_provider': DEFAULT_PROVIDER,
        }
        return render(request, 'api_case_generate.html', context)
    elif request.method == 'POST':
        if 'single_file' in request.FILES:
            uploaded_file = request.FILES['single_file']
            logger.info(f"接收到文件: {uploaded_file.name}")
            
            # 检查文件类型
            if not uploaded_file.name.lower().endswith('.json'):
                return JsonResponse({
                    'success': False,
                    'error': '只支持JSON格式的文件'
                })
            
            try:
                # 确保uploads目录存在
                uploads_dir = os.path.join(settings.MEDIA_ROOT)
                os.makedirs(uploads_dir, exist_ok=True)
                
                # 生成唯一文件名（避免重名）
                file_name = uploaded_file.name
                base_name, ext = os.path.splitext(file_name)
                counter = 1
                while os.path.exists(os.path.join(uploads_dir, file_name)):
                    file_name = f"{base_name}_{counter}{ext}"
                    counter += 1
                
                # 保存文件到uploads目录
                file_path = os.path.join(uploads_dir, file_name)
                with open(file_path, 'wb+') as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                
                logger.info(f"文件保存成功: {file_path}")
                
                # 解析JSON文件，提取接口列表
                api_list = parse_api_definitions(file_path)
                
                return JsonResponse({
                    'success': True,
                    'api_list': api_list,
                    'file_path': file_path
                })
                
            except Exception as e:
                logger.error(f"文件保存失败: {str(e)}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'error': f'文件保存失败: {str(e)}'
                })
        
        elif 'generate_test_cases' in request.POST:
            # 生成测试用例
            file_path = request.POST.get('file_path')
            selected_apis = json.loads(request.POST.get('selected_apis'))
            count_per_api = int(request.POST.get('count_per_api', 1))
            priority = request.POST.get('priority', 'P0')
            llm_provider = request.POST.get('llm_provider', 'deepseek')
            # 任务ID（前端可传入；若没有则后端生成）
            task_id = request.POST.get('task_id') or f"task_{int(time.time()*1000)}_{request.user.id if request.user.is_authenticated else 'anon'}"
            
            # 后台线程异步生成，立即返回
            import threading
            def _bg_job():
                try:
                    set_task_context(task_id)
                    # 透传用户规则覆盖（若有）
                    rules_override = request.POST.get('rules_override') or None
                    generate_test_cases_for_apis(
                        file_path, selected_apis, count_per_api, priority, llm_provider, task_id,
                        rules_override=rules_override
                    )
                except Exception as e:
                    logger.error(f"后台生成失败: {e}")
                finally:
                    clear_task_context()
            t = threading.Thread(target=_bg_job, name=f"gen-{task_id}")
            t.daemon = True
            t.start()
            
            return JsonResponse({
                'success': True,
                'task_id': task_id
            })
        
        else:
            return JsonResponse({
                'success': False,
                'error': '未接收到文件'
            })
    
    return JsonResponse({
        'success': False,
        'error': '不支持的请求方法'
    })


def get_generation_progress_api(request):
    """进度查询：根据 task_id 返回内存注册表中的进度"""
    try:
        task_id = request.GET.get('task_id')
        if not task_id:
            return JsonResponse({'success': False, 'message': '缺少 task_id'})
        progress = get_task_progress(task_id)
        if not progress:
            return JsonResponse({'success': False, 'message': '未找到进度信息'})
        
        
        # 将 ProgressData 对象转换为字典以便 JSON 序列化
        progress_dict = progress.dict() if hasattr(progress, 'dict') else progress
        return JsonResponse({'success': True, 'progress': progress_dict})
    except Exception as e:
        logger.error(f"获取进度失败: {e}")
        return JsonResponse({'success': False, 'message': str(e)})


def get_testcase_rule_template(request):
    """返回模版中的"测试用例生成规则"文本（只读）"""
    try:
        # 直接读取 prompts_config.yaml 中 api_test_case_generator.human_template 的规则段
        # 为简单起见，这里复用 PromptTemplateManager 已加载的配置
        from ..agents.prompts import PromptTemplateManager
        mgr = PromptTemplateManager()
        cfg = mgr.config.get('api_test_case_generator') or {}
        # 规则一般位于 human_template 中"## 测试用例生成规则"标题之后
        human_tpl = cfg.get('human_template') or ''
        rule_text = ''
        if human_tpl:
            marker = '## 测试用例生成规则'
            idx = human_tpl.find(marker)
            if idx >= 0:
                rule_text = human_tpl[idx:]
            else:
                rule_text = human_tpl
        return JsonResponse({'success': True, 'rule_text': rule_text})
    except Exception as e:
        logger.error(f"读取规则模版失败: {e}")
        return JsonResponse({'success': False, 'message': str(e)})
    
    
def java_code_analyzer(request):
    """Java源码分析页面视图"""
    if request.method == 'GET':
        context = {
            'llm_providers': PROVIDERS,
            'llm_provider': DEFAULT_PROVIDER,
        }
        return render(request, 'java_code_analyzer.html', context)


@require_http_methods(["POST"])
def java_code_analyzer_service_api(request):
    """Java源码分析API接口"""
    try:
        data = json.loads(request.body)
        target_service = data.get('target_service')
        base_commit = data.get('base_commit')
        new_commit = data.get('new_commit')
        llm_provider = data.get('llm_provider', DEFAULT_PROVIDER)
        # model 参数将从 settings 配置中获取，无需显式传递
        
        logger.info(f"Java代码分析请求: 服务={target_service}, 基础提交={base_commit}, 新提交={new_commit}, LLM提供商={llm_provider}")
        
        # 验证参数
        if not target_service or not base_commit or not new_commit:
            return JsonResponse({
                'success': False,
                'error': '目标服务、基础提交和新提交均为必填项'
            }, status=400)
        
        # 使用工厂创建选定的LLM服务
        llm_service = LLMServiceFactory.create(
            provider=llm_provider,
            **PROVIDERS.get(llm_provider, {})
        )
        
        # 确定仓库路径（可以根据服务名称映射到实际路径）
        # 这里可以根据实际情况调整仓库路径的确定逻辑
        repo_path_mapping = {
            'vv-education-service': '/Users/zhangxiaoguo/Documents/vv-education-service',
            'java-callgraph2': '/Users/zhangxiaoguo/Documents/java-callgraph2',
        }
        
        repo_path = repo_path_mapping.get(target_service, target_service)
        
        # 创建Java代码分析Agent实例
        analyzer_agent = JavaCodeAnalyzerAgent(
            repo_path=repo_path,
            api_key=getattr(settings, f'{llm_provider.upper()}_API_KEY', None),
            base_url=getattr(settings, f'{llm_provider.upper()}_BASE_URL', None),
            java_analyzer_service_url=getattr(settings, 'JAVA_ANALYZER_SERVICE_URL', 'http://localhost:8089'),
            max_iterations=15,
            verbose=True
        )
        
        git_tools = GitTools(repo_path)
        output_dir = Path(settings.BASE_DIR) / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        repo_identifier = Path(repo_path).name or "repo"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{repo_identifier}_analyzer_{base_commit[:8]}_{new_commit[:8]}_{timestamp}.md"
        output_path = output_dir / output_filename

        original_ref = None
        report_content = ""

        try:
            logger.info("拉取最新代码...")
            git_tools.pull_latest()

            logger.info("记录当前 Git 状态...")
            original_ref = git_tools.get_current_ref()
            logger.info(f"当前引用: {original_ref}")

            logger.info(f"切换到目标版本: {new_commit}")
            git_tools.checkout_version(new_commit)
            logger.info(f"已切换到: {new_commit}")

            result = analyzer_agent.analyze(base_commit, new_commit)

            if result.get('success'):
                report_content = result.get('output', '')
                if report_content:
                    output_path.write_text(report_content, encoding='utf-8')
                    logger.info(f"分析报告已写入: {output_path}")
                return JsonResponse({
                    'success': True,
                    'result': report_content or '分析完成，但没有返回详细结果',
                    'report_path': str(output_path)
                })

            error_msg = result.get('error', '分析失败')
            logger.error(f"分析失败: {error_msg}")
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=500)

        finally:
            if original_ref:
                try:
                    git_tools.checkout_version(original_ref)
                    logger.info(f"已恢复到原始引用: {original_ref}")
                except Exception as restore_error:
                    logger.error(f"恢复原始引用失败: {restore_error}")

    except json.JSONDecodeError:
        logger.error("JSON解析错误", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"Java代码分析时出错: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'分析失败: {str(e)}'
        }, status=500)
