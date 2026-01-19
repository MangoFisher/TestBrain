"""
基于 LangChain 的工具定义。
将现有工具封装为 LangChain Tool 对象。
"""

from typing import Optional, Type, List, Dict, Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from .tools import GitTools, AnalyzerAPITools, SourceCodeTools


# ============================================
# Git 工具的 LangChain 封装
# ============================================

class CommitInfoInput(BaseModel):
    """获取 commit 信息的输入"""
    commit_hash: str = Field(description="commit 哈希值（完整或短哈希）")


class GetCommitInfoTool(BaseTool):
    """获取 commit 详细信息工具"""
    name: str = "get_commit_info"
    description: str = "获取 commit 的详细信息，包括作者、时间、提交信息等。当需要了解某个变更的背景时使用。"
    args_schema: Type[BaseModel] = CommitInfoInput
    
    git_tools: GitTools = Field(default=None, exclude=True)
    
    def _run(self, commit_hash: str) -> str:
        """执行工具"""
        result = self.git_tools.get_commit_info(commit_hash)
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    async def _arun(self, commit_hash: str) -> str:
        """异步执行（暂不支持）"""
        return self._run(commit_hash)


class ChangedFilesInput(BaseModel):
    """获取变更文件的输入"""
    base_commit: str = Field(description="基准 commit 哈希")
    new_commit: str = Field(description="新 commit 哈希")


class GetChangedFilesTool(BaseTool):
    """获取变更文件列表工具"""
    name: str = "get_changed_files"
    description: str = "获取两个 commit 之间变更的文件列表。快速了解变更范围时使用。"
    args_schema: Type[BaseModel] = ChangedFilesInput
    
    git_tools: GitTools = Field(default=None, exclude=True)
    
    def _run(self, base_commit: str, new_commit: str) -> str:
        result = self.git_tools.get_changed_files(base_commit, new_commit)
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)


class GetChangedFilesDetailedTool(BaseTool):
    """获取详细变更信息工具"""
    name: str = "get_changed_files_detailed"
    description: str = """获取详细的文件变更信息，包括变更类型、行数统计和 hunk 信息。
    
返回格式包含：
- path: 文件路径
- changeType: 变更类型（ADD/MODIFY/DELETE）
- hunks: 变更行块，包含 oldStart, oldLines, newStart, newLines
- additions/deletions: 新增/删除行数统计

这个工具的输出可以直接传递给 map_hunks_to_symbols 进行影响分析。"""
    args_schema: Type[BaseModel] = ChangedFilesInput
    
    git_tools: GitTools = Field(default=None, exclude=True)
    
    def _run(self, base_commit: str, new_commit: str) -> str:
        import json
        result = self.git_tools.get_changed_files_detailed(base_commit, new_commit)
        
        # 转换为符合后端 API 的格式
        normalized_result = []
        for item in result:
            if "error" in item:
                continue
                
            # 确定文件路径
            path = item.get("b_path") or item.get("a_path") or "unknown"
            
            # 转换变更类型
            change_type_map = {
                "A": "ADD",
                "D": "DELETE",
                "M": "MODIFY",
                "R": "RENAME"
            }
            change_type = change_type_map.get(item.get("change_type", "M"), "MODIFY")
            
            normalized = {
                "path": path,
                "changeType": change_type,
                "hunks": item.get("hunks", []),
                "additions": item.get("additions", 0),
                "deletions": item.get("deletions", 0)
            }
            
            normalized_result.append(normalized)
        
        return json.dumps(normalized_result, ensure_ascii=False, indent=2)


class FileDiffInput(BaseModel):
    """获取文件 diff 的输入"""
    base_commit: str = Field(description="基准 commit 哈希")
    new_commit: str = Field(description="新 commit 哈希")
    file_path: str = Field(description="文件路径")
    offset: int = Field(default=0, description="起始行号（从0开始），用于分段读取大 diff")
    limit: int = Field(default=300, description="读取的行数。默认300行，可根据需要调整")


