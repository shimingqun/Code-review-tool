"""
简洁的UI界面 - 使用Streamlit
"""
import streamlit as st
from code_assistant import CodeAssistant
from langchain_core.messages import HumanMessage, AIMessage
import os
from dotenv import load_dotenv

load_dotenv()


def init_session_state():
    """初始化会话状态"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "deepseek-ai/DeepSeek-V3.1-Terminus"
    if "assistant" not in st.session_state:
        try:
            st.session_state.assistant = CodeAssistant(model_name=st.session_state.selected_model)
        except Exception as e:
            st.error(f"初始化失败: {e}")
            st.stop()


def main():
    """主函数"""
    st.set_page_config(
        page_title="代码助手",
        page_icon=None,  # 无图标
        layout="centered",
        initial_sidebar_state="collapsed"  # 默认收起侧边栏
    )
    
    # 隐藏Streamlit默认的菜单和页脚
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # 检查API密钥
    if not os.getenv("OPENAI_API_KEY"):
        st.error("请设置 OPENAI_API_KEY 环境变量")
        st.info("在项目根目录创建 .env 文件，添加：OPENAI_API_KEY=your_key")
        st.stop()
    
    # 初始化
    init_session_state()
    
    # 标题和模型选择
    col_title, col_model = st.columns([3, 1])
    with col_title:
        st.title("代码助手")
        st.caption("基于LangGraph的智能代码生成、优化和审查工具")
    with col_model:
        # 模型选择
        from code_assistant import AVAILABLE_MODELS
        model_display_names = list(AVAILABLE_MODELS.keys())
        current_model_display = None
        for display_name, model_id in AVAILABLE_MODELS.items():
            if model_id == st.session_state.selected_model:
                current_model_display = display_name
                break
        
        if current_model_display is None:
            current_model_display = model_display_names[0]
            st.session_state.selected_model = AVAILABLE_MODELS[current_model_display]
        
        selected_display = st.selectbox(
            "模型",
            model_display_names,
            index=model_display_names.index(current_model_display),
            key="model_selector"
        )
        
        # 如果模型改变，重新初始化助手
        new_model = AVAILABLE_MODELS[selected_display]
        if new_model != st.session_state.selected_model:
            st.session_state.selected_model = new_model
            try:
                st.session_state.assistant = CodeAssistant(model_name=new_model)
                # 清除对话历史（因为不同模型的上下文可能不兼容）
                st.session_state.messages = []
                st.rerun()
            except Exception as e:
                st.error(f"切换模型失败: {e}")
                st.stop()
    
    # 显示对话历史
    for message in st.session_state.messages:
        with st.chat_message("user" if isinstance(message, HumanMessage) else "assistant"):
            st.markdown(message.content)
    
    # 用户输入
    if prompt := st.chat_input("输入您的问题..."):
        # 添加用户消息
        st.session_state.messages.append(HumanMessage(content=prompt))
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 处理问题 - 流式输出
        with st.chat_message("assistant"):
            try:
                # 使用流式处理
                response_placeholder = st.empty()
                full_response = ""
                
                # 流式获取响应
                for chunk in st.session_state.assistant.process_stream(
                    prompt,
                    st.session_state.messages[:-1]  # 排除刚添加的消息
                ):
                    # 确保 chunk 是字符串类型
                    if chunk:
                        if isinstance(chunk, str):
                            full_response += chunk
                            # 实时更新显示（支持Markdown）
                            response_placeholder.markdown(full_response + "▌")
                        elif isinstance(chunk, dict):
                            # 如果是字典，提取内容
                            content = chunk.get("output", chunk.get("content", ""))
                            if content and isinstance(content, str):
                                full_response += content
                                response_placeholder.markdown(full_response + "▌")
                        else:
                            # 其他类型，转换为字符串
                            chunk_str = str(chunk)
                            full_response += chunk_str
                            response_placeholder.markdown(full_response + "▌")
                
                # 最终显示完整响应
                response_placeholder.markdown(full_response)
                
                # 更新消息历史
                st.session_state.messages.append(AIMessage(content=full_response))
                
            except Exception as e:
                st.error(f"处理出错: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    # 简洁的设置区域 - 使用expander而不是侧边栏
    with st.expander("⚙️ 设置", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("清除对话历史", type="secondary", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        with col2:
            if st.button("显示帮助", type="secondary", use_container_width=True):
                st.info("""
**功能说明：**
- **普通对话**：直接提问，获得回答
- **代码生成**：描述需求，自动生成代码
- **代码优化**：提供代码，自动优化
- **代码审查**：提供代码，获得审查评分和建议
                """)


if __name__ == "__main__":
    main()

