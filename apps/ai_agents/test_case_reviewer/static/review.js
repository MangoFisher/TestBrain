// 测试用例评审页面专用脚本

// 获取CSRF Token的辅助函数
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 等待页面加载完成
document.addEventListener('DOMContentLoaded', function() {
    // 获取所有评审按钮
    const reviewButtons = document.querySelectorAll('.review-button');
    
    // 获取 CSRF Token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // 为每个评审按钮添加点击事件监听器
    reviewButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault(); // 阻止默认行为
            
            // 获取测试用例ID
            const testCaseId = this.getAttribute('data-id');
            
            // 验证测试用例ID是否存在
            if (!testCaseId) {
                alert('错误：未找到测试用例ID');
                return;
            }
            
            // 直接打开新窗口，进入详细评审页面
            window.open(`/test_case_reviewer/case-review-detail/?id=${testCaseId}`, 'TestCaseReview', 
                'width=800,height=600,scrollbars=yes,resizable=yes');
        });
    });
    
    // 获取所有状态更新按钮
    const statusButtons = document.querySelectorAll('.status-button');
    
    // 为每个状态更新按钮添加点击事件
    statusButtons.forEach(button => {
        button.addEventListener('click', function() {
            const testCaseId = this.getAttribute('data-id');
            const status = this.getAttribute('data-status');
            const commentsElement = document.getElementById(`review-comments-${testCaseId}`);
            const comments = commentsElement ? commentsElement.value.trim() : '';
            
            if (status === 'rejected' && !comments) {
                showNotification('拒绝测试用例时必须提供评审意见', 'error');
                return;
            }
            
            // 禁用按钮
            this.disabled = true;
            
            // 发送请求到后端
            fetch('/api/update-status/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    test_case_id: testCaseId,
                    status: status,
                    comments: comments
                })
            })
            .then(response => response.json())
            .then(data => {
                this.disabled = false;
                
                if (data.success) {
                    showNotification('测试用例状态已更新', 'success');
                    
                    // 更新UI
                    const testCaseItem = document.getElementById(`test-case-${testCaseId}`);
                    if (testCaseItem) {
                        // 移除旧的状态类
                        testCaseItem.classList.remove('pending', 'approved', 'rejected');
                        
                        // 添加新的状态类
                        testCaseItem.classList.add(status);
                        
                        // 更新状态标签
                        const statusBadge = testCaseItem.querySelector('.status-badge');
                        if (statusBadge) {
                            statusBadge.textContent = status === 'approved' ? '评审通过' : '评审未通过';
                            statusBadge.classList.remove('badge-warning', 'badge-success', 'badge-danger');
                            statusBadge.classList.add(
                                status === 'approved' ? 'badge-success' : 'badge-danger'
                            );
                        }
                        
                        // 如果在待评审标签页，则移动到相应标签页
                        if (document.querySelector('#pending-tab.active')) {
                            setTimeout(() => {
                                testCaseItem.remove();
                                
                                // 检查是否还有待评审的测试用例
                                const pendingItems = document.querySelectorAll('#pending .test-case-item');
                                if (pendingItems.length === 0) {
                                    document.querySelector('#pending').innerHTML = 
                                        '<div class="alert alert-info">没有待评审的测试用例</div>';
                                }
                                
                                // 更新计数
                                updateTabCounts();
                            }, 500);
                        }
                    }
                } else {
                    showNotification(data.message || '更新测试用例状态失败', 'error');
                }
            })
            .catch(error => {
                this.disabled = false;
                showNotification('请求失败: ' + error.message, 'error');
            });
        });
    });
    
    // 显示通知
    function showNotification(message, type = 'info') {
        // 如果页面上有通知容器，使用它
        let container = document.getElementById('notification-container');
        
        // 如果没有，创建一个
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        `;
        
        // 添加到容器
        container.appendChild(notification);
        
        // 设置自动关闭
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
    
    // 更新标签页计数
    function updateTabCounts() {
        const pendingCount = document.querySelectorAll('#pending .test-case-item').length;
        const approvedCount = document.querySelectorAll('#approved .test-case-item').length;
        const rejectedCount = document.querySelectorAll('#rejected .test-case-item').length;
        
        document.querySelector('#pending-tab .badge').textContent = pendingCount;
        document.querySelector('#approved-tab .badge').textContent = approvedCount;
        document.querySelector('#rejected-tab .badge').textContent = rejectedCount;
    }

    // 添加分页链接的点击事件处理
    document.querySelectorAll('.pagination .page-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const pageType = this.getAttribute('data-page-type');
            const url = new URL(this.href);
            const page = url.searchParams.get(`${pageType}_page`);
            
            // 保持当前标签页的状态
            const currentTab = document.querySelector('.nav-tabs .nav-link.active');
            if (currentTab) {
                url.searchParams.set('active_tab', currentTab.getAttribute('href').substring(1));
            }
            
            // 跳转到新页面
            window.location.href = url.toString();
        });
    });
});