class GetFileDiffTool(BaseTool):
    """获取文件 diff 工具"""
    name: str = "get_file_diff"
    description: str = """获取特定文件在两个 commit 之间的 diff 内容（变更部分）。支持分段读取大 diff。

⚠️ 重要区别：
- ❌ 不是读取完整文件内容（那是 read_file 或 get_file_content_by_commit）
- ✅ 只返回两个版本之间的差异（diff），通常比完整文件小得多
- ✅ diff 的总行数 ≠ 文件的总行数

📖 使用方式：
- **小 diff (<300行)**: 直接调用 get_file_diff(base, new, path) 即可
- **大 diff (>300行)**: 分段读取
  * 第1段: get_file_diff(base, new, path, offset=0, limit=300)
  * 第2段: get_file_diff(base, new, path, offset=300, limit=300)
  * 继续调用直到读完
  * ⚠️ offset 必须基于 diff 的总行数，不是文件的总行数！

💡 工具会在输出末尾显示 diff 总行数和当前读取范围，方便判断是否需要继续读取

📌 典型场景：
- ✅ 查看某个文件在两个 commit 之间改了什么
- ❌ 不要用于读取文件的完整内容"""
    args_schema: Type[BaseModel] = FileDiffInput
    
    git_tools: GitTools = Field(default=None, exclude=True)
    
    def _run(self, base_commit: str, new_commit: str, file_path: str, offset: int = 0, limit: int = 300) -> str:
        # 直接调用底层方法，所有分段逻辑已在底层实现
        return self.git_tools.get_file_diff(base_commit, new_commit, file_path, offset, limit)


class FileContentInput(BaseModel):
    """获取文件内容的输入"""
    commit_hash: str = Field(description="commit 哈希")
    file_path: str = Field(description="文件路径")
    offset: int = Field(default=0, description="起始行号（从0开始），用于分段读取大文件")
    limit: int = Field(default=500, description="读取的行数。默认500行，可根据需要调整")


class GetFileContentByCommitTool(BaseTool):
    """获取文件内容工具"""
    name: str = "get_file_content_by_commit"
    description: str = """获取特定 commit 中某个文件的内容。支持分段读取大文件。

📖 使用方式：
- **小文件 (<500行)**: 直接调用 get_file_content_by_commit(commit, path) 即可
- **大文件 (>500行)**: 分段读取
  * 第1段: get_file_content_by_commit(commit, path, offset=0, limit=500)
  * 第2段: get_file_content_by_commit(commit, path, offset=500, limit=500)
  * 继续调用直到读完

⚠️ 大文件处理建议：
- 优先使用 get_file_diff 查看变更部分（最高效）
- 或使用 search_in_file 搜索关键内容
- 只在必须了解完整文件时才分段读取全文

💡 工具会在输出末尾显示文件总行数和当前读取范围，方便判断是否需要继续读取"""
    args_schema: Type[BaseModel] = FileContentInput
    
    git_tools: GitTools = Field(default=None, exclude=True)
    
    def _run(self, commit_hash: str, file_path: str, offset: int = 0, limit: int = 500) -> str:
        # 直接调用底层方法，所有分段逻辑已在底层实现
        return self.git_tools.get_file_content_by_commit(commit_hash, file_path, offset, limit)


class CommitsBetweenInput(BaseModel):
    """获取提交历史的输入"""
    base_commit: str = Field(description="基准 commit 哈希")
    new_commit: str = Field(description="新 commit 哈希")
    max_count: int = Field(
        default=20, 
        description="""最多返回的 commit 数量。建议根据时间跨度调整：
        - 小型变更（<1周）: 10-15 个
        - 中型变更（1-2周）: 20-30 个 [默认]
        - 大型变更（>1月）: 50-100 个
        合理设置可以完整了解演进历史而不遗漏关键信息。
        如果不确定，可以先用默认值，根据返回结果判断是否需要增大"""
    )


