from apps.utils.logger_manager import get_logger
from django.conf import settings
from apps.llm import LLMServiceFactory
from apps.ai_agents.java_code_analyzer.java_code_analyzer_agent import JavaCodeAnalyzerAgent
import json
from django.http import JsonResponse
from apps.ai_agents.java_code_analyzer.tools import GitTools
from pathlib import Path
from datetime import datetime
from django.views.decorators.http import require_http_methods
from django.shortcuts import render









logger = get_logger(__name__)

# 获取LLM配置
llm_config = getattr(settings, 'LLM_PROVIDERS', {})

# 获取默认提供商
DEFAULT_PROVIDER = llm_config.get('default_provider', 'deepseek')

# 创建提供商字典，排除'default_provider'键
PROVIDERS = {k: v for k, v in llm_config.items() if k != 'default_provider'}



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
