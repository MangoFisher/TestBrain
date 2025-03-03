// 知识库管理页面专用脚本

document.addEventListener('DOMContentLoaded', function() {
    const addKnowledgeForm = document.getElementById('add-knowledge-form');
    const knowledgeList = document.getElementById('knowledge-list');
    const searchInput = document.getElementById('knowledge-search');
    
    // 加载知识库列表
    loadKnowledgeList();
    
    // 添加知识条目
    if (addKnowledgeForm) {
        addKnowledgeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const titleInput = document.getElementById('knowledge-title');
            const contentInput = document.getElementById('knowledge-content');
            
            const title = titleInput.value.trim();
            const content = contentInput.value.trim();
            
            if (!title) {
                showNotification('请输入知识条目标题', 'error');
                return;
            }
            
            if (!content) {
                showNotification('请输入知识条目内容', 'error');
                return;
            }
            
            // 禁用提交按钮
            const submitButton = this.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            submitButton.textContent = '添加中...';
            
            // 发送请求到后端
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
                submitButton.disabled = false;
                submitButton.textContent = '添加知识条目';
                
                if (data.success) {
                    showNotification('知识条目添加成功', 'success');
                    
                    // 清空表单
                    titleInput.value = '';
                    contentInput.value = '';
                    
                    // 重新加载知识库列表
                    loadKnowledgeList();
                } else {
                    showNotification(data.message || '添加知识条目失败', 'error');
                }
            })
            .catch(error => {
                submitButton.disabled = false;
                submitButton.textContent = '添加知识条目';
                showNotification('请求失败: ' + error.message, 'error');
            });
        });
    }
    
    // 搜索知识库
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const knowledgeItems = document.querySelectorAll('.list-group-item');
            
            knowledgeItems.forEach(item => {
                const title = item.querySelector('h5').textContent.toLowerCase();
                const content = item.querySelector('p').textContent.toLowerCase();
                
                if (title.includes(searchTerm) || content.includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
    
    // 加载知识库列表
    function loadKnowledgeList() {
        if (!knowledgeList) return;
        
        knowledgeList.innerHTML = `
            <div class="text-center">
                <div class="spinner"></div>
                <p>加载知识库...</p>
            </div>
        `;
        
        fetch('/api/knowledge-list/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayKnowledgeList(data.knowledge_items);
                } else {
                    knowledgeList.innerHTML = `<div class="alert alert-danger">${data.message || '加载知识库失败'}</div>`;
                }
            })
            .catch(error => {
                knowledgeList.innerHTML = `<div class="alert alert-danger">请求失败: ${error.message}</div>`;
            });
    }
    
    // 显示知识库列表
    function displayKnowledgeList(items) {
        if (!items || !items.length) {
            knowledgeList.innerHTML = '<div class="alert alert-info">知识库为空</div>';
            return;
        }
        
        let html = '<div class="list-group">';
        
        items.forEach(item => {
            const date = new Date(item.created_at);
            const formattedDate = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
            
            html += `
                <div class="list-group-item">
                    <div class="d-flex justify-content-between">
                        <h5>${item.title}</h5>
                        <small>${formattedDate}</small>
                    </div>
                    <p>${item.content}</p>
                </div>
            `;
        });
        
        html += '</div>';
        knowledgeList.innerHTML = html;
    }
}); 