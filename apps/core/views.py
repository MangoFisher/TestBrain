from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

from .models import TestCase, TestCaseReview, KnowledgeBase, FileUploadTask
from .forms import TestCaseForm, TestCaseReviewForm, KnowledgeBaseForm
from ..agents.generator import TestCaseGeneratorAgent
from ..agents.reviewer import TestCaseReviewerAgent
from ..knowledge.service import KnowledgeService

# 初始化服务
from django.conf import settings
from apps.llm import LLMServiceFactory
from ..knowledge.vector_store import MilvusVectorStore
from ..knowledge.embedding import BGEM3Embedder
from utils.logger_manager import get_logger

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
from datetime import datetime
from .milvus_helper import get_embedding_model, init_milvus_collection, process_singel_file
from langchain.text_splitter import CharacterTextSplitter
import hashlib
import numpy as np
import gc
import xlwt
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .tasks import process_file_upload

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

embedder = None
# 暂时屏蔽，不要删除
# embedder = BGEM3Embedder(
#     model_name="BAAI/bge-m3"
# )

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
    
    logger.info(f"接收到的数据: {json.dumps(data, ensure_ascii=False)}")
    
    try:
        # 使用工厂创建选定的LLM服务
        logger.info(f"使用 {llm_provider} 生成测试用例")
        llm_service = LLMServiceFactory.create(llm_provider, **PROVIDERS.get(llm_provider, {}))
        
        
        generator_agent = TestCaseGeneratorAgent(llm_service=llm_service, knowledge_service=knowledge_service, case_design_methods=case_design_methods, case_categories=case_categories)
        logger.info(f"开始生成测试用例 - 需求: {requirements}...")
        logger.info(f"选择的测试用例设计方法: {case_design_methods}")
        logger.info(f"选择的测试用例类型: {case_categories}")
        
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
        if not 'single_file' in request.FILES:
            return JsonResponse({
                'success': False,
                'error': '未接收到文件'
            })
            
        uploaded_file = request.FILES['single_file']
        try:
            # 1. 先检查文件是否存在
            file_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.name)
            if os.path.exists(file_path):
                logger.info(f"文件已存在: {file_path}")
                return JsonResponse({
                    'success': False,
                    'error': '文件已存在'
                })
            
            # 2. 检查文件扩展名
            file_type = os.path.splitext(uploaded_file.name)[1].lower()
            logger.info(f"上传文件类型: {file_type}")
            logger.info(f"上传文件名: {uploaded_file.name}")
            
            if not file_type:
                logger.error("文件没有扩展名")
                return JsonResponse({
                    'success': False,
                    'error': '文件必须包含扩展名'
                })
            
            # 3. 检查是否支持该文件类型
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
            
            supported_extensions = [ext.lower() for exts in file_categories.values() for ext in exts]
            if file_type not in supported_extensions:
                logger.error(f"不支持的文件类型: {file_type}")
                return JsonResponse({
                    'success': False,
                    'error': '不支持的文件类型'
                })
            
            # 4. 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 5. 保存文件
            with open(file_path, 'wb+') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            logger.info(f"文件保存成功: {file_path}")
            
            # 6. 创建任务记录
            task = FileUploadTask.objects.create(
                file_name=uploaded_file.name,
                file_path=file_path,
                status='pending'
            )
            logger.info(f"创建上传任务: {task.id}")
            
            # 7. 启动异步任务
            process_file_upload.delay(task.id)
            logger.info(f"启动异步处理任务: {task.id}")
            
            return JsonResponse({
                'success': True,
                'task_id': task.id,
                'message': '文件上传成功，正在后台处理'
            })
            
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'文件上传失败: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': '不支持的请求方法'
    })

def get_upload_status(request, task_id):
    """获取上传任务状态"""
    try:
        task = FileUploadTask.objects.get(id=task_id)
        
        # 计算进度
        progress = (task.processed_chunks / task.total_chunks 
                   if task.total_chunks > 0 else 0)
        
        return JsonResponse({
            'status': task.status,
            'progress': progress,
            'error': task.error_message,
            'file_name': task.file_name
        })
        
    except FileUploadTask.DoesNotExist:
        logger.error(f"任务不存在: {task_id}")
        return JsonResponse({
            'error': '任务不存在'
        }, status=404)
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': f'获取任务状态失败: {str(e)}'
        }, status=500)

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
