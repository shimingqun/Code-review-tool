"""
终端命令接口
"""
import argparse
import sys
import os
import subprocess
from code_assistant import CodeAssistant
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv


def print_help():
    """打印详细的帮助信息"""
    help_text = """
代码助手 - 命令行工具使用说明
================================

基本用法：
  python cli.py [选项] [问题]

参数说明：
  question              要询问的问题（可选，如果不提供则进入交互模式）
  
选项：
  -i, --interactive      进入交互模式，支持多轮对话
  -c, --continuous      启用连续思考模式（使用 code_assistant_continous.py）
  -m, --model MODEL     选择使用的模型（默认: DeepSeek V3.1 Terminus）
  --list-models         列出所有可用的模型
  --web                 启动网页版界面（Streamlit）
  -h, --help           显示此帮助信息

使用示例：
  # 交互模式
  python cli.py -i
  
  # 单次查询
  python cli.py "生成一个Python函数计算斐波那契数列"
  
  # 连续思考模式（交互）
  python cli.py -c -i
  
  # 连续思考模式（单次查询）
  python cli.py -c "优化这段代码"
  
  # 指定模型
  python cli.py -m "DeepSeek V3.1 Terminus" -i
  
  # 列出所有可用模型
  python cli.py --list-models
  
  # 启动网页版
  python cli.py --web

交互模式命令：
  exit, quit, 退出      退出程序
  clear, 清除           清除对话历史
  model <模型名>        切换模型（仅普通模式）
  models                查看所有可用模型（仅普通模式）
  help                  显示此帮助信息

功能说明：
  - 普通对话：直接提问，获得回答
  - 代码生成：描述需求，自动生成代码
  - 代码优化：提供代码，自动优化
  - 代码审查：提供代码，获得审查评分和建议

模式说明：
  - 普通模式：支持流式输出，支持模型切换
  - 连续思考模式：支持记忆功能，详细日志，自动代码审查和优化流程
"""
    print(help_text)


def main():
    """主函数"""
    from code_assistant import AVAILABLE_MODELS
    
    parser = argparse.ArgumentParser(
        description="代码助手 - 终端版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python cli.py -i                    # 交互模式
  python cli.py "你的问题"            # 单次查询
  python cli.py -c -i                 # 连续思考模式
  python cli.py --list-models         # 列出所有模型
  python cli.py --web                 # 启动网页版

交互模式命令：
  exit, quit, 退出      退出程序
  clear, 清除           清除对话历史
  model <模型名>        切换模型（仅普通模式）
  models                查看所有可用模型（仅普通模式）
  help                  显示详细帮助信息

更多信息请使用: python cli.py --help
        """
    )
    parser.add_argument("question", nargs="?", help="要询问的问题（可选，不提供则进入交互模式）")
    parser.add_argument("-i", "--interactive", action="store_true", help="进入交互模式，支持多轮对话")
    parser.add_argument("-m", "--model", type=str, help="选择使用的模型", 
                       choices=list(AVAILABLE_MODELS.keys()) + list(AVAILABLE_MODELS.values()),
                       default="DeepSeek V3.1 Terminus")
    parser.add_argument("--list-models", action="store_true", help="列出所有可用的模型")
    parser.add_argument("-c", "--continuous", action="store_true", help="启用连续思考模式（使用 code_assistant_continous.py，支持记忆功能）")
    parser.add_argument("--web", action="store_true", help="启动网页版界面（Streamlit）")
    
    args = parser.parse_args()
    
    # 启动网页版
    if args.web:
        print("正在启动网页版界面...")
        print("浏览器将自动打开，如果没有自动打开，请访问显示的URL")
        print("按 Ctrl+C 停止服务器\n")
        try:
            # 获取 ui.py 的路径
            ui_path = os.path.join(os.path.dirname(__file__), "ui.py")
            if not os.path.exists(ui_path):
                print(f"错误：找不到 ui.py 文件 ({ui_path})")
                sys.exit(1)
            
            # 启动 Streamlit
            subprocess.run([sys.executable, "-m", "streamlit", "run", ui_path])
        except KeyboardInterrupt:
            print("\n\n网页服务器已停止")
            sys.exit(0)
        except FileNotFoundError:
            print("错误：未找到 streamlit，请先安装：pip install streamlit")
            sys.exit(1)
        except Exception as e:
            print(f"错误：启动网页版失败: {e}")
            sys.exit(1)
    
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
        print("输入 'help' 查看详细帮助信息")
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
                
                # 显示帮助命令
                if question.lower() in ["help", "帮助", "--help", "-h"]:
                    print_help()
                    print()
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

