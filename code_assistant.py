"""
代码助手 - 基于LangGraph实现
根据流程图实现代码生成、优化和审查功能
"""
from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
import json
import os
from dotenv import load_dotenv

load_dotenv()

# 默认模型列表（如果 .env 中未配置则使用此列表）
DEFAULT_MODELS = {
    "DeepSeek V3.1 Terminus": "deepseek-ai/DeepSeek-V3.1-Terminus",
    "DeepSeek V3": "deepseek-ai/DeepSeek-V3",
}


def load_models_from_env():
    """从环境变量加载模型列表"""
    models_json = os.getenv("AVAILABLE_MODELS")
    
    if models_json:
        try:
            # 从 JSON 字符串解析模型列表
            models = json.loads(models_json)
            if isinstance(models, dict):
                return models
            else:
                print("警告: AVAILABLE_MODELS 格式不正确，使用默认模型列表")
                return DEFAULT_MODELS
        except json.JSONDecodeError as e:
            print(f"警告: 解析 AVAILABLE_MODELS 失败: {e}，使用默认模型列表")
            return DEFAULT_MODELS
    else:
        # 如果未配置，使用默认模型列表
        return DEFAULT_MODELS


# 加载模型列表
AVAILABLE_MODELS = load_models_from_env()

# 定义状态结构
class AssistantState(TypedDict):
    messages: Annotated[list, "对话历史消息"]
    question: str  # 当前问题
    action: str  # 当前动作类型
    code: str  # 生成的代码
    review_result: str  # 审查结果
    review_score: float  # 审查分数
    error: str  # 错误信息
    output: str  # 最终输出
    optimize_count: int  # 优化次数计数器
    review_count: int  # 审查次数计数器


class CodeAssistant:
    def __init__(self, model_name: str = "deepseek-ai/DeepSeek-V3.1-Terminus", temperature: float = 0.7, 
                 base_url: str = None, api_key: str = None):
        """初始化代码助手
        
        Args:
            model_name: 模型名称
            temperature: 温度参数
            base_url: API基础URL，默认为 https://api.siliconflow.cn/v1
            api_key: API密钥，默认从环境变量 OPENAI_API_KEY 读取
        """
        # 设置默认 base_url
        if base_url is None:
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
        
        # 设置 API key
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        
        self.llm = ChatOpenAI(
            model=model_name, 
            temperature=temperature,
            base_url=base_url,
            api_key=api_key
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """构建LangGraph状态图"""
        workflow = StateGraph(AssistantState)
        
        # 添加节点
        workflow.add_node("analyze_input", self._analyze_input)
        workflow.add_node("error_handling", self._error_handling)
        workflow.add_node("chat", self._chat)
        workflow.add_node("code_generate", self._code_generate)
        workflow.add_node("code_optimize", self._code_optimize)
        workflow.add_node("code_review", self._code_review)
        workflow.add_node("output", self._output)
        
        # 设置入口点
        workflow.set_entry_point("analyze_input")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "analyze_input",
            self._route_after_analyze,
            {
                "unknown": "error_handling",
                "chat": "chat",
                "generate": "code_generate",
                "optimize": "code_optimize",
                "review": "code_review",
            }
        )
        
        # 错误处理 -> 输出（避免循环）
        workflow.add_edge("error_handling", "output")
        
        # 聊天 -> 输出（避免循环）
        workflow.add_edge("chat", "output")
        
        # 代码生成 -> 代码优化
        workflow.add_edge("code_generate", "code_optimize")
        
        # 代码优化条件边
        workflow.add_conditional_edges(
            "code_optimize",
            self._route_after_optimize,
            {
                "failed": "code_review",
                "success": "output",  # 成功直接输出，避免循环
            }
        )
        
        # 代码审查条件边
        workflow.add_conditional_edges(
            "code_review",
            self._route_after_review,
            {
                "failed": "code_optimize",
                "passed": "output",
                "retry": "output",  # retry也直接输出，避免循环
            }
        )
        
        # 输出 -> 结束
        workflow.add_edge("output", END)
        
        # 编译图，增加递归限制
        return workflow.compile(checkpointer=None, interrupt_before=None, interrupt_after=None)
    
    def _analyze_input(self, state: AssistantState) -> AssistantState:
        """分析输入，判断需要执行的动作"""
        question = state.get("question", "")
        messages = state.get("messages", [])
        
        # 构建分析提示
        analyze_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能代码助手。分析用户的问题，判断应该执行什么操作。

可选操作：
- "chat": 普通对话，不需要生成代码
- "generate": 需要生成新代码
- "optimize": 需要优化现有代码
- "review": 需要审查代码
- "unknown": 无法理解的问题

