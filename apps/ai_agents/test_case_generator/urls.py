from django.urls import path
from . import views

app_name = 'test_case_generator'

urlpatterns = [
    # 页面路由
    path('', views.generate, name='generate'),

    
    # API 路由


]