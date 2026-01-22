// Java源码分析页面的JavaScript功能

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('javaCodeAnalysisForm');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');
    
    // 隐藏所有状态信息
    function hideAllMessages() {
        loadingIndicator.style.display = 'none';
        errorMessage.style.display = 'none';
        successMessage.style.display = 'none';
    }
    
    // 显示加载状态
    function showLoading() {
        hideAllMessages();
        loadingIndicator.style.display = 'block';
    }
    
    // 显示错误信息
    function showError(message) {
        hideAllMessages();
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }
    
    function clearSuccessMessage() {
        while (successMessage.firstChild) {
            successMessage.removeChild(successMessage.firstChild);
        }
    }

    function showSuccessWithDownload(message, downloadUrl, filename) {
        // 只隐藏 loading / error，不隐藏 resultContainer
        loadingIndicator.style.display = 'none';
        errorMessage.style.display = 'none';

        clearSuccessMessage();
        successMessage.appendChild(document.createTextNode(message));

        if (downloadUrl && filename) {
            successMessage.appendChild(document.createElement('br'));
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.textContent = filename;
            link.target = '_blank';
            link.rel = 'noopener';
            successMessage.appendChild(link);
        }

        successMessage.style.display = 'block';
    }
    
    // 表单提交事件处理
    form.addEventListener('submit', async function(e) {
        e.preventDefault(); // 阻止默认表单提交
        
        // 获取表单数据
        const targetService = document.getElementById('targetService').value;
        const baseCommit = document.getElementById('baseCommit').value;
        const newCommit = document.getElementById('newCommit').value;
        const llmProvider = document.getElementById('llmProvider').value;
        
        // 验证输入
        if (!targetService || !baseCommit || !newCommit) {
            showError('请填写所有必填字段');
            return;
        }
        
        // 禁用按钮以防止重复提交
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = '分析中...';
        
        try {
            showLoading();
            
            // 发送分析请求
            const response = await fetch('/java_code_analyzer/api/java-code-analyzer-service/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') // 获取CSRF令牌
                },
                body: JSON.stringify({
                    target_service: targetService,
                    base_commit: baseCommit,
                    new_commit: newCommit,
                    llm_provider: llmProvider
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success) {
                    // 成功：显示成功提示 + 下载链接
                    loadingIndicator.style.display = 'none';
                    errorMessage.style.display = 'none';

                    showSuccessWithDownload(
                        'Java源码分析报告已成功生成，可点击下面链接下载',
                        data.report_download_url,
                        data.report_filename
                    );
                } else {
                    showError(data.error || '分析失败');
                }
            } else {
                const errorData = await response.json();
                showError(errorData.error || '请求失败');
            }
        } catch (error) {
            console.error('分析请求失败:', error);
            showError('网络错误或服务器不可用: ' + error.message);
        } finally {
            // 恢复按钮状态
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = '开始分析';
        }
    });
    
    // 获取CSRF令牌的辅助函数
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
    
    // 目标服务选择变化事件处理
    document.getElementById('targetService').addEventListener('change', function() {
        const selectedValue = this.value;
        if (selectedValue === 'custom') {
            // 如果选择了自定义服务，可以在这里添加额外的输入字段
            console.log('用户选择了自定义服务');
        }
    });
    
    // 初始化页面状态
    hideAllMessages();
});