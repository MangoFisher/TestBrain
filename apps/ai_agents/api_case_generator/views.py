from apps.ai_agents.api_case_generator.api_case_generator import parse_api_definitions,generate_test_cases_for_apis

from django.conf import settings
from django.http import JsonResponse, FileResponse
from apps.utils.progress_registry import get_progress as get_task_progress
from apps.utils.logger_manager import get_logger, set_task_context, clear_task_context
from django.shortcuts import render
# from apps.ai_agents.common.base_prompts import PromptTemplateManager

import json
import os
import time
from pathlib import Path
import yaml

# ... (rest of the code remains the same)



logger = get_logger(__name__)

# 获取LLM配置
llm_config = getattr(settings, 'LLM_PROVIDERS', {})

# 获取默认提供商
DEFAULT_PROVIDER = llm_config.get('default_provider', 'deepseek')

# 创建提供商字典，排除'default_provider'键
PROVIDERS = {k: v for k, v in llm_config.items() if k != 'default_provider'}


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
        # 直接读取当前 app 的 configs/prompt_config.yaml 中的 human_template
        config_path = Path(__file__).parent / 'configs' / 'prompt_config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}

        # 规则一般位于 human_template 中"## 测试用例生成规则"标题之后
        human_tpl = (cfg.get('human_template') or '').strip()
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