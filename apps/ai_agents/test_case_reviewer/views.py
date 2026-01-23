from apps.core.models import TestCase
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.utils.logger_manager import get_logger
import json
from django.shortcuts import render
from apps.ai_agents.test_case_reviewer.reviewer import TestCaseReviewerAgent
from django.http import JsonResponse
import xlwt
from django.views.decorators.http import require_http_methods
from datetime import datetime
from django.http import HttpResponse
from django.conf import settings
from apps.llm import LLMServiceFactory
from apps.knowledge.service import get_knowledgeService_instance
from apps.llm.utils import get_agent_llm_configs




logger = get_logger(__name__)

DEFAULT_PROVIDER, PROVIDERS = get_agent_llm_configs("test_case_reviewer")
# 获取默认提供商的配置
DEFAULT_LLM_CONFIG = PROVIDERS.get(DEFAULT_PROVIDER, {})

# 创建LLM服务实例
llm_service = LLMServiceFactory.create(
    provider=DEFAULT_PROVIDER,
    **DEFAULT_LLM_CONFIG
)

knowledge_service = get_knowledgeService_instance()



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