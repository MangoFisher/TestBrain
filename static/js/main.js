// 主JavaScript文件

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initPage();
    
    // 绑定事件监听器
    bindEventListeners();
});

function initPage() {
    // 根据当前页面初始化不同功能
    const currentPath = window.location.pathname;
    
    if (currentPath.includes('/generate')) {
        initGeneratePage();
    } else if (currentPath.includes('/review')) {
        initReviewPage();
    } else if (currentPath.includes('/knowledge')) {
        initKnowledgePage();
    }
}

function bindEventListeners() {
    // 通用事件监听器
    
    // 表单提交前验证
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    });
    
    // 显示/隐藏元素
    const toggleButtons = document.querySelectorAll('[data-toggle]');
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-toggle');
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                if (targetElement.style.display === 'none') {
                    targetElement.style.display = 'block';
                } else {
                    targetElement.style.display = 'none';
                }
            }
        });
    });
}

// 表单验证
function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('is-invalid');
            
            // 添加错误提示
            let errorMessage = field.getAttribute('data-error-message') || '此字段不能为空';
            let errorElement = document.createElement('div');
            errorElement.className = 'invalid-feedback';
            errorElement.textContent = errorMessage;
            
            // 移除已有的错误提示
            const existingError = field.parentNode.querySelector('.invalid-feedback');
            if (existingError) {
                existingError.remove();
            }
            
            field.parentNode.appendChild(errorElement);
        } else {
            field.classList.remove('is-invalid');
            const existingError = field.parentNode.querySelector('.invalid-feedback');
            if (existingError) {
                existingError.remove();
            }
        }
    });
    
    return isValid;
}

// 测试用例生成页面初始化
function initGeneratePage() {
    const generateForm = document.getElementById('generate-form');
    const generateButton = document.getElementById('generate-button');
    const saveButton = document.getElementById('save-button');
    const resultContainer = document.getElementById('result-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    //TODO: 貌似跟generate.js重复
    if (generateForm) {
        generateForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // 显示加载指示器
            if (loadingIndicator) {
                loadingIndicator.style.display = 'block';
            }
            
            // 禁用生成按钮
            if (generateButton) {
                generateButton.disabled = true;
                generateButton.innerHTML = '<span class="spinner"></span> 生成中...';
            }
            
            // 获取表单数据
            const formData = new FormData(generateForm);
            const inputType = document.querySelector('input[name="input_type"]:checked').value;
            const inputText = document.getElementById('input-text').value;
            
            // 发送AJAX请求
            fetch('/api/generate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    input_type: inputType,
                    input: inputText
                })
            })
            .then(response => response.json())
            .then(data => {
                // 隐藏加载指示器
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                
                // 恢复生成按钮
                if (generateButton) {
                    generateButton.disabled = false;
                    generateButton.textContent = '生成测试用例';
                }
                
                // 显示结果
                if (resultContainer) {
                    displayTestCases(data.test_cases, resultContainer);
                    
                    // 启用保存按钮
                    if (saveButton) {
                        saveButton.disabled = false;
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                
                // 隐藏加载指示器
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
                
                // 恢复生成按钮
                if (generateButton) {
                    generateButton.disabled = false;
                    generateButton.textContent = '生成测试用例';
                }
                
                // 显示错误信息
                if (resultContainer) {
                    resultContainer.innerHTML = `<div class="alert alert-danger">生成测试用例时出错: ${error.message}</div>`;
                }
            });
        });
    }
    
    // 保存测试用例，貌似跟generate.js重复
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            const testCases = collectTestCasesFromUI();
            const inputType = document.querySelector('input[name="input_type"]:checked').value;
            const inputText = document.getElementById('input-text').value;
            
            fetch('/test_case_generator-drop/save-test-case/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    test_cases: testCases,
                    requirements: inputType === 'requirements' ? inputText : '',
                    code_snippet: inputType === 'code' ? inputText : ''
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('测试用例保存成功', 'success');
                } else {
                    showNotification('测试用例保存失败: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('测试用例保存失败: ' + error.message, 'danger');
            });
        });
    }
}

