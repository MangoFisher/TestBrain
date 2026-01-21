from django.urls import path
from . import views

app_name = 'api_case_generator'

urlpatterns = [
    # 页面路由
    path('', views.api_case_generate, name='api_case_generate'),

    
    # API 路由
    path('download_file/', views.download_file, name='download_file'),
    path('api/testcase-rule-template/', views.get_testcase_rule_template, name='get_testcase_rule_template'), # 获取规则模板
    path('api/get-generation-progress/', views.get_generation_progress_api, name='get_generation_progress'), #获取生成进度


    # path('api/upload/', views.api_upload, name='api_upload'),
    # path('api/generate/', views.api_generate, name='api_generate'),
    # path('api/download/', views.api_download, name='api_download'),
    # path('core/save-test-case/', views.save_test_case, name='save_test_case'),#批量保存大模型生成的测试用例

]