class GetCommitsBetweenTool(BaseTool):
    """获取提交历史工具"""
    name: str = "get_commits_between"
    description: str = """获取两个 commit 之间的所有提交历史。了解变更演进过程时使用。

📖 使用建议：
- 先用默认 max_count=20 获取，观察时间跨度
- 如果返回的 commit 数量等于 max_count，说明可能还有更多 commit 未获取
- 根据两个 commit 的日期差异，适当增大 max_count

💡 工具会在输出末尾显示实际返回的 commit 数量和时间跨度信息"""
    args_schema: Type[BaseModel] = CommitsBetweenInput
    
    git_tools: GitTools = Field(default=None, exclude=True)
    
    def _run(self, base_commit: str, new_commit: str, max_count: int = 20) -> str:
        result = self.git_tools.get_commits_between(base_commit, new_commit, max_count)
        import json
        
        # 添加元信息反馈
        if isinstance(result, list) and len(result) > 0:
            actual_count = len(result)
            
            # 获取时间跨度
            first_date = result[0].get('date', '') if result else ''
            last_date = result[-1].get('date', '') if result else ''
            
            meta_info = f"\n\n{'='*70}\n"
            meta_info += f"📊 获取到 {actual_count} 个 commit\n"
            meta_info += f"📅 时间范围: {last_date} → {first_date}\n"
            
            # 判断是否可能有更多 commit
            if actual_count == max_count:
                meta_info += f"⚠️  返回数量达到上限 ({max_count})，可能还有更多 commit 未获取\n"
                meta_info += f"💡 如需获取完整历史，请增大 max_count，建议:\n"
                meta_info += f"   get_commits_between('{base_commit}', '{new_commit}', max_count={max_count * 2})\n"
            else:
                meta_info += f"✅ 已获取完整提交历史\n"
            
            meta_info += f"{'='*70}\n"
            
            return json.dumps(result, ensure_ascii=False, indent=2) + meta_info
        else:
            return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================
# 源码分析 API 工具的 LangChain 封装
# ============================================

class IndexProjectInput(BaseModel):
    """索引项目的输入"""
    repo_path: str = Field(description="项目根路径")


class IndexProjectTool(BaseTool):
    """索引项目工具"""
    name: str = "index_project"
    description: str = "索引 Java 项目，构建调用图。这是使用源码分析功能的第一步，必须先索引才能进行后续分析。"
    args_schema: Type[BaseModel] = IndexProjectInput
    
    api_tools: AnalyzerAPITools = Field(default=None, exclude=True)
    
    def _run(self, repo_path: str) -> str:
        result = self.api_tools.index_project(repo_path)
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)


class GetIndexStatusTool(BaseTool):
    """获取索引状态工具"""
    name: str = "get_index_status"
    description: str = "查询项目索引状态，确认是否已索引完成。"
    
    api_tools: AnalyzerAPITools = Field(default=None, exclude=True)
    
    def _run(self) -> str:
        result = self.api_tools.get_index_status()
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    async def _arun(self) -> str:
        return self._run()


class MapHunksInput(BaseModel):
    """映射变更到符号的输入"""
    changes: str = Field(
        description="""文件变更列表的 JSON 字符串。每项必须包含:
- path: 文件路径（相对于项目根目录）
- changeType: 变更类型（ADD/MODIFY/DELETE/RENAME）
- hunks: 变更行块列表，每个 hunk 包含：
  * oldStart: 旧文件起始行号
  * oldLines: 旧文件行数
  * newStart: 新文件起始行号
  * newLines: 新文件行数

示例格式：
[{
  "path": "src/main/java/Example.java",
  "changeType": "MODIFY",
  "hunks": [{"oldStart": 10, "oldLines": 5, "newStart": 10, "newLines": 8}]
}]"""
    )


