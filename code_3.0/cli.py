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
    
    # 解析模型参数
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
        print(f"当前模型: {model_name}")
        print("输入 'exit' 或 'quit' 退出")
        print("输入 'clear' 清除对话历史")
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
                
                # 切换模型命令
                if question.lower().startswith("model "):
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
                
                # 列出所有模型
                if question.lower() in ["models", "list-models"]:
                    print("\n可用模型列表：")
                    print("=" * 60)
                    for display_name, model_id in AVAILABLE_MODELS.items():
                        marker = " <- 当前" if model_id == model_name else ""
                        print(f"  {display_name:30s} -> {model_id}{marker}")
                    print("=" * 60)
                    print()
                    continue
                
                print("\n助手: ", end="", flush=True)
                
                # 流式输出
                full_response = ""
                try:
                    for chunk in assistant.process_stream(question, messages):
                        if chunk:
                            print(chunk, end="", flush=True)
                            full_response += chunk
                    
                    print()  # 换行
                    
                    # 更新消息历史
                    from langchain_core.messages import HumanMessage, AIMessage
                    messages.append(HumanMessage(content=question))
                    messages.append(AIMessage(content=full_response))
                    
                except Exception as e:
                    print(f"\n错误: {e}")
                
                print("\n" + "-" * 60)
                print()
                
            except KeyboardInterrupt:
                print("\n\n再见！")
                break
            except Exception as e:
                print(f"\n错误: {e}\n")
    else:
        # 单次查询模式 - 流式输出
        try:
            print("助手: ", end="", flush=True)
            full_response = ""
            for chunk in assistant.process_stream(args.question, messages):
                if chunk:
                    print(chunk, end="", flush=True)
                    full_response += chunk
            print("\n")  # 换行
        except Exception as e:
            print(f"\n错误: {e}")
            sys.exit(1)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    main()

