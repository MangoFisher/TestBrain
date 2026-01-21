// 接口case生成页面专用脚本

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('single_file');
    const submitBtn = document.getElementById('submitBtn');
    const selectedFileDiv = document.getElementById('selected-file');
    const statusDiv = document.getElementById('uploadStatus');

    // 文件选择事件处理
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            updateFileName(this);
        });
    }

    // 拖拽上传区域事件处理
    const uploadArea = document.querySelector('.upload-area');
    if (uploadArea) {
        // 阻止默认拖拽行为
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });

        // 拖拽进入和离开时的视觉反馈
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });

        // 文件拖拽放置处理
        uploadArea.addEventListener('drop', handleDrop, false);
    }

    // 表单提交事件处理
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleSubmit(e);
        });
    }

    // 更新文件名显示
    function updateFileName(input) {
        if (input.files && input.files[0]) {
            selectedFileDiv.style.display = 'block';
            selectedFileDiv.textContent = '已选择文件: ' + input.files[0].name;
            
            // 验证文件类型
            const fileName = input.files[0].name;
            if (!fileName.toLowerCase().endsWith('.json')) {
                statusDiv.textContent = '请选择JSON格式的文件';
                statusDiv.style.color = '#dc3545';
                submitBtn.disabled = true;
            } else {
                statusDiv.textContent = '';
                submitBtn.disabled = false;
            }
        } else {
            selectedFileDiv.style.display = 'none';
            selectedFileDiv.textContent = '';
            statusDiv.textContent = '';
            submitBtn.disabled = false;
        }
    }

    // 阻止默认拖拽行为
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // 拖拽进入时高亮
    function highlight(e) {
        uploadArea.classList.add('highlight');
    }

    // 拖拽离开时取消高亮
    function unhighlight(e) {
        uploadArea.classList.remove('highlight');
    }

    // 处理文件拖拽放置
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files;
            updateFileName(fileInput);
        }
    }

    // 处理表单提交
    async function handleSubmit(event) {
        const form = event.target;
        const fileInput = form.querySelector('input[type="file"]');
        
        if (!fileInput.files || !fileInput.files[0]) {
            statusDiv.textContent = '请先选择要上传的文件';
            statusDiv.style.color = '#dc3545';
            return false;
        }

        // 验证文件类型
        const fileName = fileInput.files[0].name;
        if (!fileName.toLowerCase().endsWith('.json')) {
            statusDiv.textContent = '请选择JSON格式的文件';
            statusDiv.style.color = '#dc3545';
            return false;
        }

        submitBtn.disabled = true;
        statusDiv.textContent = '正在上传文件，请稍候...';
        statusDiv.style.color = '#007bff';
        statusDiv.style.fontWeight = 'bold';

        try {
            const formData = new FormData(form);
            
            // 发送POST请求到api_case_generate路由
            const response = await fetch('/api_case_generator/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });

            const result = await response.json();

            if (result.success) {
                statusDiv.textContent = `文件上传成功！正在解析接口信息...`;
                statusDiv.style.color = '#28a745';
                fileInput.value = '';
                selectedFileDiv.style.display = 'none';
                
                // 处理API列表
                handleFileUploadSuccess(result);
            } else {
                statusDiv.textContent = result.error || '上传失败，请重试';
                statusDiv.style.color = '#dc3545';
            }
        } catch (error) {
            console.error('上传错误:', error);
            statusDiv.textContent = '上传过程中发生错误，请重试';
            statusDiv.style.color = '#dc3545';
        } finally {
            submitBtn.disabled = false;
        }

        return false;
    }

    // 处理文件上传成功后的API列表显示
    function handleFileUploadSuccess(response) {
        if (response.success && response.api_list) {
            // 隐藏上传区域，显示接口选择界面
            document.querySelector('.upload-container').style.display = 'none';
            document.getElementById('api-selection').style.display = 'block';
            
            // 生成接口表格行
            generateApiTableRows(response.api_list);
            
            // 保存文件路径
            window.uploadedFilePath = response.file_path;

            // 初始化规则编辑区：从后端拉取模版规则
            fetch('/api_case_generator/api/testcase-rule-template/')
                .then(r => r.json())
                .then(data => {
                    if (data && data.success) {
                        window.defaultRuleText = data.rule_text || '';
                        const editor = document.getElementById('rule-editor');
                        if (editor) {
                            editor.value = window.defaultRuleText;
                            updateCharCount();
                            setupRuleEditorValidation();
                        }
                    }
                })
                .catch(() => {});
        }
    }

    // 更新字符计数显示
    function updateCharCount() {
        const editor = document.getElementById('rule-editor');
        const charCount = document.getElementById('rule-char-count');
        if (editor && charCount) {
            const currentLength = editor.value.length;
            charCount.textContent = `${currentLength}/1000`;
            
            // 根据字符数量改变颜色
            if (currentLength > 1000) {
                charCount.style.color = '#dc3545'; // 红色
            } else if (currentLength > 800) {
                charCount.style.color = '#ffc107'; // 黄色
            } else {
                charCount.style.color = '#6c757d'; // 灰色
            }
        }
    }

    // 设置规则编辑器验证
    function setupRuleEditorValidation() {
        const editor = document.getElementById('rule-editor');
        if (!editor) return;

        // 字符类型验证：只允许中英文字符和标点符号
        editor.addEventListener('input', function(e) {
            const value = e.target.value;
            // 允许中英文字符、数字、空格、换行、制表符，以及中英文标点符号
            const validValue = value.replace(/[^\u4e00-\u9fa5a-zA-Z0-9\s\n\r\t\u3000-\u303f\uff00-\uffef\u2000-\u206f\u0020-\u002f\u003a-\u0040\u005b-\u0060\u007b-\u007e]/g, '');
            
            if (value !== validValue) {
                e.target.value = validValue;
                showValidationMessage('只允许输入中英文、数字和标点符号', 'error');
            } else {
                clearValidationMessage();
            }
            
            updateCharCount();
        });

        // 字符长度限制
        editor.addEventListener('input', function(e) {
            const value = e.target.value;
            if (value.length > 1000) {
                e.target.value = value.substring(0, 1000);
                showValidationMessage('字符数量不能超过1000个', 'error');
            } else {
                clearValidationMessage();
            }
            updateCharCount();
        });

        // 粘贴事件处理
        editor.addEventListener('paste', function(e) {
            setTimeout(() => {
                const value = e.target.value;
                const validValue = value.replace(/[^\u4e00-\u9fa5a-zA-Z0-9\s\n\r\t\u3000-\u303f\uff00-\uffef\u2000-\u206f\u0020-\u002f\u003a-\u0040\u005b-\u0060\u007b-\u007e]/g, '');
                
                if (value !== validValue) {
                    e.target.value = validValue;
                    showValidationMessage('粘贴内容包含非法字符（仅允许中英文、数字和标点），已自动过滤', 'warning');
                }
                
                if (value.length > 1000) {
                    e.target.value = value.substring(0, 1000);
                    showValidationMessage('粘贴内容超过1000字符限制，已截断', 'warning');
                }
                
                updateCharCount();
            }, 0);
        });
    }

    // 显示验证消息
    function showValidationMessage(message, type) {
        const msgEl = document.getElementById('rule-validate-msg');
        if (msgEl) {
            msgEl.textContent = message;
            msgEl.style.color = type === 'error' ? '#dc3545' : '#ffc107';
        }
    }

    // 清除验证消息
    function clearValidationMessage() {
        const msgEl = document.getElementById('rule-validate-msg');
        if (msgEl) {
            msgEl.textContent = '';
            msgEl.style.color = '#6c757d';
        }
    }

    // 生成接口表格行
    function generateApiTableRows(apiList) {
        const tbody = document.getElementById('api-table-body');
        tbody.innerHTML = '';
        
        apiList.forEach(api => {
            // 调试日志：打印每个API的完整数据
            console.log('API数据:', api);
            console.log('has_test_cases:', api.has_test_cases);
            console.log('test_case_count:', api.test_case_count, '类型:', typeof api.test_case_count);
            
            const row = document.createElement('tr');
            
            // 第一列：勾选框
            const checkboxCell = document.createElement('td');
            checkboxCell.style.width = '80px';
            checkboxCell.style.textAlign = 'center';
            checkboxCell.style.padding = '8px';
            checkboxCell.style.border = '1px solid #dee2e6';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'api-checkbox';
            checkbox.value = api.path;
            checkbox.id = `api-${api.path.replace(/[^a-zA-Z0-9]/g, '-')}`;
            checkbox.style.margin = '0';
            checkbox.style.transform = 'scale(1.2)';
            
            checkboxCell.appendChild(checkbox);
            
            // 第二列：API路径
            const pathCell = document.createElement('td');
            pathCell.style.width = '40%';
            pathCell.style.padding = '8px';
            pathCell.style.border = '1px solid #dee2e6';
            pathCell.innerHTML = `<code>${api.method} ${api.path}</code>`;
            
            // 第三列：API名称
            const nameCell = document.createElement('td');
            nameCell.style.padding = '8px';
            nameCell.style.border = '1px solid #dee2e6';
            let nameContent = api.name;
            if (api.has_test_cases) {
                let cnt = null;
                if (api.test_case_count !== undefined && api.test_case_count !== null) {
                    const n = Number(api.test_case_count);
                    if (!Number.isNaN(n)) cnt = n;
                }
                console.log('计算后的cnt:', cnt);
                nameContent += ` <span class="badge badge-info">已有（<span style="font-size: 2.0em; font-weight: bold; color: red;">${cnt}</span>）条测试用例</span>`;
            }
            nameCell.innerHTML = nameContent;
            
            // 组装行
            row.appendChild(checkboxCell);
            row.appendChild(pathCell);
            row.appendChild(nameCell);
            
            tbody.appendChild(row);
        });
        
        // 绑定全选功能
        bindSelectAllFunctionality();
    }

    // 生成测试用例按钮事件
    document.getElementById('generateBtn').addEventListener('click', function() {
        const selectedApis = getSelectedApis();
        if (selectedApis.length === 0) {
            alert('请至少选择一个接口');
            return;
        }
        
        const countInput = document.getElementById('count-per-api');
        let countPerApi = parseInt(countInput.value || '0', 10);
        if (isNaN(countPerApi) || countPerApi <= 0) {
            alert('每个接口生成数量必须为正整数');
            countInput.focus();
            return;
        }
        
        const totalCount = selectedApis.length * countPerApi;
        if (totalCount < 1 || totalCount > 100) {
            alert(`单次生成测试用例数量不能超过100条`);
            return;
        }
        
        const priority = document.getElementById('priority').value;
        const llmProvider = document.getElementById('llm-provider').value;
        
        // 显示进度界面和日志区域
        document.getElementById('api-selection').style.display = 'none';
        document.getElementById('generation-progress').style.display = 'block';
        document.getElementById('live-logs').style.display = 'block';
        
        // 发送生成请求
        generateTestCases(selectedApis, countPerApi, priority, llmProvider);
    });

    // 对“每个接口生成测试用例数量”的输入框仅允许数字
    (function enforceDigitOnlyForCountInput() {
        const countInput = document.getElementById('count-per-api');
        if (!countInput) return;

        // 提示移动端弹出数字键盘
        try {
            countInput.setAttribute('inputmode', 'numeric');
            countInput.setAttribute('pattern', '\\d*');
        } catch (_) {}

        const sanitize = () => {
            const digits = (countInput.value || '').replace(/\D+/g, '');
            countInput.value = digits;
        };

        countInput.addEventListener('input', sanitize);
        countInput.addEventListener('paste', function() {
            setTimeout(sanitize, 0);
        });
        countInput.addEventListener('blur', function() {
            sanitize();
            if (countInput.value === '' || countInput.value === '0') {
                countInput.value = '1';
            }
        });
    })();

    // 绑定全选功能
    function bindSelectAllFunctionality() {
        const selectAllCheckbox = document.getElementById('select-all');
        const apiCheckboxes = document.querySelectorAll('.api-checkbox');
        
        // 全选复选框点击事件
        selectAllCheckbox.addEventListener('change', function() {
            const isChecked = this.checked;
            
            // 更新所有API复选框状态
            apiCheckboxes.forEach(checkbox => {
                checkbox.checked = isChecked;
            });
        });
        
        // 单个API复选框点击事件
        apiCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                updateSelectAllState();
            });
        });
    }
    
    // 更新全选复选框状态
    function updateSelectAllState() {
        const selectAllCheckbox = document.getElementById('select-all');
        const apiCheckboxes = document.querySelectorAll('.api-checkbox');
        const checkedCount = document.querySelectorAll('.api-checkbox:checked').length;
        const totalCount = apiCheckboxes.length;
        
        if (checkedCount === 0) {
            // 没有选中任何API
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (checkedCount === totalCount) {
            // 全部选中
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else {
            // 部分选中
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        }
    }
    
    // 获取选中的接口
    function getSelectedApis() {
        const checkboxes = document.querySelectorAll('#api-table-body input[type="checkbox"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }

    // 生成测试用例
    async function generateTestCases(selectedApis, countPerApi, priority, llmProvider) {
        try {
            const formData = new FormData();
            formData.append('generate_test_cases', 'true');
            formData.append('file_path', window.uploadedFilePath);
            formData.append('selected_apis', JSON.stringify(selectedApis));
            formData.append('count_per_api', countPerApi);
            formData.append('priority', priority);
            formData.append('llm_provider', llmProvider);
            // 附带规则覆盖（若与默认不同且校验通过）
            const editor = document.getElementById('rule-editor');
            const msgEl = document.getElementById('rule-validate-msg');
            let rulesOverride = '';
            if (editor) {
                const current = (editor.value || '').trim();
                const defaultText = (window.defaultRuleText || '').trim();
                if (current && current !== defaultText) {
                    // 验证字符类型和长度
                    const isValidChars = /^[\u4e00-\u9fa5a-zA-Z0-9\s\n\r\t\u3000-\u303f\uff00-\uffef\u2000-\u206f\u0020-\u002f\u003a-\u0040\u005b-\u0060\u007b-\u007e]*$/.test(current);
                    const isValidLength = current.length <= 1000;
                    
                    if (!isValidChars) {
                        if (msgEl) {
                            msgEl.textContent = '规则包含非法字符，只允许中英文字符和标点符号，已忽略自定义规则。';
                            msgEl.style.color = '#dc3545';
                        }
                    } else if (!isValidLength) {
                        if (msgEl) {
                            msgEl.textContent = '规则文本过长（>1000字符），已忽略自定义规则，继续使用模版。';
                            msgEl.style.color = '#dc3545';
                        }
                    } else {
                        rulesOverride = current;
                        if (msgEl) {
                            msgEl.textContent = '已使用自定义规则';
                            msgEl.style.color = '#28a745';
                        }
                    }
                }
            }
            if (rulesOverride) {
                formData.append('rules_override', rulesOverride);
            }
            
            const response = await fetch('/api_case_generator/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 开始轮询进度
                if (result.task_id) {
                    window.currentTaskId = result.task_id;
                    // 优先尝试 SSE，失败回退轮询
                    startSSE(result.task_id);
                }
            } else {
                alert('生成失败: ' + result.error);
                // 返回选择界面
                document.getElementById('generation-progress').style.display = 'none';
                document.getElementById('api-selection').style.display = 'block';
            }
            
        } catch (error) {
            console.error('生成测试用例失败:', error);
            alert('生成失败: ' + error.message);
            // 返回选择界面
            document.getElementById('generation-progress').style.display = 'none';
            document.getElementById('api-selection').style.display = 'block';
        }
    }

    // 轮询获取进度
    async function pollProgress(taskId) {
        try {
            const resp = await fetch(`/api_case_generator/api/get-generation-progress/?task_id=${encodeURIComponent(taskId)}`);
            const data = await resp.json();
            if (!data.success) return;
            updateProgressUI(data.progress);
            if (data.progress && data.progress.percentage >= 100) {
                if (window.progressTimer) {
                    clearInterval(window.progressTimer);
                    window.progressTimer = null;
                }
            }
        } catch (e) {
            console.error('进度查询失败:', e);
        }
    }

    // SSE 优先，失败回退轮询
    function startSSE(taskId) {
        try {
            // 清理旧连接
            if (window.es) {
                try { window.es.close(); } catch (_) {}
                window.es = null;
            }

            // 先立即拉一次，避免等待首条日志事件
            pollProgress(taskId);

            const url = `/api/stream-logs/?task_id=${encodeURIComponent(taskId)}`;
            const es = new EventSource(url);
            window.es = es;

            es.onopen = () => {
                // 连接建立后再拉一次，确保状态最新
                pollProgress(taskId);
            };
            // 收到日志事件后拉一次最新进度
            es.addEventListener('log', () => {
                pollProgress(taskId);
            });
            // 后端 progress 事件：定期驱动刷新
            es.addEventListener('progress', () => {
                pollProgress(taskId);
            });
            es.onerror = () => {
                // 连接异常，回退到轮询
                try { es.close(); } catch (_) {}
                window.es = null;
                // 启动轮询作为兜底
                if (!window.progressTimer) {
                    window.progressTimer = setInterval(() => pollProgress(taskId), 2000);
                }
            };
            // 无论连接是否稳定，都启动轻量兜底轮询（完成时自动清理）
            if (!window.progressTimer) {
                window.progressTimer = setInterval(() => pollProgress(taskId), 2000);
            }
        } catch (_) {
            // 直接回退轮询
            pollProgress(taskId);
            if (!window.progressTimer) {
                window.progressTimer = setInterval(() => pollProgress(taskId), 2000);
            }
        }
    }

    function updateProgressUI(progress) {
        const bar = document.getElementById('progress-bar');
        const text = document.getElementById('progress-text');
        const currentApi = document.getElementById('current-api');
        const logsBox = document.getElementById('live-logs');
        
        if (bar && typeof progress.percentage === 'number') {
            bar.style.width = progress.percentage + '%';
        }
        if (text && progress.message) {
            text.textContent = progress.message;
        }
        if (currentApi) {
            currentApi.textContent = progress.current_api ? `当前接口：${progress.current_api}` : '';
        }
        if (logsBox && Array.isArray(progress.logs)) {
            logsBox.innerHTML = progress.logs.map(l => `<div>${formatLogEntry(l)}</div>`).join('');
            logsBox.scrollTop = logsBox.scrollHeight;
        }
        // 完成后自动显示结果（若无文件路径也先展示完成状态，链接在可用时再赋值）
        if (progress.percentage >= 100) {
            // 隐藏进度条相关元素
            document.getElementById('progress-bar').style.display = 'none';
            document.getElementById('progress-text').style.display = 'none';
            document.getElementById('current-api').style.display = 'none';
            
            // 隐藏进度区域的标题
            const progressTitle = document.querySelector('#generation-progress h3');
            if (progressTitle) {
                progressTitle.style.display = 'none';
            }
            
            // 切换到结果区域，隐藏整个进度容器，日志区域保持显示
            const progressContainer = document.getElementById('generation-progress');
            if (progressContainer) progressContainer.style.display = 'none';
            document.getElementById('generation-result').style.display = 'block';
            document.getElementById('live-logs').style.display = 'block';
            document.getElementById('result-message').textContent = progress.message || 'API测试用例生成完成';
            if (progress.file_path) {
                document.getElementById('download-link').href = `/api_case_generator/download_file/?file_path=${encodeURIComponent(progress.file_path)}`;
                document.getElementById('download-link').classList.remove('disabled');
            }
            // 完成后清理 SSE 与轮询
            if (window.es) {
                try { window.es.close(); } catch (_) {}
                window.es = null;
            }
            if (window.progressTimer) {
                clearInterval(window.progressTimer);
                window.progressTimer = null;
            }
        }
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function formatLogEntry(logEntry) {
        const escaped = escapeHtml(logEntry);
        
        // 根据日志级别添加颜色
        if (escaped.includes(' - ERROR - ')) {
            return `<span style="color: #ff6b6b;">${escaped}</span>`; // 红色 - 错误
        } else if (escaped.includes(' - WARNING - ')) {
            return `<span style="color: #ffa726;">${escaped}</span>`; // 橙色 - 警告
        } else {
            return `<span style="color: #ffffff;">${escaped}</span>`; // 白色 - 其他所有级别
        }
    }

    // 显示生成结果
    function showGenerationResult(result) {
        document.getElementById('generation-progress').style.display = 'none';
        document.getElementById('generation-result').style.display = 'block';
        
        document.getElementById('result-message').textContent = result.message;
        document.getElementById('download-link').href = `/api_case_generator/download_file/?file_path=${encodeURIComponent(result.file_path)}`;
    }
});
