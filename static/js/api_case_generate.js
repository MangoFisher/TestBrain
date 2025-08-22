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
            const response = await fetch('/api_case_generate/', {
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
            checkboxCell.className = 'text-center';
            checkboxCell.style.verticalAlign = 'middle';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'form-check-input api-checkbox';
            checkbox.value = api.path;
            checkbox.id = `api-${api.path.replace(/[^a-zA-Z0-9]/g, '-')}`;
            checkbox.style.margin = '0';
            checkbox.style.transform = 'scale(1.2)';
            
            checkboxCell.appendChild(checkbox);
            
            // 第二列：API路径
            const pathCell = document.createElement('td');
            pathCell.innerHTML = `<code>${api.method} ${api.path}</code>`;
            
            // 第三列：API名称
            const nameCell = document.createElement('td');
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
        
        const countPerApi = document.getElementById('count-per-api').value;
        const priority = document.getElementById('priority').value;
        const llmProvider = document.getElementById('llm-provider').value;
        
        // 显示进度界面
        document.getElementById('api-selection').style.display = 'none';
        document.getElementById('generation-progress').style.display = 'block';
        
        // 发送生成请求
        generateTestCases(selectedApis, countPerApi, priority, llmProvider);
    });

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
            
            const response = await fetch('/api_case_generate/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                showGenerationResult(result);
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

    // 显示生成结果
    function showGenerationResult(result) {
        document.getElementById('generation-progress').style.display = 'none';
        document.getElementById('generation-result').style.display = 'block';
        
        document.getElementById('result-message').textContent = result.message;
        document.getElementById('download-link').href = `/download_file/?file_path=${encodeURIComponent(result.file_path)}`;
    }
});
