class InputHandler:

    
    def __init__(self):
        self._user_input = ""  # 存储用户输入
    
    def set_user_input(self, input_text: str) -> None:
        """
        Set user input
        
        Args:
            input_text (str):
        """
        self._user_input = input_text.strip()
    
    def get_user_input(self) -> str:
        """
        Get user input
        
        Returns:
            str: 
        """
        return self._user_input
    
    def get_input_from_terminal(self, prompt="👤 用户: ") -> str:
        """
        get input from terminal
        
        Returns:
            str: 
        """
        user_input = input(prompt).strip()
        self.set_user_input(user_input)  # 自动设置到内部变量
        return user_input