// 测试用例评审页面初始化
function initReviewPage() {
    const reviewButtons = document.querySelectorAll('.review-button');
    const statusButtons = document.querySelectorAll('.status-button');
    
    // 评审按钮点击事件
    reviewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const testCaseId = this.getAttribute('data-id');
            
            // 显示加载指示器
            this.innerHTML = '<span class="spinner"></span> 评审中...';
            this.disabled = true;
            
            fetch('/api/review/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    test_case_id: [testCaseId]
                })
            })
            .then(response => response.json())
            .then(data => {
                // 恢复按钮状态
                this.textContent = '评审';
                this.disabled = false;
                
                // 显示评审结果
                if (data.success) {
                    displayReviewResults(data.review_results, testCaseId);
                } else {
                    showNotification('评审失败: ' + data.errors.join(', '), 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                
                // 恢复按钮状态
                this.textContent = '评审';
                this.disabled = false;
                
                showNotification('评审失败: ' + error.message, 'danger');
            });
        });
    });
    
    // 状态更新按钮点击事件
    statusButtons.forEach(button => {
        button.addEventListener('click', function() {
            const testCaseId = this.getAttribute('data-id');
            const status = this.getAttribute('data-status');
            const commentsElement = document.getElementById(`comments-${testCaseId}`);
            const comments = commentsElement ? commentsElement.value : '';
            
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
                if (data.success) {
                    showNotification('状态更新成功', 'success');
                    
                    // 更新UI
                    updateTestCaseStatus(testCaseId, status);
                } else {
                    showNotification('状态更新失败: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('状态更新失败: ' + error.message, 'danger');
            });
        });
    });
}

// 知识库页面初始化
function initKnowledgePage() {
    const addKnowledgeForm = document.getElementById('add-knowledge-form');
    
    if (addKnowledgeForm) {
        addKnowledgeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const title = document.getElementById('knowledge-title').value;
            const content = document.getElementById('knowledge-content').value;
            
            fetch('/api/add-knowledge/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    title: title,
                    content: content
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('知识条目添加成功', 'success');
                    
                    // 清空表单
                    document.getElementById('knowledge-title').value = '';
                    document.getElementById('knowledge-content').value = '';
                    
                    // 刷新知识列表
                    loadKnowledgeList();
                } else {
                    showNotification('知识条目添加失败: ' + data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('知识条目添加失败: ' + error.message, 'danger');
            });
        });
    }
    
    // 初始加载知识列表
    loadKnowledgeList();
}

// 辅助函数

