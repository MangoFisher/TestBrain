from django.db import models
from django.contrib.auth.models import User

class TestCase(models.Model):
    """测试用例模型"""
    STATUS_CHOICES = [
        ('pending_review', '待评审'),
        ('approved', '评审通过'),
        ('rejected', '评审未通过'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="测试用例标题")
    description = models.TextField(verbose_name="测试用例描述")
    requirements = models.TextField(verbose_name="需求描述", blank=True)
    code_snippet = models.TextField(verbose_name="代码片段", blank=True)
    test_steps = models.TextField(verbose_name="测试步骤")
    expected_results = models.TextField(verbose_name="预期结果")
    actual_results = models.TextField(verbose_name="实际结果", blank=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending_review',
        verbose_name="评审状态"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_testcases',
        verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "测试用例"
        verbose_name_plural = "测试用例"

class TestCaseReview(models.Model):
    """测试用例评审记录"""
    test_case = models.ForeignKey(
        TestCase, 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name="测试用例"
    )
    reviewer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name="评审人"
    )
    review_comments = models.TextField(verbose_name="评审意见")
    review_date = models.DateTimeField(auto_now_add=True, verbose_name="评审时间")
    
    def __str__(self):
        return f"Review for {self.test_case.title}"
    
    class Meta:
        verbose_name = "测试用例评审"
        verbose_name_plural = "测试用例评审"

class KnowledgeBase(models.Model):
    """知识库条目"""
    title = models.CharField(max_length=200, verbose_name="知识条目标题")
    content = models.TextField(verbose_name="知识内容")
    vector_id = models.CharField(max_length=100, blank=True, verbose_name="向量ID")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "知识库"
        verbose_name_plural = "知识库" 