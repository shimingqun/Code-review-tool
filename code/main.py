from input_output import InputHandler
input_handler = InputHandler()


# use set_user_input 和 get_user_input
input_handler.set_user_input("Hello World")
print(f"get input: {input_handler.get_user_input()}")  # 输出: 获取到的输入: Hello World

user_input = input_handler.get_input_from_terminal("please input: ")