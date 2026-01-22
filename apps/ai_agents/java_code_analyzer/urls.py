from django.urls import path
from . import views

app_name = 'java_code_analyzer'

urlpatterns = [
    # 页面路由
    path('', views.java_code_analyzer, name='java_code_analyzer'),
    path('java_code_analyzer/', views.java_code_analyzer, name='java_code_analyzer'),

    
    # API 路由
    #调用java源码分析服务java-analyzer
    path('api/java-code-analyzer-service/', views.java_code_analyzer_service_api, name='java_code_analyzer_service_api'),
    
    #下载java源码分析报告
    path('api/download-report/', views.download_report, name='download_report'),

]