只返回操作名称，不要其他内容。"""),
            ("human", "问题：{question}\n\n历史对话：{history}")
        ])
        
        # 格式化历史对话
        history_str = ""
        if messages:
            history_str = "\n".join([
                f"{'用户' if isinstance(msg, HumanMessage) else '助手'}: {msg.content}"
                for msg in messages[-5:]  # 只取最近5条
            ])
        
        chain = analyze_prompt | self.llm
        response = chain.invoke({
            "question": question,
            "history": history_str
        })
        
        action = response.content.strip().lower()
        
        # 验证操作类型
        valid_actions = ["chat", "generate", "optimize", "review", "unknown"]
        if action not in valid_actions:
            action = "unknown"
        
        state["action"] = action
        return state
    
    def _error_handling(self, state: AssistantState) -> AssistantState:
        """错误处理节点"""
        question = state.get("question", "")
        error = state.get("error", "无法理解您的问题")
        
        error_response = f"抱歉，{error}。请重新描述您的需求。"
        
        # 更新消息历史
        messages = state.get("messages", [])
        messages.append(HumanMessage(content=question))
        messages.append(AIMessage(content=error_response))
        state["messages"] = messages
        
        state["error"] = ""
        return state
    
    def _chat(self, state: AssistantState) -> AssistantState:
        """聊天节点"""
        question = state.get("question", "")
        messages = state.get("messages", [])
        
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的代码助手，能够回答编程相关的问题。"),
            ("human", "{question}")
        ])
        
        chain = chat_prompt | self.llm
        response = chain.invoke({"question": question})
        
        # 更新消息历史
        messages.append(HumanMessage(content=question))
        messages.append(AIMessage(content=response.content))
        state["messages"] = messages
        state["output"] = response.content
        
        return state
    
    def process_stream(self, question: str, messages: list = None):
        """流式处理用户问题 - 支持实时输出和Markdown预览"""
        if messages is None:
            messages = []
        
        # 先分析输入类型
        analyze_state = {
            "messages": messages,
            "question": question,
            "action": "",
        }
        self._analyze_input(analyze_state)
        action = analyze_state.get("action", "chat")
        
        # 根据动作类型选择不同的流式处理
        if action == "chat":
            yield from self._chat_stream(question, messages)
        elif action == "generate":
            yield from self._code_generate_stream(question, messages)
        elif action == "optimize":
            yield from self._code_optimize_stream(question, messages)
        elif action == "review":
            yield from self._code_review_stream(question, messages)
        else:
            # unknown 或 error
            error_msg = "抱歉，无法理解您的问题。请重新描述您的需求。"
            yield error_msg
    
    def _chat_stream(self, question: str, messages: list = None):
        """聊天节点 - 流式版本"""
        if messages is None:
            messages = []
        
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的代码助手，能够回答编程相关的问题。"),
            ("human", "{question}")
        ])
        
        chain = chat_prompt | self.llm
        full_response = ""
        
        # 流式调用
        for chunk in chain.stream({"question": question}):
            # LangChain 流式返回的是 AIMessageChunk 对象
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content
                full_response += content
                yield content
            elif isinstance(chunk, dict) and 'content' in chunk:
                content = chunk['content']
                if content:
                    full_response += content
                    yield content
        
        # 更新消息历史
        messages.append(HumanMessage(content=question))
        messages.append(AIMessage(content=full_response))
    
    def _code_generate_stream(self, question: str, messages: list = None):
        """代码生成节点 - 流式版本"""
        if messages is None:
            messages = []
        
        generate_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的代码生成助手。根据用户需求生成高质量、可运行的代码。

要求：
1. 代码要完整、可运行
2. 添加必要的注释
3. 遵循最佳实践
4. 如果用户没有指定语言，默认使用Python"""),
            ("human", "需求：{question}\n\n请生成代码：")
        ])
        
        chain = generate_prompt | self.llm
        full_response = ""
        
        # 流式调用
        for chunk in chain.stream({"question": question}):
            # LangChain 流式返回的是 AIMessageChunk 对象
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content
                full_response += content
                yield content
            elif isinstance(chunk, dict) and 'content' in chunk:
                content = chunk['content']
                if content:
                    full_response += content
                    yield content
        
        # 更新消息历史
        messages.append(HumanMessage(content=question))
        messages.append(AIMessage(content=full_response))
    
    def _code_optimize_stream(self, question: str, messages: list = None):
        """代码优化节点 - 流式版本"""
        if messages is None:
            messages = []
        
        # 从问题中提取代码（简单实现，实际可以更复杂）
        optimize_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个代码优化专家。优化给定的代码，使其更高效、更易读、更符合最佳实践。

