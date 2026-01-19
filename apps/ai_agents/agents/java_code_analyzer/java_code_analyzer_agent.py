"""
基于 LangChain 的测试范围分析 Agent。
使用 LangChain 的 Agent 框架进行工具编排和决策。
"""

from typing import Optional, List, Dict, Any
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from .java_code_analyzer_tools import create_langchain_tools
from .prompts import JavaCodeAnalyzerPromptManager
from apps.llm.base import LLMServiceFactory


class JavaCodeAnalyzerAgent:
    """基于 LangChain 的 Java 代码分析 Agent"""
    
    def __init__(
        self,
        repo_path: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "deepseek-chat",
        java_analyzer_service_url: str = "http://localhost:8089",
        max_iterations: int = 15, # 默认的React Agent迭代次数
        verbose: bool = True
    ):
        """
        初始化 Agent。
        
        Args:
            repo_path: 项目路径
            api_key: DeepSeek API 密钥（或其他兼容 OpenAI API 的密钥）
            base_url: API 基础 URL（DeepSeek: https://api.deepseek.com）
            model: 模型名称（默认: deepseek-reasoner，推理模型）
            java_analyzer_service_url: java源码分析服务URL
            max_iterations: 最大迭代次数
            verbose: 是否输出详细日志
        """
        self.repo_path = repo_path
        self.verbose = verbose
        self.model = model
        
        # 初始化提示词管理器
        self.prompt_manager = JavaCodeAnalyzerPromptManager()
        
        # 设置默认 base_url 为 DeepSeek
        if base_url is None:
            base_url = "https://api.deepseek.com"
        
        # 使用 LLMServiceFactory 创建 LLM 服务实例
        llm_config = {
            "model": model,
            "base_url": base_url,
        }
        if api_key:
            llm_config["api_key"] = api_key
        
        # 根据模型类型决定是否添加 temperature 参数
        if "reasoner" not in model.lower():
            # 推理模型不支持 temperature 参数
            pass
        else:
            # 对话模型支持 temperature 参数
            llm_config["temperature"] = 0.7  # type: ignore
        
        # 从模型名称推断提供商 (如 deepseek-chat, deepseek-reasoner -> deepseek)
        provider = model.split('-')[0].lower()
        if provider not in ['deepseek', 'qwen']:
            provider = 'deepseek'  # 默认使用 deepseek
        
        self.llm = LLMServiceFactory.create(provider, **llm_config)
        
        # 创建工具
        self.tools = create_langchain_tools(repo_path, java_analyzer_service_url)
        
        # 获取系统提示词
        system_prompt = self.prompt_manager.get_system_prompt()
        
        # 创建 agent graph (使用 LangGraph)
        self.agent_executor = create_react_agent(
            self.llm,
            self.tools,
            prompt=system_prompt  # 使用从配置加载的提示词
        )
        
        self.max_iterations = max_iterations
    
    def analyze(self, base_commit: str, new_commit: str) -> Dict[str, Any]:
        """
        分析两个 commit 之间的变更影响。
        
        Args:
            base_commit: 基准 commit
            new_commit: 新 commit
            
        Returns:
            包含分析结果的字典
        """
        # 使用提示词管理器生成用户提示词
        user_input = self.prompt_manager.get_user_prompt(self.repo_path, base_commit, new_commit)
        
        if self.verbose:
            print("="*70)
            print("🤖 开始 LangChain Agent 分析")
            print("="*70)
            print(f"📁 项目: {self.repo_path}")
            print(f"🔄 变更: {base_commit[:8]} → {new_commit[:8]}")
            print(f"🧠 模型: {getattr(self.llm, 'model_name', self.model)}")
            print("="*70)
            print()
        
        # 执行 agent - 使用 stream 模式以获取详细执行信息
        try:
            # 设置递归限制（需要足够大以支持多次工具调用）
            from langchain_core.runnables.config import RunnableConfig
            config: RunnableConfig = {"configurable": {"recursion_limit": max(100, self.max_iterations * 3)}}
            
            step_count = 0
            all_messages = []
            
            if self.verbose:
                print("📝 用户输入:")
                print("-"*70)
                print(user_input)
                print("="*70)
                print()
            
            # 使用 stream 来捕获每一步
            for event in self.agent_executor.stream(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config
            ):
                # 处理每个节点的输出
                for node_name, node_data in event.items():
                    if self.verbose:
                        step_count += 1
                        print(f"\n{'='*70}")
                        print(f"✅ 步骤 {step_count}: 节点 {node_name}")
                        print(f"{'='*70}")
                    
                    # 获取消息
                    if "messages" in node_data:
                        messages = node_data["messages"]
                        for msg in messages:
                            all_messages.append(msg)
                            
                            if self.verbose:
                                # 区分不同类型的消息
                                if hasattr(msg, 'type'):
                                    msg_type = msg.type
                                elif hasattr(msg, '__class__'):
                                    msg_type = msg.__class__.__name__
                                else:
                                    msg_type = "unknown"
                                
                                print(f"\n📨 消息类型: {msg_type}")
                                print("-"*70)
                                
                                # AI 消息（包含思考和工具调用）
                                if msg_type == 'ai' or 'AI' in str(type(msg)):
                                    # 打印内容
                                    if hasattr(msg, 'content') and msg.content:
                                        print("🤖 AI 思考/回复:")
                                        print(msg.content)
                                    
                                    # 打印工具调用
                                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                        print("\n🔧 工具调用:")
                                        for tool_call in msg.tool_calls:
                                            print(f"  - 工具: {tool_call.get('name', 'unknown')}")
                                            print(f"    参数: {tool_call.get('args', {})}")
                                
                                # 工具消息（工具执行结果）
                                elif msg_type == 'tool' or 'Tool' in str(type(msg)):
                                    print("🛠️  工具执行结果:")
                                    if hasattr(msg, 'name'):
                                        print(f"  工具名: {msg.name}")
                                    if hasattr(msg, 'content'):
                                        content_str = str(msg.content)
                                        tmp_flag = False #临时控制全部打印的标志, 方便本地调试查看接口返回内容是否正确
                                        # 限制输出长度
                                        if len(content_str) > 500 and tmp_flag:
                                            print(f"  结果: {content_str[:500]}...\n  (共 {len(content_str)} 字符)")
                                        else:
                                            print(f"  结果: {content_str}")
                                
                                # 人类消息
                                elif msg_type == 'human' or 'Human' in str(type(msg)):
                                    if hasattr(msg, 'content'):
                                        print("👤 用户消息:")
                                        print(msg.content)
                                
                                # 其他消息
                                else:
                                    if hasattr(msg, 'content'):
                                        print(f"📄 内容:")
                                        print(msg.content)
                                
                                print("-"*70)
            
            # 提取最终输出
            final_output = all_messages[-1].content if all_messages else "无输出"
            
            if self.verbose:
                print(f"\n\n{'='*70}")
                print("✅ Agent 执行完成")
                print(f"{'='*70}")
                print(f"总步骤数: {step_count}")
                print(f"{'='*70}\n")
            
            return {
                "output": final_output,
                "intermediate_steps": [],  # LangGraph 不直接提供 intermediate_steps
                "success": True
            }
        except Exception as e:
            if self.verbose:
                print(f"\n❌ Agent 执行失败: {e}")
            return {
                "output": f"分析失败: {str(e)}",
                "intermediate_steps": [],
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [tool.name for tool in self.tools]