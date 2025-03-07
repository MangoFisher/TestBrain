// 测试用例评审页面专用脚本

// 评审功能的 JavaScript 代码
function reviewTestCase(testCaseId) {
    console.log('开始评审测试用例，ID:', testCaseId);
    
    fetch('/api/review/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            test_case_id: testCaseId  // 使用正确的字段名
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('评审响应:', data);
        if (data.success) {
            alert('评审完成！');
            // 可以添加页面刷新或状态更新的代码
            location.reload();
        } else {
            alert('评审失败：' + data.message);
        }
    })
    .catch(error => {
        console.error('评审请求失败:', error);
        alert('评审请求失败，请查看控制台获取详细信息');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // 获取所有评审按钮
    const reviewButtons = document.querySelectorAll('.review-button');
    
    // 为每个评审按钮添加点击事件监听器
    reviewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const testCaseId = this.getAttribute('data-id');
            reviewTestCase(testCaseId);
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
                    'X-CSRFToken': getCookie('csrftoken')
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
    
    // 显示评审结果
    function displayReviewResult(container, result) {
        let html = `
            <div class="card mt-3">
                <div class="card-header">
                    评审结果 - 评分: <span class="badge ${getScoreBadgeClass(result.score)}">${result.score}/10</span>
                    <span class="badge ${result.recommendation === '通过' ? 'badge-success' : 'badge-danger'} float-right">
                        ${result.recommendation}
                    </span>
                </div>
                <div class="card-body">
                    <p><strong>总体评价:</strong> ${result.comments}</p>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <h5>优点:</h5>
                            <ul>
                                ${result.strengths.map(item => `<li>${item}</li>`).join('')}
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h5>缺点:</h5>
                            <ul>
                                ${result.weaknesses.map(item => `<li>${item}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                    
                    <div class="mt-3">
                        <div class="form-group">
                            <label for="review-comments-${result.test_case_id}">评审意见:</label>
                            <textarea id="review-comments-${result.test_case_id}" class="form-control" rows="3"></textarea>
                        </div>
                        
                        <div class="btn-group">
                            <button class="btn btn-success status-button" data-id="${result.test_case_id}" data-status="approved">
                                通过
                            </button>
                            <button class="btn btn-danger status-button" data-id="${result.test_case_id}" data-status="rejected">
                                拒绝
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
        
        // 重新绑定新添加的按钮事件
        container.querySelectorAll('.status-button').forEach(button => {
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
                        'X-CSRFToken': getCookie('csrftoken')
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
                        setTimeout(() => location.reload(), 1000);
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
    
    // 获取评分对应的徽章类
    function getScoreBadgeClass(score) {
        if (score >= 8) return 'badge-success';
        if (score >= 6) return 'badge-warning';
        return 'badge-danger';
    }
    
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
});