from django.urls import path
from . import views

urlpatterns = [
    # 页面路由
    path('', views.index, name='index'),
    path('generate/', views.generate, name='generate'),
    path('review/', views.review_view, name='review'),
    path('knowledge/', views.knowledge_view, name='knowledge'),
    #知识库文件上传页面
    path('upload/', views.upload_test_cases, name='upload_test_cases'),

    
    # API路由
    path('api/generate/', views.generate_api, name='generate_api'),
    path('core/save-test-case/', views.save_test_case, name='save_test_case'),
    path('api/review/', views.review_api, name='review_api'),
    path('api/update-status/', views.update_test_case_status, name='update_status'),
    path('api/add-knowledge/', views.add_knowledge, name='add_knowledge'),
    path('api/knowledge-list/', views.knowledge_list, name='knowledge_list'),
    path('api/search-knowledge/', views.search_knowledge, name='search_knowledge'),
] 