优化方向：
1. 性能优化
2. 代码可读性
3. 错误处理
4. 代码结构
5. 最佳实践"""),
            ("human", "原始需求：{question}\n\n请优化这段代码：")
        ])
        
        chain = optimize_prompt | self.llm
        full_response = ""
        
        # 流式调用
        for chunk in chain.stream({"question": question}):
            # LangChain 流式返回的是 AIMessageChunk 对象
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content
                full_response += content
                yield content
            elif isinstance(chunk, dict) and 'content' in chunk:
                content = chunk['content']
                if content:
                    full_response += content
                    yield content
        
        # 更新消息历史
        messages.append(HumanMessage(content=question))
        messages.append(AIMessage(content=full_response))
    
    def _code_review_stream(self, question: str, messages: list = None):
        """代码审查节点 - 流式版本"""
        if messages is None:
            messages = []
        
        review_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个代码审查专家。审查代码的质量，给出评分（0-100）和改进建议。

审查维度：
1. 代码正确性（30分）
2. 代码质量（30分）
3. 性能（20分）
4. 可维护性（20分）"""),
            ("human", "需求：{question}\n\n请审查这段代码：")
        ])
        
        chain = review_prompt | self.llm
        full_response = ""
        
        # 流式调用
        for chunk in chain.stream({"question": question}):
            # LangChain 流式返回的是 AIMessageChunk 对象
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content
                full_response += content
                yield content
            elif isinstance(chunk, dict) and 'content' in chunk:
                content = chunk['content']
                if content:
                    full_response += content
                    yield content
        
        # 更新消息历史
        messages.append(HumanMessage(content=question))
        messages.append(AIMessage(content=full_response))
    
    def _code_generate(self, state: AssistantState) -> AssistantState:
        """代码生成节点"""
        question = state.get("question", "")
        messages = state.get("messages", [])
        
        generate_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的代码生成助手。根据用户需求生成高质量、可运行的代码。

要求：
1. 代码要完整、可运行
2. 添加必要的注释
3. 遵循最佳实践
4. 如果用户没有指定语言，默认使用Python"""),
            ("human", "需求：{question}\n\n请生成代码：")
        ])
        
        chain = generate_prompt | self.llm
        response = chain.invoke({"question": question})
        
        code = response.content
        
        # 提取代码块（如果有）
        if "```" in code:
            parts = code.split("```")
            if len(parts) >= 3:
                code = parts[1].strip()
                if code.startswith("python") or code.startswith("py"):
                    code = code[6:].strip()
                elif code.startswith("javascript") or code.startswith("js"):
                    code = code[10:].strip()
        
        state["code"] = code
        state["output"] = response.content
        
        # 更新消息历史
        messages.append(HumanMessage(content=question))
        messages.append(AIMessage(content=response.content))
        state["messages"] = messages
        
        return state
    
    def _code_optimize(self, state: AssistantState) -> AssistantState:
        """代码优化节点"""
        code = state.get("code", "")
        question = state.get("question", "")
        messages = state.get("messages", [])
        optimize_count = state.get("optimize_count", 0) + 1
        state["optimize_count"] = optimize_count
        
        # 防止无限循环：如果优化次数超过3次，直接输出
        if optimize_count > 3:
            state["output"] = f"代码已优化{optimize_count}次，当前代码：\n```\n{code}\n```"
            return state
        
        if not code:
            state["action"] = "failed"
            return state
        
        optimize_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个代码优化专家。优化给定的代码，使其更高效、更易读、更符合最佳实践。

优化方向：
1. 性能优化
2. 代码可读性
3. 错误处理
4. 代码结构
5. 最佳实践"""),
            ("human", "原始需求：{question}\n\n代码：\n```\n{code}\n```\n\n请优化这段代码：")
        ])
        
        chain = optimize_prompt | self.llm
        response = chain.invoke({"question": question, "code": code})
        
        optimized_code = response.content
        
        # 提取优化后的代码
        if "```" in optimized_code:
            parts = optimized_code.split("```")
            if len(parts) >= 3:
                optimized_code = parts[1].strip()
                if optimized_code.startswith("python") or optimized_code.startswith("py"):
                    optimized_code = optimized_code[6:].strip()
                elif optimized_code.startswith("javascript") or optimized_code.startswith("js"):
                    optimized_code = optimized_code[10:].strip()
        
        state["code"] = optimized_code
        state["output"] = response.content
        
        # 更新消息历史（如果是首次优化）
        if not any("优化" in str(msg.content) for msg in messages):
            messages.append(AIMessage(content=f"代码已优化：\n{response.content}"))
            state["messages"] = messages
        
        return state
    
    def _code_review(self, state: AssistantState) -> AssistantState:
        """代码审查节点"""
        code = state.get("code", "")
        question = state.get("question", "")
        messages = state.get("messages", [])
        review_count = state.get("review_count", 0) + 1
        state["review_count"] = review_count
        
        # 防止无限循环：如果审查次数超过3次，直接输出
        if review_count > 3:
            state["output"] = f"代码已审查{review_count}次，当前代码：\n```\n{code}\n```"
            state["review_score"] = 85.0  # 设置一个默认分数
            return state
        
        if not code:
            state["action"] = "failed"
            return state
        
        review_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个代码审查专家。审查代码的质量，给出评分（0-100）和改进建议。

