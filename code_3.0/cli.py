"""
终端命令接口
"""
import argparse
import sys
import os
from code_assistant import CodeAssistant
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv


def main():
    """主函数"""
    from code_assistant import AVAILABLE_MODELS
    
    parser = argparse.ArgumentParser(description="代码助手 - 终端版本")
    parser.add_argument("question", nargs="?", help="要询问的问题")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式")
    parser.add_argument("-m", "--model", type=str, help="选择模型", 
                       choices=list(AVAILABLE_MODELS.keys()) + list(AVAILABLE_MODELS.values()),
                       default="DeepSeek V3.1 Terminus")
    parser.add_argument("--list-models", action="store_true", help="列出所有可用模型")
    parser.add_argument("-c", "--continuous", action="store_true", help="启用连续思考模式（使用 code_assistant_continous.py）")
    
    args = parser.parse_args()
    
    # 列出所有模型
    if args.list_models:
        print("可用模型列表：")
        print("=" * 60)
        for display_name, model_id in AVAILABLE_MODELS.items():
            print(f"  {display_name:30s} -> {model_id}")
        print("=" * 60)
        sys.exit(0)
    
    # 检查环境变量
    if not os.getenv("OPENAI_API_KEY"):
        print("错误：请设置 OPENAI_API_KEY 环境变量")
        print("可以在 .env 文件中设置，或使用 export OPENAI_API_KEY=your_key")
        sys.exit(1)
    
    # 初始化助手
    if args.continuous:
        # 连续思考模式
        try:
            from code_assistant_continous import CodeQualityAgent
            print("使用连续思考模式 (code_assistant_continous.py)")
            assistant = CodeQualityAgent(os.getenv("OPENAI_API_KEY"))
            model_name = None  # 连续模式不使用模型选择
        except Exception as e:
            print(f"错误：连续思考模式初始化失败: {e}")
            sys.exit(1)
    else:
        # 普通模式
        model_name = args.model
        if model_name in AVAILABLE_MODELS:
            model_name = AVAILABLE_MODELS[model_name]
        print(f"使用模型: {model_name}")
        assistant = CodeAssistant(model_name=model_name)
    
    messages = []
    
    if args.interactive or not args.question:
        # 交互模式 - 支持多轮对话
        print("=" * 60)
        print("代码助手 - 交互模式")
        if args.continuous:
            print("模式: 连续思考")
        else:
            print(f"当前模型: {model_name}")
        print("输入 'exit' 或 'quit' 退出")
        print("输入 'clear' 清除对话历史")
        if not args.continuous:
            print("输入 'model <模型名>' 切换模型")
            print("输入 'models' 查看所有可用模型")
        print("=" * 60)
        print()
        
        while True:
            try:
                question = input("您: ").strip()
                
                if not question:
                    continue
                
                if question.lower() in ["exit", "quit", "退出"]:
                    print("再见！")
                    break
                
                if question.lower() in ["clear", "清除"]:
                    messages = []
                    print("对话历史已清除\n")
                    continue
                
                # 切换模型命令（仅非连续模式）
                if not args.continuous and question.lower().startswith("model "):
                    new_model_name = question[6:].strip()
                    # 检查是否是显示名称
                    if new_model_name in AVAILABLE_MODELS:
                        new_model_name = AVAILABLE_MODELS[new_model_name]
                    elif new_model_name not in AVAILABLE_MODELS.values():
                        print(f"错误：未找到模型 '{new_model_name}'")
                        print("使用 'models' 命令查看所有可用模型\n")
                        continue
                    
                    try:
                        assistant = CodeAssistant(model_name=new_model_name)
                        model_name = new_model_name
                        print(f"已切换到模型: {model_name}\n")
                    except Exception as e:
                        print(f"切换模型失败: {e}\n")
                    continue
                
                # 列出所有模型（仅非连续模式）
                if not args.continuous and question.lower() in ["models", "list-models"]:
                    print("\n可用模型列表：")
                    print("=" * 60)
                    for display_name, model_id in AVAILABLE_MODELS.items():
                        marker = " <- 当前" if model_id == model_name else ""
                        print(f"  {display_name:30s} -> {model_id}{marker}")
                    print("=" * 60)
                    print()
                    continue
                
                print("\n助手: ", end="", flush=True)
                
                # 处理请求
                full_response = ""
                try:
                    if args.continuous:
                        # 连续思考模式 - 非流式输出
                        config = {"configurable": {"thread_id": "cli_session"}}
                        full_response = assistant.process_message(question, config)
                        print(full_response)
                    else:
                        # 普通模式 - 流式输出
                        for chunk in assistant.process_stream(question, messages):
                            if chunk:
                                print(chunk, end="", flush=True)
                                full_response += chunk
                    
                    print()  # 换行
                    
                    # 更新消息历史（仅普通模式，连续模式内部已处理）
                    if not args.continuous:
                        from langchain_core.messages import HumanMessage, AIMessage
                        messages.append(HumanMessage(content=question))
                        messages.append(AIMessage(content=full_response))
                    
                except Exception as e:
                    print(f"\n错误: {e}")
                    import traceback
                    traceback.print_exc()
                
                print("\n" + "-" * 60)
                print()
                
            except KeyboardInterrupt:
                print("\n\n再见！")
                break
            except Exception as e:
                print(f"\n错误: {e}\n")
    else:
        # 单次查询模式
        try:
            print("助手: ", end="", flush=True)
            full_response = ""
            
            if args.continuous:
                # 连续思考模式 - 非流式输出
                config = {"configurable": {"thread_id": "cli_session"}}
                full_response = assistant.process_message(args.question, config)
                print(full_response)
            else:
                # 普通模式 - 流式输出
                for chunk in assistant.process_stream(args.question, messages):
                    if chunk:
                        print(chunk, end="", flush=True)
                        full_response += chunk
            
            print("\n")  # 换行
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    main()

