# 1. 安装必要包 (请在终端中运行)
# pip install -U langgraph langchain-openai

import os
from typing import Annotated, TypedDict
from input_output import InputHandler
input_handler = InputHandler()
os.environ["OPENAI_API_KEY"] = "sk-yalxlthqsmnmwsowcbwjxusjrveuzugihjrwuedgkgwkgwwy"
os.environ["OPENAI_API_BASE"] = "https://api.siliconflow.cn/v1"

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 2. 定义状态机：用来记录对话历史
class State(TypedDict):
    # 关键：使用 add_messages 这个 reducer，新的消息会自动追加到列表，而不是覆盖
    messages: Annotated[list, add_messages]

# 3. 初始化图
graph_builder = StateGraph(State)

# 4. 定义节点函数：智能分类与响应节点
def chatbot_node(state: State):
    # 4.1 初始化大模型
    llm = ChatOpenAI(model="deepseek-ai/DeepSeek-V3.1-Terminus")
    
    # 4.2 构建分类提示词
    classification_prompt = """
你是一个智能代码助手。请先对用户输入进行分类，然后提供专业回答。

分类标准：
🔍 代码检查 - 代码审查、bug检测、规范检查等
⚡ 代码优化 - 性能优化、效率提升、重构等  
💻 代码生成 - 生成代码、编写函数、实现功能等
💬 chat聊天 - 技术咨询、问题解答、普通对话等

请按以下格式响应：
【分类】代码检查/代码优化/代码生成/chat聊天
【回答】您的专业回答...

用户输入：{user_input}
""".format(user_input=state["messages"][-1].content)
    
    # 4.3 调用模型进行分类和响应
    response = llm.invoke([{"role": "user", "content": classification_prompt}])

    # 4.4 美化输出
    print("🤖 助手:", end=" ")
    if "【分类】" in response.content and "【回答】" in response.content:
        # 解析分类和回答
        lines = response.content.split('\n')
        for line in lines:
            if line.startswith("【分类】"):
                category = line.replace("【分类】", "").strip()
                category_icons = {
                    "代码检查": "🔍",
                    "代码优化": "⚡", 
                    "代码生成": "💻",
                    "chat聊天": "💬"
                }
                icon = category_icons.get(category, "📝")
                print(f"\n{icon} 检测到: {category}")
            elif line.startswith("【回答】"):
                answer = line.replace("【回答】", "").strip()
                print(f"💬 回答: {answer}")
            elif line and not line.startswith("【"):
                print(f"      {line}")
    else:
        # 如果模型没有按格式响应，直接输出
        print(response.content)

    # 4.5 返回响应
    return {"messages": [response]}

# 5. 添加节点
graph_builder.add_node("chatbot", chatbot_node)

# 6. 定义执行流程：起点 -> 聊天节点 -> 终点
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

# 7. 编译图
graph = graph_builder.compile()

# 8. 运行聊天机器人
print("🚀 欢迎使用智能代码助手！")
print("📋 功能分类：")
print("  🔍 代码检查 - 代码审查、bug检测、规范检查")
print("  ⚡ 代码优化 - 性能优化、效率提升、代码重构")  
print("  💻 代码生成 - 生成代码、编写函数、实现功能")
print("  💬 chat聊天 - 技术咨询、问题解答、普通对话")
print("-" * 60)
print("输入 'quit', 'exit' 或 'q' 来退出。")

input_handler = InputHandler()

while True:
    user_input = input_handler.get_input_from_terminal("please input: ")
    
    if user_input.lower() in ["quit", "exit", "q"]:
        print("再见！👋")
        break
    
    if not user_input:
        print("🤖 助手: 请输入您的问题...")
        continue
    
    # 初始化输入状态，将用户输入作为 HumanMessage 放入消息列表
    input_state = {"messages": [{"role": "user", "content": user_input}]}
    
    try:
        # 调用编译好的图
        result = graph.invoke(input_state)
        
    except Exception as e:
        print(f"❌ 发生错误: {e}")