class MapHunksToSymbolsTool(BaseTool):
    """映射变更到符号工具"""
    name: str = "map_hunks_to_symbols"
    description: str = """将文件变更映射到受影响的具体方法和类。用于精确识别变更影响的代码符号。

IMPORTANT: 输入必须是正确的格式，包含 path, changeType, hunks 字段。
hunks 必须是标准 Git diff 格式：oldStart, oldLines, newStart, newLines。

通常从 get_file_diff 获取 diff 内容后，解析出 hunk 信息再调用此工具。"""
    args_schema: Type[BaseModel] = MapHunksInput
    
    api_tools: AnalyzerAPITools = Field(default=None, exclude=True)
    
    def _run(self, changes: str) -> str:
        import json
        try:
            changes_list = json.loads(changes)
        except:
            # 如果已经是列表，直接使用
            changes_list = changes
        
        # 转换数据格式：将 AI 可能生成的简化格式转换为标准格式
        normalized_changes = []
        for change in changes_list:
            normalized = {
                "path": change.get("path", ""),
                "changeType": change.get("changeType", "MODIFY"),
                "hunks": []
            }
            
            # 处理 hunks 格式转换
            hunks = change.get("hunks", [])
            for hunk in hunks:
                if isinstance(hunk, dict):
                    # 如果是简化格式（startLine, endLine），转换为标准格式
                    if "startLine" in hunk and "endLine" in hunk:
                        start_line = hunk["startLine"]
                        end_line = hunk["endLine"]
                        line_count = max(1, end_line - start_line + 1)
                        normalized_hunk = {
                            "oldStart": start_line,
                            "oldLines": line_count,
                            "newStart": start_line,
                            "newLines": line_count
                        }
                    # 如果已经是标准格式，保持不变
                    elif "newStart" in hunk and "newLines" in hunk:
                        normalized_hunk = hunk
                    else:
                        # 如果格式无法识别，跳过
                        continue
                    
                    normalized["hunks"].append(normalized_hunk)
            
            # 如果没有 hunks，添加一个覆盖整个文件的 hunk（默认前 1000 行）
            if not normalized["hunks"]:
                normalized["hunks"].append({
                    "oldStart": 1,
                    "oldLines": 1000,
                    "newStart": 1,
                    "newLines": 1000
                })
            
            normalized_changes.append(normalized)
        
        result = self.api_tools.map_hunks_to_symbols(normalized_changes)
        return json.dumps(result, ensure_ascii=False, indent=2)


class AnalyzeImpactInput(BaseModel):
    """影响分析的输入"""
    seeds: str = Field(description="""种子方法/类的 JSON 字符串。
格式：{"methods": [{"fqnClass": "完整类名", "methodName": "方法名", "paramTypes": ["参数类型"]}], "classes": ["完整类名"]}
注意：类名必须使用完整包名（FQN），例如 "com.example.MyClass" 而不是 "MyClass"。
方法必须包含 fqnClass（完整类名）、methodName（方法名）、paramTypes（参数类型列表）。""")
    depth: int = Field(default=2, description="传播深度，建议 1-5")
    direction: str = Field(default="both", description="传播方向：inbound（向上找调用者）、outbound（向下找影响）、both（双向）")
    include_edges: bool = Field(default=True, description="是否返回调用边信息")


class AnalyzeImpactTool(BaseTool):
    """影响分析工具"""
    name: str = "analyze_impact"
    description: str = """分析变更的影响范围。基于调用图进行传播分析，找出受影响的方法。
重要：seeds 参数中的类名必须使用完整包名（如 com.example.MyClass），不能只用简单类名（MyClass）。
建议先使用 map_hunks_to_symbols 工具获取受影响的方法和类（会包含完整类名），再将其结果作为 seeds 传入本工具。
支持向上（找调用者/测试入口）、向下（找被调用/影响范围）、双向传播。"""
    args_schema: Type[BaseModel] = AnalyzeImpactInput
    
    api_tools: AnalyzerAPITools = Field(default=None, exclude=True)
    
    def _run(self, seeds: str, depth: int = 2, direction: str = "both", include_edges: bool = True) -> str:
        import json
        try:
            seeds_dict = json.loads(seeds)
        except:
            seeds_dict = seeds
        
        result = self.api_tools.analyze_impact(seeds_dict, depth, direction, include_edges)
        return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================
# 源码读取工具的 LangChain 封装
# ============================================

class ReadFileInput(BaseModel):
    """读取文件的输入"""
    relative_path: str = Field(description="相对于项目根的文件路径")
    max_lines: int = Field(default=500, description="每次读取的最大行数，默认 500 行")
    offset: int = Field(default=0, description="起始行号（从 0 开始），用于分段读取大文件")


