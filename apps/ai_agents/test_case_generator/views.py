import os
import json
from django.http import JsonResponse
from apps.llm import LLMServiceFactory
from apps.ai_agents.test_case_generator.generator import TestCaseGeneratorAgent
from apps.core.models import TestCase
from apps.utils.logger_manager import get_logger
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from apps.knowledge.service import KnowledgeService
from apps.knowledge.vector_store import MilvusVectorStore
from apps.knowledge.embedding import BGEM3Embedder



logger = get_logger(__name__)
# 获取LLM配置
llm_config = getattr(settings, 'LLM_PROVIDERS', {})

# 获取默认提供商
DEFAULT_PROVIDER = llm_config.get('default_provider', 'deepseek')

# 创建提供商字典，排除'default_provider'键
PROVIDERS = {k: v for k, v in llm_config.items() if k != 'default_provider'}

vector_store = MilvusVectorStore(
    host=settings.VECTOR_DB_CONFIG['host'],
    port=settings.VECTOR_DB_CONFIG['port'],
    collection_name=settings.VECTOR_DB_CONFIG['collection_name']
)

embedder = BGEM3Embedder(
    model_name="BAAI/bge-m3"
)

knowledge_service = KnowledgeService(vector_store, embedder)



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