// 显示测试用例
function displayTestCases(testCases, container) {
    if (!testCases || testCases.length === 0) {
        container.innerHTML = '<div class="alert alert-info">没有生成测试用例</div>';
        return;
    }
    
    let html = '<div class="test-cases-container">';
    
    testCases.forEach((testCase, index) => {
        html += `
            <div class="test-case-item" data-index="${index}">
                <h3>${testCase.title}</h3>
                <p>${testCase.description}</p>
                <div class="form-group">
                    <label>测试步骤:</label>
                    <div class="test-steps">${testCase.test_steps}</div>
                </div>
                <div class="form-group">
                    <label>预期结果:</label>
                    <div class="expected-results">${testCase.expected_results}</div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// 从UI收集测试用例数据
function collectTestCasesFromUI() {
    const testCases = [];
    const testCaseItems = document.querySelectorAll('.test-case-item');
    
    testCaseItems.forEach(item => {
        const title = item.querySelector('h3').textContent;
        const description = item.querySelector('p').textContent;
        const testSteps = item.querySelector('.test-steps').innerHTML;
        const expectedResults = item.querySelector('.expected-results').innerHTML;
        
        testCases.push({
            title: title,
            description: description,
            test_steps: testSteps,
            expected_results: expectedResults
        });
    });
    
    return testCases;
}

// 显示评审结果
function displayReviewResults(reviewResults, testCaseId) {
    const resultContainer = document.getElementById(`review-result-${testCaseId}`);
    if (!resultContainer) return;
    
    const review = reviewResults.find(r => r.test_case_index.toString() === testCaseId);
    if (!review) {
        resultContainer.innerHTML = '<div class="alert alert-warning">未找到评审结果</div>';
        return;
    }
    
    let statusBadge = '';
    if (review.status === 'approved') {
        statusBadge = '<span class="badge badge-success">建议通过</span>';
    } else {
        statusBadge = '<span class="badge badge-danger">建议不通过</span>';
    }
    
    let html = `
        <div class="card mt-3">
            <div class="card-header">
                评审结果 ${statusBadge}
            </div>
            <div class="card-body">
                <h5>评审意见:</h5>
                <p>${review.comments}</p>
                
                <h5>改进建议:</h5>
                <p>${review.suggestions}</p>
                
                <div class="form-group mt-3">
                    <label for="comments-${testCaseId}">添加评审备注:</label>
                    <textarea id="comments-${testCaseId}" class="form-control" rows="3"></textarea>
                </div>
                
                <div class="text-right">
                    <button class="btn btn-success status-button" data-id="${testCaseId}" data-status="approved">
                        标记为通过
                    </button>
                    <button class="btn btn-danger status-button" data-id="${testCaseId}" data-status="rejected">
                        标记为不通过
                    </button>
                </div>
            </div>
        </div>
    `;
    
    resultContainer.innerHTML = html;
    
    // 重新绑定状态按钮事件
    const statusButtons = resultContainer.querySelectorAll('.status-button');
    statusButtons.forEach(button => {
        button.addEventListener('click', function() {
            const testCaseId = this.getAttribute('data-id');
            const status = this.getAttribute('data-status');
            const commentsElement = document.getElementById(`comments-${testCaseId}`);
            const comments = commentsElement ? commentsElement.value : '';
            
            updateTestCaseStatus(testCaseId, status, comments);
        });
    });
}

// 更新测试用例状态
function updateTestCaseStatus(testCaseId, status, comments = '') {
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
        if (data.success) {
            showNotification('状态更新成功', 'success');
            
            // 更新UI
            const testCaseElement = document.getElementById(`test-case-${testCaseId}`);
            if (testCaseElement) {
                // 移除所有状态类
                testCaseElement.classList.remove('pending', 'approved', 'rejected');
                
                // 添加新状态类
                if (status === 'approved') {
                    testCaseElement.classList.add('approved');
                } else if (status === 'rejected') {
                    testCaseElement.classList.add('rejected');
                } else {
                    testCaseElement.classList.add('pending');
                }
                
                // 更新状态标签
                const statusBadge = testCaseElement.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = 'badge status-badge';
                    if (status === 'approved') {
                        statusBadge.classList.add('badge-success');
                        statusBadge.textContent = '评审通过';
                    } else if (status === 'rejected') {
                        statusBadge.classList.add('badge-danger');
                        statusBadge.textContent = '评审未通过';
                    } else {
                        statusBadge.classList.add('badge-warning');
                        statusBadge.textContent = '待评审';
                    }
                }
            }
        } else {
            showNotification('状态更新失败: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('状态更新失败: ' + error.message, 'danger');
    });
}

// 加载知识库列表
function loadKnowledgeList() {
    const knowledgeListContainer = document.getElementById('knowledge-list');
    if (!knowledgeListContainer) return;
    
    fetch('/api/knowledge-list/')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayKnowledgeList(data.knowledge_items, knowledgeListContainer);
            } else {
                knowledgeListContainer.innerHTML = `<div class="alert alert-danger">加载知识库失败: ${data.message}</div>`;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            knowledgeListContainer.innerHTML = `<div class="alert alert-danger">加载知识库失败: ${error.message}</div>`;
        });
}

// 显示知识库列表
function displayKnowledgeList(knowledgeItems, container) {
    if (!knowledgeItems || knowledgeItems.length === 0) {
        container.innerHTML = '<div class="alert alert-info">知识库中没有条目</div>';
        return;
    }
    
    let html = '<div class="list-group">';
    
    knowledgeItems.forEach(item => {
        html += `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">${item.title}</h5>
                    <small>ID: ${item.id}</small>
                </div>
                <p class="mb-1">${item.content.substring(0, 150)}${item.content.length > 150 ? '...' : ''}</p>
                <small>创建时间: ${new Date(item.created_at).toLocaleString()}</small>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// 显示通知
function showNotification(message, type = 'info') {
    const notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        // 创建通知容器
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '1000';
        document.body.appendChild(container);
    }
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.style.marginBottom = '10px';
    notification.innerHTML = message;
    
    // 添加关闭按钮
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'close';
    closeButton.innerHTML = '&times;';
    closeButton.addEventListener('click', function() {
        notification.remove();
    });
    
    notification.appendChild(closeButton);
    
    // 添加到容器
    document.getElementById('notification-container').appendChild(notification);
    
    // 自动关闭
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// 获取CSRF令牌
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

// 初始化标签页切换
document.addEventListener('DOMContentLoaded', function() {
    const tabLinks = document.querySelectorAll('.nav-tabs .nav-link');
    
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // 移除所有活动状态
            tabLinks.forEach(l => l.classList.remove('active'));
            const tabContents = document.querySelectorAll('.tab-pane');
            tabContents.forEach(c => {
                c.classList.remove('show', 'active');
            });
            
            // 设置当前标签为活动状态
            this.classList.add('active');
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.classList.add('show', 'active');
            }
        });
    });
}); 