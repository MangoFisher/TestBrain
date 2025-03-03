// 测试用例评审页面专用脚本

document.addEventListener('DOMContentLoaded', function() {
    // 获取所有评审按钮
    const reviewButtons = document.querySelectorAll('.review-button');
    
    // 为每个评审按钮添加点击事件
    reviewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const testCaseId = this.getAttribute('data-id');
            const reviewContainer = document.getElementById(`review-result-${testCaseId}`);
            const loadingIndicator = document.getElementById(`loading-indicator-${testCaseId}`);
            
            // 显示加载指示器
            loadingIndicator.style.display = 'block';
            reviewContainer.innerHTML = '';
            this.disabled = true;
            
            // 发送请求到后端
            fetch('/api/review/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    test_case_id: testCaseId
                })
            })
            .then(response => response.json())
            .then(data => {
                // 隐藏加载指示器
                loadingIndicator.style.display = 'none';
                this.disabled = false;
                
                if (data.success) {
                    // 显示评审结果
                    displayReviewResult(reviewContainer, data.review_result);
                } else {
                    reviewContainer.innerHTML = `<div class="alert alert-danger">${data.message || '评审测试用例时出错'}</div>`;
                }
            })
            .catch(error => {
                loadingIndicator.style.display = 'none';
                this.disabled = false;
                reviewContainer.innerHTML = `<div class="alert alert-danger">请求失败: ${error.message}</div>`;
            });
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
                        <h5>改进建议:</h5>
                        <ul>
                            ${result.suggestions.map(item => `<li>${item}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div class="mt-3">
                        <h5>缺失场景:</h5>
                        <ul>
                            ${result.missing_scenarios.map(item => `<li>${item}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div class="form-group mt-4">
                        <label for="review-comments-${container.id.split('-').pop()}">评审意见:</label>
                        <textarea id="review-comments-${container.id.split('-').pop()}" class="form-control" rows="3" 
                            placeholder="请输入您的评审意见...">${result.comments}</textarea>
                    </div>
                    
                    <div class="text-right">
                        <button class="btn btn-success status-button" 
                            data-id="${container.id.split('-').pop()}" 
                            data-status="approved">
                            通过
                        </button>
                        <button class="btn btn-danger status-button ml-2" 
                            data-id="${container.id.split('-').pop()}" 
                            data-status="rejected">
                            不通过
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
        
        // 为新添加的按钮绑定事件
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
    }
    
    // 根据评分获取徽章类
    function getScoreBadgeClass(score) {
        if (score >= 8) return 'badge-success';
        if (score >= 6) return 'badge-warning';
        return 'badge-danger';
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
}); 