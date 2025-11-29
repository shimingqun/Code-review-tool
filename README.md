# 代码助手 - CodeSuper

基于 LangGraph 实现的智能代码助手，支持代码生成、优化和审查功能。

## 功能特性

- ✅ **智能路由**：自动分析用户输入，判断需要执行的操作
- ✅ **代码生成**：根据需求自动生成高质量代码
- ✅ **代码优化**：优化现有代码，提升性能和可读性
- ✅ **代码审查**：审查代码质量，给出评分和改进建议
- ✅ **多轮对话**：支持上下文记忆的连续对话
- ✅ **双界面**：提供终端命令行和 Web UI 两种使用方式

## 安装

1. 克隆或下载项目

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
创建 `.env` 文件，添加你的 API 配置：
```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# 可选：自定义模型列表（JSON 格式）
# 如果未配置，将使用默认模型列表
AVAILABLE_MODELS={"DeepSeek V3.1 Terminus": "deepseek-ai/DeepSeek-V3.1-Terminus", "GPT-4": "gpt-4"}
```

**配置说明：**
- `OPENAI_API_KEY`: 必填，你的 API 密钥
- `OPENAI_BASE_URL`: 可选，API 基础 URL，默认为 `https://api.siliconflow.cn/v1`
- `AVAILABLE_MODELS`: 可选，自定义模型列表（JSON 格式），格式为 `{"显示名称": "模型ID", ...}`

**模型列表配置示例：**
```env
AVAILABLE_MODELS={"DeepSeek V3.1 Terminus": "deepseek-ai/DeepSeek-V3.1-Terminus", "DeepSeek V3": "deepseek-ai/DeepSeek-V3", "GPT-4": "gpt-4", "Qwen2.5 72B": "Qwen/Qwen2.5-72B-Instruct"}
```

注意：如果使用 SiliconFlow 或其他兼容 OpenAI API 的服务，需要设置 `OPENAI_BASE_URL`。

## 使用方法

### 终端命令行

#### 交互模式（推荐，支持多轮对话）：
```bash
python cli.py -i
# 或
python cli.py --interactive
```

#### 单次查询：
```bash
python cli.py "生成一个Python函数来计算斐波那契数列"
```

#### 选择模型：
```bash
# 使用指定模型
python cli.py -m "DeepSeek V3.1 Terminus" "你的问题"
python cli.py -m "GPT-4" "你的问题"

# 查看所有可用模型
python cli.py --list-models
```

#### 交互模式命令：
- 输入问题即可开始对话
- 输入 `exit` 或 `quit` 退出
- 输入 `clear` 清除对话历史
- 输入 `model <模型名>` 切换模型（如：`model DeepSeek V3.1 Terminus`）
- 输入 `models` 查看所有可用模型

### Web UI 界面

启动 Web 界面：
```bash
streamlit run ui.py
```

然后在浏览器中打开显示的地址（通常是 http://localhost:8501）

**模型选择**：在界面右上角的下拉框中选择不同的模型。切换模型时会自动清除对话历史。

## 工作流程

根据流程图，代码助手的工作流程如下：

1. **分析输入**：判断用户意图（chat/generate/optimize/review/unknown）
2. **错误处理**：处理无法理解的问题
3. **聊天对话**：回答一般性问题
4. **代码生成**：生成新代码 → 自动优化
5. **代码优化**：优化现有代码
6. **代码审查**：审查代码质量（90分以上通过）
7. **输出结果**：返回最终结果

## 使用示例

### 代码生成
```
您: 生成一个Python函数来读取CSV文件并计算平均值
助手: [生成代码并自动优化]
```

### 代码优化
```
您: 优化这段代码：[粘贴代码]
助手: [优化后的代码]
```

### 代码审查
```
您: 审查这段代码：[粘贴代码]
助手: [审查分数和建议]
```

### 多轮对话
```
您: 生成一个计算器类
助手: [生成代码]

您: 添加日志功能
助手: [在之前代码基础上添加日志功能]
```

## 项目结构

```
CodeSuper/
├── code_assistant.py  # 核心代码助手实现（LangGraph）
├── cli.py             # 终端命令行接口
├── ui.py              # Web UI 界面（Streamlit）
├── requirements.txt   # 依赖包列表
└── README.md          # 项目说明
```

## 支持的模型

代码助手支持多种模型，包括：
- **DeepSeek 系列**：DeepSeek V3.1 Terminus、DeepSeek V3、DeepSeek Chat
- **GPT 系列**：GPT-4、GPT-4 Turbo、GPT-3.5 Turbo
- **Qwen 系列**：Qwen2.5 72B/32B/14B
- **Llama 系列**：Llama 3.1 70B/8B

可以通过 `python cli.py --list-models` 查看完整的模型列表。

## 技术栈

- **LangGraph**：构建工作流图
- **LangChain**：LLM 集成和提示管理
- **OpenAI 兼容 API**：支持多种大语言模型（通过 SiliconFlow 等平台）
- **Streamlit**：Web UI 框架

## 注意事项

1. 需要有效的 OpenAI API 密钥
2. API 调用会产生费用，请注意使用量
3. 代码生成和优化结果仅供参考，请自行测试和验证

## 许可证

本项目仅供学习和研究使用。

