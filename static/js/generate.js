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
    
    // 提交表单生成测试用例
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
    
    // 保存测试用例
    saveButton.addEventListener('click', function() {
        const testCases = JSON.parse(sessionStorage.getItem('generatedTestCases') || '[]');
        const inputType = sessionStorage.getItem('inputType');
        const inputText = sessionStorage.getItem('inputText');
        
        if (!testCases.length) {
            showNotification('没有可保存的测试用例', 'error');
            return;
        }
        
        saveButton.disabled = true;
        saveButton.textContent = '保存中...';
        
        // 发送请求到后端
        fetch('/api/save-test-case/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                test_cases: testCases,
                input_type: inputType,
                input_text: inputText
            })
        })
        .then(response => response.json())
        .then(data => {
            saveButton.textContent = '保存测试用例';
            
            if (data.success) {
                showNotification('测试用例保存成功', 'success');
                // 清除会话存储
                sessionStorage.removeItem('generatedTestCases');
                sessionStorage.removeItem('inputType');
                sessionStorage.removeItem('inputText');
            } else {
                saveButton.disabled = false;
                showNotification(data.message || '保存测试用例失败', 'error');
            }
        })
        .catch(error => {
            saveButton.disabled = false;
            saveButton.textContent = '保存测试用例';
            showNotification('请求失败: ' + error.message, 'error');
        });
    });
    
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
}); 