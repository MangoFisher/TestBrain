import os
from django.http import JsonResponse
from apps.utils.logger_manager import get_logger
from apps.ai_agents.prd_analyzer.analyser import PrdAnalyserAgent
from django.conf import settings
from apps.llm import LLMServiceFactory
from django.shortcuts import render
from apps.utils.file_transfer import word_to_markdown
from apps.llm.utils import get_agent_llm_configs





# 获取LLM配置
llm_config = getattr(settings, 'LLM_PROVIDERS', {})

DEFAULT_PROVIDER, PROVIDERS = get_agent_llm_configs("prd_analyzer")

# 获取默认提供商的配置
DEFAULT_LLM_CONFIG = PROVIDERS.get(DEFAULT_PROVIDER, {})

# 创建LLM服务实例
llm_service = LLMServiceFactory.create(
    provider=DEFAULT_PROVIDER,
    **DEFAULT_LLM_CONFIG
)

logger = get_logger(__name__)


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