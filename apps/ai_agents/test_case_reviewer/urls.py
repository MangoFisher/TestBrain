from django.urls import path
from . import views

app_name = 'test_case_reviewer'

urlpatterns = [
    # 页面路由
    path('', views.review_view, name='review'),
    path('case-review-detail/', views.case_review_detail, name='case_review_detail'),


    
    # API 路由
    #获取单个测试用例详情
    path('case-review-detail/api/test-case/<int:test_case_id>/', views.get_test_case, name='get_test_case'),
    path('test_case_reviewer/api/copy-test-cases/', views.copy_test_cases, name='copy_test_cases'), #复制选中的用例集合
    path('test_case_reviewer/api/export-test-cases-excel/', views.export_test_cases_excel, name='export_test_cases_excel'), #将用例集合导出到excel
    path('api/delete-test-cases/', views.delete_test_cases, name='delete_test_cases'), #删除选中的测试用例
    path('case-review-detail/api/update-test-case/', views.update_test_case, name='update_test_case'),#更新单个测试用例的状态到mysql
    path('case-review-detail/api/review/', views.case_review, name='case_review'),#调用大模型对单个测试用例进行AI评审



    path('api/test-cases/<str:test_case_ids>/', views.get_test_cases, name='get_test_cases'),






   
]