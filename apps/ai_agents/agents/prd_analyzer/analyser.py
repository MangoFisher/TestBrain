from typing import Dict, Any, List, Optional
import json
import logging

from apps.llm.base import BaseLLMService
from apps.knowledge.service import KnowledgeService
from .prompts import PrdAnalyserPrompt
from langchain_core.messages import SystemMessage, HumanMessage
from apps.utils.logger_manager import get_logger

class PrdAnalyserAgent:
    """PRD分析Agent，用于从PRD文档中提取测试点和测试场景"""
    
    def __init__(self, llm_service: BaseLLMService, knowledge_service: KnowledgeService = None):
        self.llm_service = llm_service
        self.knowledge_service = knowledge_service
        self.prompt = PrdAnalyserPrompt()
        self.logger = get_logger(self.__class__.__name__)
    
    def analyse(self, markdown_content: str) -> Dict[str, Any]:
        """
        分析PRD文档，提取测试点和测试场景
        
        Args:
            markdown_content: Markdown格式的PRD文档内容
            
        Returns:
            包含测试点和测试场景的字典，格式为：
            {
                "test_points": [...],
                "summary": {...}
            }
        """
        try:
            self.logger.info(f"开始分析PRD文档，文档长度：{len(markdown_content)} 字符")
            
            # 使用prompt模板格式化消息
            messages = self.prompt.format_messages(markdown_content=markdown_content)
            
            self.logger.info(f"构建后的PRD分析提示词: \n{'='*50}\n{messages}\n{'='*50}")
            
            # 调用LLM服务
            response = self.llm_service.invoke(messages)
            result = response.content
            
            # 解析JSON结果
            try:
                if "```json" in result:
                    json_str = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    json_str = result.split("```")[1].split("```")[0].strip()
                else:
                    json_str = result
                    
                analysis_result = json.loads(json_str)
                self.logger.info(f"成功解析PRD分析结果，包含测试点数量：{len(analysis_result.get('test_points', []))}")
                
                # 验证分析结果
                self._validate_analysis_result(analysis_result)
                
                return analysis_result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"解析JSON结果失败: {str(e)}")
                self.logger.error(f"原始响应: {result}")
                raise ValueError(f"无法解析生成的分析结果: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"PRD分析过程出错: {str(e)}", exc_info=True)
            raise Exception(f"PRD分析失败: {str(e)}")
    
    def _validate_analysis_result(self, result: Dict[str, Any]) -> bool:
        """
        验证分析结果是否符合预期格式
        
        Args:
            result: 分析结果字典
            
        Returns:
            如果符合格式返回True，否则抛出异常
        """
        # 检查是否包含测试点列表
        if "test_points" not in result or not isinstance(result["test_points"], list):
            raise ValueError("分析结果缺少有效的test_points列表")
        
        # 检查测试点是否包含必要字段
        for i, point in enumerate(result["test_points"]):
            required_fields = ["id", "title", "description", "priority", "scenarios"]
            for field in required_fields:
                if field not in point:
                    raise ValueError(f"测试点 #{i+1} 缺少必要字段: {field}")
            
            # 验证每个测试点的scenarios列表
            if not isinstance(point["scenarios"], list):
                raise ValueError(f"测试点 #{i+1} 的scenarios不是有效的列表")
            
            # 验证scenarios中的每个场景
            for j, scenario in enumerate(point["scenarios"]):
                scenario_fields = ["id", "title", "description", "test_type"]
                for field in scenario_fields:
                    if field not in scenario:
                        raise ValueError(f"测试点 #{i+1} 的测试场景 #{j+1} 缺少必要字段: {field}")
        
        # 检查汇总信息
        if "summary" not in result or not isinstance(result["summary"], dict):
            raise ValueError("分析结果缺少有效的summary信息")
            
        summary_fields = ["total_test_points", "total_test_scenarios", 
                         "high_priority_points", "medium_priority_points", "low_priority_points"]
        for field in summary_fields:
            if field not in result["summary"]:
                raise ValueError(f"汇总信息缺少必要字段: {field}")
        
        return True

