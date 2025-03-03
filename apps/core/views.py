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
    api_key=settings.EMBEDDING_CONFIG['api_key'],
    api_url=settings.EMBEDDING_CONFIG['api_url']
)

knowledge_service = KnowledgeService(vector_store, embedder)
test_case_generator = TestCaseGeneratorAgent(llm_service, knowledge_service)
test_case_reviewer = TestCaseReviewerAgent(llm_service, knowledge_service)

# @login_required 先屏蔽登录
def index(request):
    """首页视图"""
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
    logger.info("===== 进入generate视图函数 =====")
    logger.info(f"请求方法: {request.method}")
    context = {
        'llm_providers': PROVIDERS,
        'llm_provider': DEFAULT_PROVIDER,
        'requirement': '',
        # 'api_description': '',
        'test_cases': ''
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
                
                # 生成测试用例
                test_cases = generator_agent.generate(requirement, input_type="requirement")
                
                # 格式化测试用例为HTML
                test_cases_html = format_test_cases_to_html(test_cases)
                
                # 更新上下文
                context.update({
                    'requirement': requirement,
                    'test_cases': test_cases_html,
                    'test_cases_json': json.dumps(test_cases),
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
        test_cases = data.get('test_cases', [])
        requirements = data.get('requirements', '')
        code_snippet = data.get('code_snippet', '')
        
        saved_test_cases = []
        
        for tc in test_cases:
            test_case = TestCase(
                title=tc.get('title', ''),
                description=tc.get('description', ''),
                requirements=requirements,
                code_snippet=code_snippet,
                test_steps=tc.get('test_steps', ''),
                expected_results=tc.get('expected_results', ''),
                status='pending_review',
                created_by=request.user
            )
            test_case.save()
            saved_test_cases.append({
                'id': test_case.id,
                'title': test_case.title
            })
        
        return JsonResponse({
            'success': True,
            'message': f'成功保存 {len(saved_test_cases)} 个测试用例',
            'test_cases': saved_test_cases
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

# @login_required 先屏蔽登录
def review_view(request):
    """测试用例评审页面"""
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
    """测试用例评审API"""
    try:
        data = json.loads(request.body)
        test_case_id = data.get('test_case_id')
        
        test_case = get_object_or_404(TestCase, id=test_case_id)
        
        # 调用测试用例评审Agent
        review_result = test_case_reviewer.review(test_case)
        
        return JsonResponse({
            'success': True,
            'review_result': review_result
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

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