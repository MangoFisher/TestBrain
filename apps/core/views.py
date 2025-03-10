from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

from .models import TestCase, TestCaseReview, KnowledgeBase
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
from .milvus_helper import get_embedding_model, init_milvus_collection, process_excel

logger = get_logger('core')

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
test_case_generator = TestCaseGeneratorAgent(llm_service, knowledge_service)
test_case_reviewer = TestCaseReviewerAgent(llm_service, knowledge_service)

# @login_required 先屏蔽登录
def index(request):
    """页面-首页视图"""
    # 获取测试用例统计数据
    total_test_cases = TestCase.objects.count()
    pending_review_count = TestCase.objects.filter(status='pending_review').count()
    approved_count = TestCase.objects.filter(status='approved').count()
    rejected_count = TestCase.objects.filter(status='rejected').count()
    
    # 获取最近的测试用例
    recent_test_cases = TestCase.objects.order_by('-created_at')[:10]
    
    context = {
        'total_test_cases': total_test_cases,
        'pending_review_count': pending_review_count,
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
    
    if request.method == 'POST':
        requirement = request.POST.get('requirement', '')
        llm_provider = request.POST.get('llm_provider', DEFAULT_PROVIDER)
        
        if requirement:
            try:
                # 使用工厂创建选定的LLM服务
                logger.info(f"使用 {llm_provider} 生成测试用例")
                llm_service = LLMServiceFactory.create(llm_provider, **PROVIDERS.get(llm_provider, {}))
                
                # 创建知识服务和测试用例生成Agent
                # knowledge_service = KnowledgeService()
                generator_agent = TestCaseGeneratorAgent(llm_service, knowledge_service)
                logger.info(f"开始生成测试用例 - 需求: {requirement}...")
                # 生成测试用例
                test_cases = generator_agent.generate(requirement, input_type="requirement")
                logger.info(f"测试用例生成成功 - 生成数量: {len(test_cases)}")
                logger.info(f"测试用例数据结构: {type(test_cases)}")
                logger.info(f"测试用例详细内容: {json.dumps(test_cases, ensure_ascii=False, indent=2)}")
                
                # 直接将测试用例数据传递给模板
                context.update({
                    'requirement': requirement,
                    'test_cases': test_cases,  # 直接传递测试用例数据
                    'llm_provider': llm_provider
                })
                
            except Exception as e:
                logger.error(f"生成测试用例时出错: {str(e)}", exc_info=True)
                context['error'] = f"生成测试用例时出错: {str(e)}"
    
    return render(request, 'generate.html', context)

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
def generate_api(request):
    """测试用例生成API"""
    try:
        data = json.loads(request.body)
        input_type = data.get('input_type')
        input_text = data.get('input')
        
        if not input_text:
            return JsonResponse({
                'success': False,
                'message': '输入内容不能为空'
            })
        
        # 调用测试用例生成Agent
        test_cases = test_case_generator.generate(input_text, input_type)
        
        return JsonResponse({
            'success': True,
            'test_cases': test_cases
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

# @login_required 先屏蔽登录
@require_http_methods(["POST"])
def save_test_case(request):
    """保存测试用例"""
    try:
        data = json.loads(request.body)
        requirement = data.get('requirement')
        test_cases_list = data.get('test_cases', [])
        llm_provider = data.get('llm_provider')
        
        logger.info(f"接收到的保存请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
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
                status='pending_review'  # 默认状态为待评审
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
    pending_test_cases = TestCase.objects.filter(status='pending_review')
    approved_test_cases = TestCase.objects.filter(status='approved')
    rejected_test_cases = TestCase.objects.filter(status='rejected')
    
    context = {
        'pending_test_cases': pending_test_cases,
        'approved_test_cases': approved_test_cases,
        'rejected_test_cases': rejected_test_cases,
    }
    
    return render(request, 'review.html', context)

# @login_required 先屏蔽登录
@require_http_methods(["POST"])
def review_api(request):
    """测试用例评审API接口"""
    try:
        data = json.loads(request.body)
        test_case_ids = data.get('test_case_ids')
        
        logger.info(f"接收到评审请求，测试用例ID: {test_case_ids}")
        
        # 检查test_case_id是否为空
        if not test_case_ids:
            logger.error("测试用例ID为空")
            return JsonResponse({
                'success': False,
                'message': '测试用例ID不能为空'
            }, status=400)
            
        # 检查测试用例是否存在
        try:
            test_case = TestCase.objects.get(id=test_case_ids[0])
            logger.info(f"找到测试用例: ID={test_case.id}")
        except TestCase.DoesNotExist:
            logger.error(f"找不到ID为 {test_case.id} 的测试用例")
            return JsonResponse({
                'success': False,
                'message': f'找不到ID为 {test_case.id} 的测试用例'
            }, status=404)
        
        # 调用测试用例评审Agent
        logger.info("开始调用评审Agent...")
        review_result = test_case_reviewer.review(test_case)
        logger.info(f"评审完成，结果: {review_result}")
        
        return JsonResponse({
            'success': True,
            'review_result': review_result
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
@require_http_methods(["POST"])
def update_test_case_status(request):
    """更新测试用例状态"""
    try:
        data = json.loads(request.body)
        test_case_id = data.get('test_case_id')
        status = data.get('status')
        comments = data.get('comments', '')
        
        test_case = get_object_or_404(TestCase, id=test_case_id)
        test_case.status = status
        test_case.save()
        
        # 创建评审记录
        review = TestCaseReview(
            test_case=test_case,
            reviewer=request.user,
            review_comments=comments
        )
        review.save()
        
        return JsonResponse({
            'success': True,
            'message': f'测试用例状态已更新为 {dict(TestCase.STATUS_CHOICES).get(status)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

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
def upload_test_cases(request):
    """处理测试用例上传的视图函数"""
    if request.method == 'GET':
        return render(request, 'upload.html')
    elif request.method == 'POST':
        try:
            # 1. 接收文件
            uploaded_file = request.FILES.get('excel_file')
            if not uploaded_file:
                return JsonResponse({'success': False, 'error': '未接收到文件'})
            
            if not uploaded_file.name.endswith(('.xlsx', '.xls')):
                return JsonResponse({'success': False, 'error': '仅支持Excel文件'})

            # 2. 保存临时文件
            save_dir = 'uploads/'
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx")
            with open(file_path, 'wb+') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            # 3. 处理Excel
            test_cases, texts = process_excel(file_path)  # 获取原始数据和文本
            if not test_cases:
                return JsonResponse({'success': False, 'error': 'Excel中无有效测试用例'})

            # 4. 生成向量
            model = get_embedding_model()
            embeddings = model.encode(texts, normalize_embeddings=True)
            logger.info(f"上传的向量维度: {embeddings.shape}, 前5个维度值: {embeddings[0][:5]}")

            # 5. 构建文档
            documents = []
            for i, row in enumerate(test_cases):
                doc = {
                    "embedding": embeddings[i].tolist(),
                    "case_name": str(row['用例名称']),
                    "case_id": str(row['ID']),
                    "module": str(row['所属模块']),
                    "precondition": str(row['前置条件']),
                    "steps": str(row['步骤描述']),
                    "expected": str(row['预期结果']),
                    "tags": str(row['标签']),
                    "priority": str(row['用例等级']),
                    "creator": str(row['创建人']),
                    "create_time": str(row['创建时间'])
                }
                documents.append(doc)

            # 6. 添加到向量数据库
            vector_store = MilvusVectorStore()
            vector_store.add_documents(documents)
            
            return JsonResponse({
                'success': True, 
                'count': len(documents),
                'message': f'成功导入 {len(documents)} 条测试用例'
            })
            
        except Exception as e:
            logger.error(f"处理上传文件时出错: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)})
        finally:
            # 清理临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
                
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})