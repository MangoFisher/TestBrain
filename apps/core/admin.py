from django.contrib import admin
from .models import TestCase, TestCaseReview, KnowledgeBase

@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TestCaseReview)
class TestCaseReviewAdmin(admin.ModelAdmin):
    list_display = ('test_case', 'reviewer', 'review_date')
    list_filter = ('review_date',)
    search_fields = ('test_case__title', 'review_comments')
    readonly_fields = ('review_date',)

@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at') 