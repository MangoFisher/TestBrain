// 测试用例生成页面专用脚本

document.addEventListener('DOMContentLoaded', function() {
    const generateForm = document.getElementById('generate-form');
    const inputTypeRadios = document.querySelectorAll('input[name="input_type"]');
    const inputTextLabel = document.getElementById('input-text-label');
    const inputText = document.getElementById('input-text');
    const generateButton = document.getElementById('generate-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultContainer = document.getElementById('result-container');
    const saveButton = document.getElementById('save-button');
    
    // 根据输入类型更改标签文本
    if (inputTypeRadios && inputTypeRadios.length > 0) {
        inputTypeRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (this.value === 'requirement') {
                    inputTextLabel.textContent = '需求描述:';
                    inputText.placeholder = '请输入需求描述...';
                } else {
                    inputTextLabel.textContent = '代码片段:';
                    inputText.placeholder = '请输入代码片段...';
                }
            });
        });
    }
    
    // 保存用户选择的大模型到本地存储
    const llmProviderSelect = document.getElementById('llm-provider');
    if (llmProviderSelect) {
        llmProviderSelect.addEventListener('change', function() {
            localStorage.setItem('preferred-llm-provider', this.value);
        });
        
        // 页面加载时恢复用户之前的选择（如果后端没有指定值）
        if (!llmProviderSelect.options[llmProviderSelect.selectedIndex].hasAttribute('selected')) {
            const savedProvider = localStorage.getItem('preferred-llm-provider');
            if (savedProvider) {
                // 确保保存的值在当前选项中存在
                for (let i = 0; i < llmProviderSelect.options.length; i++) {
                    if (llmProviderSelect.options[i].value === savedProvider) {
                        llmProviderSelect.value = savedProvider;
                        break;
                    }
                }
            }
        }
    }
    
    // 表单提交时显示加载指示器
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function() {
            if (loadingIndicator) {
                loadingIndicator.style.display = 'block';
            }
            if (generateButton) {
                generateButton.disabled = true;
            }
        });
    }
    
    // 提交表单生成测试用例 (原有功能，保留以兼容API调用方式)
    if (generateForm) {
        generateForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // 获取表单数据
            const inputType = document.querySelector('input[name="input_type"]:checked').value;
            const inputTextValue = inputText.value.trim();
            
            if (!inputTextValue) {
                showNotification('请输入' + (inputType === 'requirement' ? '需求描述' : '代码片段'), 'error');
                return;
            }
            
            // 显示加载指示器
            loadingIndicator.style.display = 'block';
            resultContainer.innerHTML = '';
            saveButton.disabled = true;
            
            // 发送请求到后端
            fetch('/api/generate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    input_type: inputType,
                    input_text: inputTextValue
                })
            })
            .then(response => response.json())
            .then(data => {
                // 隐藏加载指示器
                loadingIndicator.style.display = 'none';
                
                if (data.success) {
                    // 显示生成的测试用例
                    displayTestCases(data.test_cases);
                    saveButton.disabled = false;
                    
                    // 保存生成的测试用例到会话存储
                    sessionStorage.setItem('generatedTestCases', JSON.stringify(data.test_cases));
                    sessionStorage.setItem('inputType', inputType);
                    sessionStorage.setItem('inputText', inputTextValue);
                } else {
                    resultContainer.innerHTML = `<div class="alert alert-danger">${data.message || '生成测试用例时出错'}</div>`;
                }
            })
            .catch(error => {
                loadingIndicator.style.display = 'none';
                resultContainer.innerHTML = `<div class="alert alert-danger">请求失败: ${error.message}</div>`;
            });
        });
    }
    
    // 保存测试用例
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            console.log('保存按钮被点击'); // 调试日志
            
            // 尝试从会话存储获取数据
            let testCases = null;
            try {
                // 首先尝试从页面元素获取
                const testCasesScript = document.getElementById('test-cases-data');
                if (testCasesScript) {
                    testCases = JSON.parse(testCasesScript.textContent);
                } else {
                    // 如果页面元素不存在，尝试从会话存储获取
                    testCases = JSON.parse(sessionStorage.getItem('generatedTestCases') || '[]');
                }
            } catch (error) {
                console.error('解析测试用例数据失败:', error);
                alert('解析测试用例数据失败，请查看控制台获取详细信息');
                return;
            }
            
            if (!testCases || testCases.length === 0) {
                alert('没有可保存的测试用例');
                return;
            }
            
            // 获取其他必要数据
            const requirementElement = document.getElementById('input-text');
            const llmProviderElement = document.getElementById('llm-provider');
            
            // 检查元素是否存在
            if (!requirementElement) {
                console.error('缺失需求描述元素 (input-text)');
            }
            if (!llmProviderElement) {
                console.error('缺失LLM提供商选择元素 (llm-provider)');
            }
            
            if (!requirementElement || !llmProviderElement) {
                alert('页面元素缺失，无法保存数据。请查看控制台获取详细信息。');
                return;
            }
            
            // 准备请求数据
            const requestData = {
                test_cases: testCases,
                requirement: requirementElement.value,
                llm_provider: llmProviderElement.value
            };
            
            // 如果有会话存储中的数据，也考虑使用
            const inputType = sessionStorage.getItem('inputType');
            const inputText = sessionStorage.getItem('inputText');
            if (inputType) {
                requestData.input_type = inputType;
            }
            if (inputText && !requestData.requirement) {
                requestData.requirement = inputText;
            }
            
            // 禁用按钮防止重复提交
            saveButton.disabled = true;
            saveButton.textContent = '保存中...';
            
            // 发送保存请求
            fetch('/core/save-test-case/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            })
            .then(response => response.json())
            .then(data => {
                saveButton.textContent = '保存测试用例';
                
                if (data.success) {
                    alert('测试用例保存成功！');
                    // 清除会话存储
                    sessionStorage.removeItem('generatedTestCases');
                    sessionStorage.removeItem('inputType');
                    sessionStorage.removeItem('inputText');
                } else {
                    saveButton.disabled = false;
                    alert('保存失败：' + (data.message || '未知错误'));
                }
            })
            .catch(error => {
                saveButton.disabled = false;
                saveButton.textContent = '保存测试用例';
                console.error('保存失败:', error);
                alert('保存失败，请查看控制台获取详细信息');
            });
        });
    }
    
    // 显示测试用例
    function displayTestCases(testCases) {
        if (!testCases || !testCases.length) {
            resultContainer.innerHTML = '<div class="alert alert-info">没有生成测试用例</div>';
            return;
        }
        
        let html = '<h3>生成的测试用例</h3>';
        
        testCases.forEach((testCase, index) => {
            html += `
                <div class="card mb-3">
                    <div class="card-header">
                        <h4>${testCase.title}</h4>
                    </div>
                    <div class="card-body">
                        <p><strong>描述:</strong> ${testCase.description}</p>
                        
                        <div class="mt-3">
                            <h5>测试步骤:</h5>
                            <div class="test-steps">${testCase.test_steps}</div>
                        </div>
                        
                        <div class="mt-3">
                            <h5>预期结果:</h5>
                            <div class="expected-results">${testCase.expected_results}</div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        resultContainer.innerHTML = html;
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