class ReadFileTool(BaseTool):
    """读取文件工具"""
    name: str = "read_file"
    description: str = """读取项目中的文件内容。支持分段读取大文件。

⚠️ 重要限制：
- ❌ 只能读取文件，不能读取目录
- ❌ 要列出目录内容，请使用 list_directory 工具
- ❌ 要查找文件，请使用 find_file 工具

📖 使用方式：
- **小文件 (<500行)**: 直接调用 read_file(path) 即可
- **大文件 (>500行)**: 分段读取
  * 第1段: read_file(path, offset=0, max_lines=500)
  * 第2段: read_file(path, offset=500, max_lines=500)
  * 继续调用直到读完

💡 工具会在输出末尾显示文件总行数和当前读取范围，方便判断是否需要继续读取

⚠️ 使用注意事项：
- 大文件会消耗大量 token 和时间，影响执行效率
- 对于代码变更分析，优先使用 get_file_diff 查看具体改动
- 如果只需查找特定内容，优先使用 search_in_file
- 只在需要理解完整文件上下文时使用本工具

适用场景：
✅ README、配置文件等小文档（通常 <5KB，<500行）
✅ 需要理解完整代码逻辑和上下文
❌ 大型源码文件（建议先用 get_file_diff 或 search_in_file）
❌ 只想查看代码变更（应该用 get_file_diff）
❌ 查看目录有哪些文件（应该用 list_directory）"""
    args_schema: Type[BaseModel] = ReadFileInput
    
    source_tools: SourceCodeTools = Field(default=None, exclude=True)
    
    def _run(self, relative_path: str, max_lines: int = 500, offset: int = 0) -> str:
        result = self.source_tools.read_file(relative_path, max_lines, offset)
        return result


class SearchInFileInput(BaseModel):
    """搜索文件的输入"""
    relative_path: str = Field(description="文件路径")
    keyword: str = Field(description="搜索关键字")


class SearchInFileTool(BaseTool):
    """搜索文件工具"""
    name: str = "search_in_file"
    description: str = """在文件内容中搜索关键字。

⚠️ 重要限制：
- ❌ 在文件内容中搜索，不是搜索文件名
- ❌ 要查找文件，请使用 find_file 工具
- ❌ 要列出目录内容，请使用 list_directory 工具

✅ 适用场景：
- 在已知文件中查找特定方法、类或变量
- 查找包含特定关键字的代码行
- 定位某个字符串在文件中的位置

💡 使用示例：
- search_in_file("src/Main.java", "public static void")
- search_in_file("pom.xml", "spring-boot")"""
    args_schema: Type[BaseModel] = SearchInFileInput
    
    source_tools: SourceCodeTools = Field(default=None, exclude=True)
    
    def _run(self, relative_path: str, keyword: str) -> str:
        result = self.source_tools.search_in_file(relative_path, keyword)
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)


class ListJavaFilesInput(BaseModel):
    """列出 Java 文件的输入"""
    directory: str = Field(default="", description="相对目录路径，空字符串表示根目录")


class ListJavaFilesTool(BaseTool):
    """列出 Java 文件工具"""
    name: str = "list_java_files"
    description: str = "列出目录下的所有 Java 文件。返回按目录分组的统计信息和完整文件列表。"
    args_schema: Type[BaseModel] = ListJavaFilesInput
    
    source_tools: SourceCodeTools = Field(default=None, exclude=True)
    
    def _run(self, directory: str = "") -> str:
        result = self.source_tools.list_java_files(directory)
        import json
        from collections import defaultdict
        
        # 按目录分组统计
        dir_stats = defaultdict(list)
        for file_path in result:
            if isinstance(file_path, str) and not file_path.startswith("Error"):
                # 提取目录路径（去掉文件名）
                parts = file_path.split('/')
                if len(parts) > 1:
                    dir_path = '/'.join(parts[:-1])
                    dir_stats[dir_path].append(parts[-1])
                else:
                    dir_stats['根目录'].append(file_path)
        
        # 构建输出结构
        output = {
            "总计": len(result),
            "目录统计": {
                dir_path: {
                    "文件数": len(files),
                    "文件列表": sorted(files)
                }
                for dir_path, files in sorted(dir_stats.items())
            }
        }
        
        return json.dumps(output, ensure_ascii=False, indent=2)


