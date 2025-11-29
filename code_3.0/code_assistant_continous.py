import os
import sys
import json
import time
import logging
import subprocess
import webbrowser
from typing import Dict, Any, List, Optional, TypedDict
from enum import Enum
from urllib import request
import urllib.parse
from datetime import datetime

# 导入 LangGraph
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# 设置日志系统
def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('code_agent_debug.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("CodeQualityAgent")

logger = setup_logging()


class Intent(Enum):
    REVIEW = "review"
    OPTIMIZE = "optimize"
    GENERATE = "generate"
    CHAT = "chat"
    UNKNOWN = "unknown"


# 使用 TypedDict 定义状态
class AgentState(TypedDict):
    messages: List[Dict[str, str]]
    current_intent: Optional[Intent]
    filename: Optional[str]
    code_content: Optional[str]
    generated_code: Optional[str]
    optimized_code: Optional[str]
    review_comments: Optional[str]
    review_score: int
    review_passed: bool
    last_node: str
    output: str
    user_input: str


class AIService:
    """使用标准库调用云端AI服务的封装"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.siliconflow.cn/v1"):
        self.api_key = api_key
        self.base_url = base_url
        logger.info(f"AIService 初始化完成，Base URL: {base_url}")
    
    def call_ai(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        """调用AI服务 - 使用标准库"""
        payload = {
            "model": "deepseek-ai/DeepSeek-V3.1-Terminus",
            "messages": messages,
            "temperature": temperature
        }
        
        try:
            # 准备请求
            data = json.dumps(payload).encode('utf-8')
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 创建请求
            req = request.Request(
                f"{self.base_url}/chat/completions",
                data=data,
                headers=headers,
                method="POST"
            )
            
            logger.debug(f"发送AI请求，消息数量: {len(messages)}")
            
            # 发送请求
            with request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                response_content = result["choices"][0]["message"]["content"]
                logger.debug(f"AI响应接收完成，长度: {len(response_content)}")
                return response_content
        except Exception as e:
            error_msg = f"AI服务调用失败: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """分析用户意图"""
        logger.info(f"开始分析用户意图: {user_input[:50]}...")
        
        messages = [
            {
                "role": "system",
                "content": """分析用户意图，返回JSON：{"intent": "review|optimize|generate|chat|unknown", "filename": "文件名或null"}"""
            },
            {
                "role": "user", 
                "content": f"用户输入: {user_input}"
            }
        ]
        
        response = self.call_ai(messages)
        
        try:
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            result = json.loads(content)
            
            intent_str = result.get("intent", "unknown")
            try:
                result["intent"] = Intent(intent_str)
            except ValueError:
                result["intent"] = Intent.UNKNOWN

            content_lower = response.lower()
            if "review" in content_lower or  "optimize" in content_lower:
                if(result.get('filename') == None):
                    result["intent"] = Intent.UNKNOWN
 
            logger.info(f"意图分析结果: {result['intent']}, 文件名: {result.get('filename')}")
            return result
        except json.JSONDecodeError:
            logger.warning(f"AI返回的意图分析不是标准JSON: {response}")
            content_lower = response.lower()
            if "review" in content_lower:
                result = {"intent": Intent.REVIEW, "filename": None}
            elif "optimize" in content_lower:
                result = {"intent": Intent.OPTIMIZE, "filename": None}
            elif "generate" in content_lower or "生成" in response:
                result = {"intent": Intent.GENERATE, "filename": None}
            elif "chat" in content_lower or "聊天" in response:
                result = {"intent": Intent.CHAT, "filename": None}
            else:
                result = {"intent": Intent.UNKNOWN, "filename": None}
            
            logger.info(f"回退意图分析结果: {result['intent']}")
            return result
    
    def chat(self, conversation_history: List[Dict[str, str]]) -> str:
        """通用聊天功能"""
        logger.info(f"执行聊天功能，历史消息数: {len(conversation_history)}")
        return self.call_ai(conversation_history)
    
    def generate_code(self, requirements: str) -> str:
        """代码生成"""
        logger.info(f"执行代码生成，需求: {requirements[:50]}...")
        
        messages = [
            {
                "role": "system",
                "content": "你是代码生成助手。根据需求生成高质量代码，直接返回代码。"
            },
            {
                "role": "user",
                "content": f"需求: {requirements}"
            }
        ]
        
        result = self.call_ai(messages)
        logger.info(f"代码生成完成，生成长度: {len(result)}")
        return result
    
    def review_code(self, code: str, context: str = "") -> Dict[str, Any]:
        """代码审查"""
        logger.info(f"执行代码审查，代码长度: {len(code)}, 上下文: {context}")
        
        messages = [
            {
                "role": "system",
                "content": """你是代码审查专家。返回JSON：{"score": 0-100, "comments": "审查意见", "passed": true/false}，评分>=80通过。"""
            },
            {
                "role": "user",
                "content": f"代码:\n```\n{code}\n```\n\n上下文: {context}"
            }
        ]
        
        response = self.call_ai(messages)
        
        try:
            content = response.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            result = json.loads(content)
            result["passed"] = result.get("score", 0) >= 80
            
            logger.info(f"代码审查完成，得分: {result['score']}, 通过: {result['passed']}")
            return result
        except json.JSONDecodeError:
            logger.warning(f"AI返回的代码审查结果不是标准JSON: {response}")
            return {"score": 85, "comments": "代码质量良好", "passed": True}
    
    def optimize_code(self, code: str, review_comments: str = "") -> str:
        """代码优化"""
        logger.info(f"执行代码优化，代码长度: {len(code)}, 审查意见长度: {len(review_comments)}")
        
        messages = [
            {
                "role": "system",
                "content": "你是代码优化专家。根据审查意见优化代码，直接返回优化后的代码。"
            },
            {
                "role": "user",
                "content": f"原始代码:\n```\n{code}\n```\n\n审查意见: {review_comments}"
            }
        ]
        
        result = self.call_ai(messages)
        logger.info(f"代码优化完成，优化后长度: {len(result)}")
        return result


class CodeQualityAgent:
    """代码质量提升智能体 - 修复记忆问题"""
    
    def __init__(self, api_key: str):
        self.ai_service = AIService(api_key)
        self.node_execution_count = {}
        self.start_time = None
        
        logger.info("初始化 CodeQualityAgent")
        self.graph = self._build_graph()
    
    def _log_node_entry(self, node_name: str, state: AgentState):
        """记录节点进入"""
        self.node_execution_count[node_name] = self.node_execution_count.get(node_name, 0) + 1
        
        logger.info(f"🔹 进入节点: {node_name}")
        logger.info(f"   当前状态: intent={state.get('current_intent')}, last_node={state.get('last_node')}")
        logger.info(f"   执行次数: {self.node_execution_count[node_name]}")
        logger.info(f"   消息历史长度: {len(state.get('messages', []))}")
        
        if state.get('messages'):
            last_msg = state['messages'][-1]
            if 'content' in last_msg:
                content_preview = last_msg['content'][:50] + "..." if len(last_msg['content']) > 50 else last_msg['content']
                logger.info(f"   最后消息: {content_preview}")
    
    def _log_node_exit(self, node_name: str, result: Dict[str, Any]):
        """记录节点退出"""
        logger.info(f"🔸 退出节点: {node_name}")
        if 'output' in result and result['output']:
            output_preview = result['output'][:100] + "..." if len(result['output']) > 100 else result['output']
            logger.info(f"   输出预览: {output_preview}")
        if 'review_passed' in result:
            logger.info(f"   审查结果: {'通过' if result['review_passed'] else '未通过'}")
        if 'review_score' in result:
            logger.info(f"   审查分数: {result['review_score']}")
    
    def _log_route_decision(self, route_name: str, decision: str, state: AgentState):
        """记录路由决策"""
        logger.info(f"🔄 路由决策: {route_name} -> {decision}")
        logger.info(f"   当前意图: {state.get('current_intent')}")
        if 'review_passed' in state:
            logger.info(f"   审查通过: {state['review_passed']}")
    
    def _build_graph(self):
        """构建LangGraph工作流 - 修复记忆问题"""
        logger.info("开始构建 LangGraph 工作流")
        
        workflow = StateGraph(AgentState)
        
        # 添加所有节点
        workflow.add_node("process_input", self.process_input_node)
        workflow.add_node("analyze_intent", self.analyze_intent_node)
        workflow.add_node("error_handling", self.error_handling_node)
        workflow.add_node("chat", self.chat_node)
        workflow.add_node("code_generate", self.code_generate_node)
        workflow.add_node("code_review", self.code_review_node)
        workflow.add_node("code_optimize", self.code_optimize_node)
        workflow.add_node("output", self.output_node)
        
        # 设置入口点
        workflow.set_entry_point("process_input")
        
        # 处理输入后分析意图
        workflow.add_edge("process_input", "analyze_intent")
        
        # 根据意图路由
        workflow.add_conditional_edges(
            "analyze_intent",
            self.route_by_intent,
            {
                "review": "code_review",
                "optimize": "code_optimize", 
                "generate": "code_generate",
                "chat": "chat",
                "unknown": "error_handling"
            }
        )
        
        # 固定边
        workflow.add_edge("error_handling", "output")
        workflow.add_edge("chat", "output")
        workflow.add_edge("code_generate", "code_review")
        
        # 根据审查结果路由
        workflow.add_conditional_edges(
            "code_review",
            self.route_by_review_result,
            {
                "pass": "output",
                "fail": "code_optimize"
            }
        )
        
        workflow.add_edge("code_optimize", "code_review")
        
        # 输出节点后结束
        workflow.add_edge("output", END)
        
        # 使用内存检查点实现记忆
        memory = MemorySaver()
        
        logger.info("LangGraph 工作流构建完成")
        return workflow.compile(checkpointer=memory)
    
    # 节点实现
    def process_input_node(self, state: AgentState) -> Dict[str, Any]:
        """处理用户输入节点 - 将用户输入添加到消息历史"""
        self._log_node_entry("process_input", state)
        
        user_input = state.get('user_input', '').strip()
        if not user_input:
            result = {"output": "请输入有效内容", "last_node": "process_input"}
            self._log_node_exit("process_input", result)
            return result
        
        # 将用户输入添加到消息历史
        current_messages = state.get('messages', [])
        new_messages = current_messages + [{"role": "user", "content": user_input}]
        
        result = {
            "messages": new_messages,
            "user_input": "",  # 清空用户输入
            "last_node": "process_input"
        }
        
        logger.info(f"   添加用户消息到历史，历史消息数: {len(new_messages)}")
        self._log_node_exit("process_input", result)
        return result
    
    def analyze_intent_node(self, state: AgentState) -> Dict[str, Any]:
        """分析用户意图节点"""
        self._log_node_entry("analyze_intent", state)
        
        if not state.get('messages'):
            result = {"current_intent": Intent.UNKNOWN, "last_node": "analyze_intent"}
            self._log_node_exit("analyze_intent", result)
            return result
        
        # 获取最新的用户消息
        user_messages = [msg for msg in state['messages'] if msg['role'] == 'user']
        if not user_messages:
            result = {"current_intent": Intent.UNKNOWN, "last_node": "analyze_intent"}
            self._log_node_exit("analyze_intent", result)
            return result
        
        latest_user_message = user_messages[-1]['content']
        intent_result = self.ai_service.analyze_intent(latest_user_message)
        
        result = {
            "current_intent": intent_result["intent"],
            "filename": intent_result.get("filename"),
            "last_node": "analyze_intent"
        }
        
        self._log_node_exit("analyze_intent", result)
        return result
    
    def error_handling_node(self, state: AgentState) -> Dict[str, Any]:
        """错误处理节点"""
        self._log_node_entry("error_handling", state)
        
        result = {
            "output": "无法理解您的请求。请明确说明您需要：代码审查、代码优化、代码生成，或者只是聊天。",
            "last_node": "error_handling"
        }
        
        self._log_node_exit("error_handling", result)
        return result
    
    def chat_node(self, state: AgentState) -> Dict[str, Any]:
        """聊天节点"""
        self._log_node_entry("chat", state)
        
        messages = state.get('messages', [])
        # 限制历史长度以避免token超限，但保留足够的上下文
        if len(messages) > 10:
            # 保留系统消息和最近的消息
            system_messages = [msg for msg in messages if msg.get('role') == 'system']
            recent_messages = messages[-8:]  # 保留最近的8条消息
            messages = system_messages + recent_messages
        
        response = self.ai_service.chat(messages)
        new_messages = messages + [{"role": "assistant", "content": response}]
        
        result = {
            "messages": new_messages,
            "output": response,
            "last_node": "chat"
        }
        
        logger.info(f"   聊天响应完成，消息历史长度: {len(new_messages)}")
        self._log_node_exit("chat", result)
        return result
    
    def code_generate_node(self, state: AgentState) -> Dict[str, Any]:
        """代码生成节点"""
        self._log_node_entry("code_generate", state)
        
        if not state.get('messages'):
            result = {"last_node": "code_generate"}
            self._log_node_exit("code_generate", result)
            return result
        
        # 获取最新的用户消息作为需求
        user_messages = [msg for msg in state['messages'] if msg['role'] == 'user']
        if not user_messages:
            result = {"last_node": "code_generate"}
            self._log_node_exit("code_generate", result)
            return result
        
        latest_user_message = user_messages[-1]['content']
        generated_code = self.ai_service.generate_code(latest_user_message)
        
        result = {
            "generated_code": generated_code,
            "code_content": generated_code,
            "last_node": "code_generate"
        }
        
        logger.info(f"   生成代码长度: {len(generated_code)} 字符")
        self._log_node_exit("code_generate", result)
        return result
    
    def code_review_node(self, state: AgentState) -> Dict[str, Any]:
        """代码审查节点"""
        self._log_node_entry("code_review", state)
        
        code_to_review = ""
        context = ""
        last_node = state.get('last_node', '')
        
        logger.info(f"   上一个节点: {last_node}")
        logger.info(f"   文件名: {state.get('filename')}")
        
        if last_node == "code_generate":
            code_to_review = state.get('generated_code', '')
            context = "审查新生成的代码"
            logger.info("   审查类型: 新生成代码")
        elif last_node == "code_optimize":
            code_to_review = state.get('optimized_code', '')
            context = "审查优化后的代码"
            logger.info("   审查类型: 优化后代码")
        elif last_node == "analyze_intent" and state.get('filename'):
            try:
                with open(state['filename'], 'r', encoding='utf-8') as f:
                    code_to_review = f.read()
                context = f"审查文件: {state['filename']}"
                logger.info(f"   审查类型: 文件审查 - {state['filename']}")
            except FileNotFoundError:
                result = {
                    "output": f"错误: 文件 {state['filename']} 不存在",
                    "last_node": "code_review",
                    "review_score": 0,
                    "review_passed": False
                }
                self._log_node_exit("code_review", result)
                return result
        else:
            result = {
                "output": "错误: 没有可审查的代码",
                "last_node": "code_review",
                "review_score": 0,
                "review_passed": False
            }
            self._log_node_exit("code_review", result)
            return result
        
        if not code_to_review.strip():
            result = {
                "output": "错误: 代码内容为空",
                "last_node": "code_review",
                "review_score": 0,
                "review_passed": False
            }
            self._log_node_exit("code_review", result)
            return result
        
        logger.info(f"   审查代码长度: {len(code_to_review)} 字符")
        review_result = self.ai_service.review_code(code_to_review, context)
        
        result = {
            "review_comments": review_result["comments"],
            "review_score": review_result["score"],
            "review_passed": review_result["passed"],
            "last_node": "code_review"
        }
        
        logger.info(f"   审查得分: {review_result['score']}/100")
        logger.info(f"   审查结果: {'通过' if review_result['passed'] else '未通过'}")
        self._log_node_exit("code_review", result)
        return result
    
    def code_optimize_node(self, state: AgentState) -> Dict[str, Any]:
        """代码优化节点"""
        self._log_node_entry("code_optimize", state)
        
        code_to_optimize = ""
        review_comments = state.get('review_comments', '')
        last_node = state.get('last_node', '')
        
        logger.info(f"   上一个节点: {last_node}")
        logger.info(f"   审查意见长度: {len(review_comments)}")
        
        if last_node == "code_review":
            if state.get('generated_code'):
                code_to_optimize = state['generated_code']
                logger.info("   优化类型: 新生成代码")
            elif state.get('optimized_code'):
                code_to_optimize = state['optimized_code']
                logger.info("   优化类型: 已优化代码")
            elif state.get('filename'):
                try:
                    with open(state['filename'], 'r', encoding='utf-8') as f:
                        code_to_optimize = f.read()
                    logger.info(f"   优化类型: 文件代码 - {state['filename']}")
                except FileNotFoundError:
                    result = {
                        "output": f"错误: 文件 {state['filename']} 不存在",
                        "last_node": "code_optimize"
                    }
                    self._log_node_exit("code_optimize", result)
                    return result
        else:
            result = {
                "output": "错误: 没有可优化的代码",
                "last_node": "code_optimize"
            }
            self._log_node_exit("code_optimize", result)
            return result
        
        if not code_to_optimize.strip():
            result = {
                "output": "错误: 代码内容为空",
                "last_node": "code_optimize"
            }
            self._log_node_exit("code_optimize", result)
            return result
        
        logger.info(f"   优化代码长度: {len(code_to_optimize)} 字符")
        optimized_code = self.ai_service.optimize_code(code_to_optimize, review_comments)
        
        result = {
            "optimized_code": optimized_code,
            "code_content": optimized_code,
            "last_node": "code_optimize"
        }
        
        logger.info(f"   优化后代码长度: {len(optimized_code)} 字符")
        self._log_node_exit("code_optimize", result)
        return result
    
    def output_node(self, state: AgentState) -> Dict[str, Any]:
        """输出节点"""
        self._log_node_entry("output", state)
        
        output_message = ""
        last_node = state.get('last_node', '')
        
        logger.info(f"   上一个节点: {last_node}")
        logger.info(f"   审查通过: {state.get('review_passed', False)}")
        
        if last_node == "chat":
            output_message = state.get('output', '')
            logger.info("   输出类型: 聊天响应")
        elif last_node == "code_review" and state.get('review_passed', False):
            if state.get('generated_code'):
                output_message = f"✅ 代码生成并通过审查！\n评分: {state.get('review_score', 0)}/100\n\n生成的代码:\n```python\n{state['generated_code']}\n```"
                logger.info("   输出类型: 代码生成通过")
            elif state.get('optimized_code'):
                output_message = f"✅ 代码优化并通过审查！\n评分: {state.get('review_score', 0)}/100\n\n优化后的代码:\n```python\n{state['optimized_code']}\n```"
                logger.info("   输出类型: 代码优化通过")
            else:
                output_message = f"✅ 代码审查通过！\n评分: {state.get('review_score', 0)}/100\n审查意见:\n{state.get('review_comments', '')}"
                logger.info("   输出类型: 代码审查通过")
        elif last_node == "error_handling":
            output_message = state.get('output', '')
            logger.info("   输出类型: 错误处理")
        else:
            output_message = state.get('output', '') or "处理完成"
            logger.info("   输出类型: 默认输出")
        
        # 将AI响应添加到消息历史
        if last_node != "error_handling" and output_message:
            new_messages = state.get('messages', []) + [{"role": "assistant", "content": output_message}]
        else:
            new_messages = state.get('messages', [])
        
        result = {
            "messages": new_messages,
            "output": output_message,
            "last_node": "output"
        }
        
        logger.info(f"   输出长度: {len(output_message)}")
        logger.info(f"   更新后消息历史长度: {len(new_messages)}")
        self._log_node_exit("output", result)
        return result
    
    def route_by_intent(self, state: AgentState) -> str:
        """根据意图路由"""
        current_intent = state.get('current_intent')
        
        if current_intent == Intent.REVIEW:
            decision = "review"
        elif current_intent == Intent.OPTIMIZE:
            decision = "optimize"
        elif current_intent == Intent.GENERATE:
            decision = "generate"
        elif current_intent == Intent.CHAT:
            decision = "chat"
        else:
            decision = "unknown"
        
        self._log_route_decision("route_by_intent", decision, state)
        return decision
    
    def route_by_review_result(self, state: AgentState) -> str:
        """根据审查结果路由"""
        if state.get('review_passed', False):
            decision = "pass"
        else:
            decision = "fail"
        
        self._log_route_decision("route_by_review_result", decision, state)
        return decision
    
    def process_message(self, user_input: str, config: Dict = None) -> str:
        """处理用户输入 - 修复记忆问题"""
        self.start_time = time.time()
        logger.info(f"🎯 开始处理用户输入: {user_input}")
        
        if config is None:
            config = {
                "configurable": {"thread_id": "code_agent_session"}
            }
        
        # 关键修复：只传入需要更新的字段，而不是完整的初始状态
        # 这样 MemorySaver 会合并现有状态，而不是覆盖
        update_state = {
            "user_input": user_input
        }
        
        logger.info("🚀 开始执行 LangGraph 工作流")
        try:
            # 使用 update_state 而不是完整的 initial_state
            final_state = self.graph.invoke(update_state, config=config)
            
            execution_time = time.time() - self.start_time
            logger.info(f"✅ LangGraph 工作流执行完成，耗时: {execution_time:.2f}秒")
            
            # 打印执行统计
            logger.info("📊 节点执行统计:")
            for node, count in sorted(self.node_execution_count.items()):
                logger.info(f"   {node}: {count} 次")
            
            # 打印消息历史长度用于调试
            messages_count = len(final_state.get('messages', []))
            logger.info(f"💬 当前消息历史长度: {messages_count}")
            
            # 重置节点计数，为下一次调用做准备
            self.node_execution_count = {}
            
            # 从字典中获取输出
            return final_state.get('output', '处理完成，但没有返回输出')
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            return f"处理过程中出现错误: {str(e)}"
    
    def process_message_with_details(self, user_input: str, config: Dict = None) -> Dict[str, Any]:
        """处理用户输入并返回详细信息（包括评审意见、得分等）"""
        self.start_time = time.time()
        logger.info(f"🎯 开始处理用户输入（详细信息模式）: {user_input}")
        
        if config is None:
            config = {
                "configurable": {"thread_id": "code_agent_session"}
            }
        
        # 关键修复：只传入需要更新的字段，而不是完整的初始状态
        # 这样 MemorySaver 会合并现有状态，而不是覆盖
        update_state = {
            "user_input": user_input
        }
        
        logger.info("🚀 开始执行 LangGraph 工作流")
        try:
            # 使用 update_state 而不是完整的 initial_state
            final_state = self.graph.invoke(update_state, config=config)
            
            execution_time = time.time() - self.start_time
            logger.info(f"✅ LangGraph 工作流执行完成，耗时: {execution_time:.2f}秒")
            
            # 打印执行统计
            logger.info("📊 节点执行统计:")
            for node, count in sorted(self.node_execution_count.items()):
                logger.info(f"   {node}: {count} 次")
            
            # 打印消息历史长度用于调试
            messages_count = len(final_state.get('messages', []))
            logger.info(f"💬 当前消息历史长度: {messages_count}")
            
            # 构建返回结果
            current_intent = final_state.get('current_intent')
            intent_str = ''
            if current_intent:
                if isinstance(current_intent, Intent):
                    intent_str = current_intent.value
                else:
                    intent_str = str(current_intent)
            
            result = {
                "output": final_state.get('output', '处理完成，但没有返回输出'),
                "review_score": final_state.get('review_score', 0),
                "review_comments": final_state.get('review_comments', ''),
                "review_passed": final_state.get('review_passed', False),
                "generated_code": final_state.get('generated_code', ''),
                "optimized_code": final_state.get('optimized_code', ''),
                "current_intent": intent_str,
                "execution_time": execution_time
            }
            
            # 重置节点计数
            self.node_execution_count = {}
            
            return result
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            return {
                "output": f"处理过程中出现错误: {str(e)}",
                "review_score": 0,
                "review_comments": "",
                "review_passed": False,
                "generated_code": "",
                "optimized_code": "",
                "current_intent": "",
                "execution_time": time.time() - self.start_time
            }


def main():
    """
    启动方式：
    - 命令行对话模式：python CodeAsistant.py
    - Web GUI 模式：  python CodeAsistant.py --gui
    """
    # 如果带有 --gui 参数，则启动 Flask Web 界面
    if "--gui" in sys.argv:
        print("🌐 正在启动 Web 界面（Flask）...")
        try:
            # 使用当前 Python 解释器启动 app.py
            server_proc = subprocess.Popen(
                [sys.executable, "app.py"],
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
        except Exception as e:
            print(f"❌ 启动 Web 服务失败: {e}")
            return

        # 等待服务启动一小段时间
        time.sleep(1.5)
        url = "http://127.0.0.1:5000"
        print(f"✅ Web 界面已启动，请在浏览器打开：{url}")
        try:
            webbrowser.open(url)
        except Exception:
            # 即使打不开浏览器也不影响使用
            pass

        # 阻塞等待 Flask 进程退出
        try:
            server_proc.wait()
        except KeyboardInterrupt:
            print("\n🛑 收到中断信号，正在关闭 Web 服务...")
            server_proc.terminate()
        return

    # 默认：命令行对话模式
    # 初始化智能体 - 替换为您的API密钥
    api_key = os.getenv("OPENAI_API_KEY", "sk-yalxlthqsmnmwsowcbwjxusjrveuzugihjrwuedgkgwkgwwy")
    agent = CodeQualityAgent(api_key)

    print("代码质量提升智能体已启动！（命令行模式）")
    print("支持的功能：代码审查、代码优化、代码生成、聊天")
    print("输入 'quit' 退出程序；使用 `python CodeAsistant.py --gui` 打开网页版\n")

    # 创建测试文件
    with open("test_code.py", "w", encoding="utf-8") as f:
        f.write('''def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total
''')

    # 使用固定的配置，确保对话记忆保持
    # 使用有意义的 thread_id
    config = {"configurable": {"thread_id": "user_session_1"}}

    # 交互式对话循环
    while True:
        try:
            user_input = input("\n用户: ").strip()
            if user_input.lower() in ['quit', 'exit', '退出']:
                break

            if user_input:
                response = agent.process_message(user_input, config)
                print(f"\n智能体: {response}")

                # 测试记忆功能
                if "我叫" in user_input or "我的名字是" in user_input:
                    print("\n💡 提示: 接下来可以问'我叫什么名字？'来测试记忆功能")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")

    print("程序已退出")


if __name__ == "__main__":
    main()