审查维度：
1. 代码正确性（30分）
2. 代码质量（30分）
3. 性能（20分）
4. 可维护性（20分）

请以JSON格式返回：
{{
    "score": 85,
    "feedback": "代码整体良好，但可以改进...",
    "suggestions": ["建议1", "建议2"]
}}"""),
            ("human", "需求：{question}\n\n代码：\n```\n{code}\n```\n\n请审查这段代码：")
        ])
        
        chain = review_prompt | self.llm
        response = chain.invoke({"question": question, "code": code})
        
        review_text = response.content
        
        # 尝试解析JSON
        try:
            if "```json" in review_text:
                json_part = review_text.split("```json")[1].split("```")[0].strip()
            elif "```" in review_text:
                json_part = review_text.split("```")[1].split("```")[0].strip()
            else:
                json_part = review_text
            
            review_data = json.loads(json_part)
            score = float(review_data.get("score", 0))
            feedback = review_data.get("feedback", review_text)
        except:
            # 如果解析失败，尝试从文本中提取分数
            score = 0
            feedback = review_text
            # 尝试提取数字
            import re
            numbers = re.findall(r'\d+', review_text)
            if numbers:
                score = float(numbers[0])
                if score > 100:
                    score = score / 10
        
        state["review_score"] = score
        state["review_result"] = feedback
        state["output"] = f"审查分数：{score}/100\n\n{feedback}"
        
        # 更新消息历史
        messages.append(AIMessage(content=f"代码审查结果：\n{state['output']}"))
        state["messages"] = messages
        
        return state
    
    def _output(self, state: AssistantState) -> AssistantState:
        """输出节点"""
        output = state.get("output", "")
        code = state.get("code", "")
        review_result = state.get("review_result", "")
        
        # 构建最终输出
        final_output = output
        if code and "代码" in output.lower():
            final_output = f"{output}\n\n生成的代码：\n```\n{code}\n```"
        
        state["output"] = final_output
        return state
    
    def _route_after_analyze(self, state: AssistantState) -> str:
        """分析后的路由"""
        return state.get("action", "unknown")
    
    def _route_after_optimize(self, state: AssistantState) -> str:
        """优化后的路由"""
        # 如果已经达到最大优化次数，直接输出
        if state.get("optimize_count", 0) > 3:
            return "success"
        
        # 简单判断：如果代码为空或有问题，返回failed
        code = state.get("code", "")
        if not code or len(code) < 10:
            return "failed"
        return "success"
    
    def _route_after_review(self, state: AssistantState) -> str:
        """审查后的路由 - 根据流程图：90% ok -> output, failed -> code_optimize, 其他 -> output"""
        # 如果已经达到最大审查次数，直接输出
        if state.get("review_count", 0) > 3:
            return "passed"
        
        score = state.get("review_score", 0)
        
        # 90% ok -> output
        if score >= 90:
            return "passed"
        # failed -> code_optimize (但限制循环次数)
        elif score < 60:
            # 如果优化次数已经很多，直接输出
            if state.get("optimize_count", 0) > 2:
                return "passed"
            return "failed"
        # 其他情况 -> output (避免循环)
        else:
            return "retry"
    
    def process(self, question: str, messages: list = None) -> dict:
        """处理用户问题 - 支持多轮对话"""
        if messages is None:
            messages = []
        
        # 添加当前用户问题到消息历史（用于多轮对话上下文）
        current_messages = messages.copy()
        
        initial_state = {
            "messages": current_messages,
            "question": question,
            "action": "",
            "code": "",
            "review_result": "",
            "review_score": 0.0,
            "error": "",
            "output": "",
            "optimize_count": 0,
            "review_count": 0,
        }
        
        # 运行图，增加递归限制配置
        config = {"recursion_limit": 50}  # 增加递归限制到50
        final_state = self.graph.invoke(initial_state, config=config)
        
        # 确保消息历史被正确更新（如果节点没有更新，则手动添加）
        if not final_state.get("messages") or len(final_state["messages"]) == len(current_messages):
            # 如果消息历史没有更新，说明可能是直接输出，需要添加消息
            final_messages = final_state.get("messages", current_messages)
            if final_messages == current_messages:
                # 添加用户消息和助手回复
                final_messages.append(HumanMessage(content=question))
                if final_state.get("output"):
                    final_messages.append(AIMessage(content=final_state["output"]))
            final_state["messages"] = final_messages
        
        return final_state

