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

]