class ListDirectoryInput(BaseModel):
    """列出目录内容的输入"""
    directory: str = Field(default="", description="相对目录路径，空字符串表示项目根目录")


class ListDirectoryTool(BaseTool):
    """列出目录内容工具"""
    name: str = "list_directory"
    description: str = """列出指定目录下的文件和子目录。
    
📁 用途：
- 查看项目根目录有哪些文件（如构建文件、配置文件）
- 浏览某个包下的目录结构
- 了解项目组织方式

📖 使用示例：
- list_directory("") → 列出项目根目录
- list_directory("src/main/java") → 列出 Java 源码目录
- list_directory("docs") → 列出文档目录

💡 提示：
- 只列出直接子项，不递归
- 目录以 / 结尾标识
- 显示文件大小"""
    args_schema: Type[BaseModel] = ListDirectoryInput
    
    source_tools: SourceCodeTools = Field(default=None, exclude=True)
    
    def _run(self, directory: str = "") -> str:
        result = self.source_tools.list_directory(directory)
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)


class FindFileInput(BaseModel):
    """查找文件的输入"""
    pattern: str = Field(description="文件名模式，支持通配符。例如: 'pom.xml', '*.xml', '**/*.properties'")
    max_results: int = Field(default=20, description="最多返回的结果数，默认 20")


class FindFileTool(BaseTool):
    """查找文件工具"""
    name: str = "find_file"
    description: str = """在项目中查找特定文件名。
    
🔍 用途：
- 查找构建文件（如 pom.xml, build.gradle, package.json）
- 查找配置文件（如 application.properties, config.yml, .gitignore）
- 查找文档（如 README.md, CHANGELOG.md）
- 查找特定扩展名的文件

📖 使用示例：
- find_file("pom.xml") → 查找精确文件名
- find_file("*.xml") → 查找所有 XML 文件
- find_file("README*") → 查找所有 README 文件
- find_file("*.properties") → 查找所有 properties 文件

💡 提示：
- 支持通配符 * 和 ?
- 递归搜索整个项目
- 默认最多返回 20 个结果"""
    args_schema: Type[BaseModel] = FindFileInput
    
    source_tools: SourceCodeTools = Field(default=None, exclude=True)
    
    def _run(self, pattern: str, max_results: int = 20) -> str:
        result = self.source_tools.find_file(pattern, max_results)
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================
# 工具创建函数
# ============================================

def create_langchain_tools(
    repo_path: str,
    api_base_url: str = "http://localhost:8089"
) -> List[BaseTool]:
    """
    创建所有 LangChain 工具。
    
    Args:
        repo_path: 项目路径
        api_base_url: API 基础 URL
        
    Returns:
        工具列表
    """
    from .tools import get_all_tools
    
    tools_instances = get_all_tools(repo_path, api_base_url)
    git = tools_instances["git"]
    api = tools_instances["api"]
    source = tools_instances["source"]
    
    tools = [
        # Git 工具
        GetCommitInfoTool(git_tools=git),
        GetChangedFilesTool(git_tools=git),
        GetChangedFilesDetailedTool(git_tools=git),
        GetFileDiffTool(git_tools=git),
        GetFileContentByCommitTool(git_tools=git),
        GetCommitsBetweenTool(git_tools=git),
        
        # API 工具
        IndexProjectTool(api_tools=api),
        GetIndexStatusTool(api_tools=api),
        MapHunksToSymbolsTool(api_tools=api),
        AnalyzeImpactTool(api_tools=api),
        
        # 源码工具
        ReadFileTool(source_tools=source),
        SearchInFileTool(source_tools=source),
        ListJavaFilesTool(source_tools=source),
        ListDirectoryTool(source_tools=source),
        FindFileTool(source_tools=source),
    ]
    
    return tools
