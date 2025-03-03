from django import forms
from .models import TestCase, KnowledgeBase

class TestCaseForm(forms.ModelForm):
    """测试用例表单"""
    class Meta:
        model = TestCase
        fields = ['title', 'description', 'requirements', 'code_snippet', 
                 'test_steps', 'expected_results']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'requirements': forms.Textarea(attrs={'rows': 5}),
            'code_snippet': forms.Textarea(attrs={'rows': 8, 'class': 'code-editor'}),
            'test_steps': forms.Textarea(attrs={'rows': 8}),
            'expected_results': forms.Textarea(attrs={'rows': 5}),
        }

class TestCaseReviewForm(forms.Form):
    """测试用例评审表单"""
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}),
        label="评审意见"
    )
    status = forms.ChoiceField(
        choices=[
            ('approved', '评审通过'),
            ('rejected', '评审未通过')
        ],
        label="评审结果"
    )

class KnowledgeBaseForm(forms.ModelForm):
    """知识库条目表单"""
    class Meta:
        model = KnowledgeBase
        fields = ['title', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        } 