from django.urls import path
from . import views

app_name = 'prd_analyzer'

urlpatterns = [
    # 页面路由
    path('', views.prd_analyzer, name='prd_analyzer'),
    path('prd_analyzer/', views.prd_analyzer, name='prd_analyzer'),

    
    # API 路由
    
]