# 代码质量提升智能体

一个基于 LangGraph 的智能代码助手，支持代码审查、代码优化、代码生成和智能聊天功能。提供命令行和 Web UI 两种使用方式。

## 功能特性

- 📝 **代码生成**：根据需求自动生成高质量代码
- 🔍 **代码审查**：智能审查代码质量，提供评分和改进建议
- ⚡ **代码优化**：根据审查意见自动优化代码
- 💬 **智能聊天**：支持多轮对话，回答编程相关问题
- 🌐 **Web UI**：现代化的网页界面，支持流式输出和实时 Markdown 预览
- 🔄 **多轮对话**：基于 LangGraph 的记忆机制，保持对话上下文

## 安装

### 1. 克隆或下载项目

```bash
cd CodeAssistant2
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API 密钥

设置环境变量（可选，代码中已有默认值）：

```bash
# Windows
set OPENAI_API_KEY=your_api_key_here

# Linux/Mac
export OPENAI_API_KEY=your_api_key_here
```

或者在代码中直接修改 `CodeAsistant.py` 和 `app.py` 中的 API 密钥。

## 启动方式

### 方式一：Web UI 模式（推荐）

使用 `--gui` 参数启动网页版界面：

```bash
python CodeAsistant.py --gui
```

启动后会自动：
- 启动 Flask 服务器（默认端口 5000）
- 自动打开浏览器访问 `http://127.0.0.1:5000`
- 显示访问地址和关闭提示

**停止服务**：在终端中按 `Ctrl+C`

### 方式二：直接启动 Flask 服务器

```bash
python app.py
```

然后手动在浏览器中访问 `http://localhost:5000`

### 方式三：命令行模式

不使用 `--gui` 参数，直接运行：

```bash
python CodeAsistant.py
```

进入交互式命令行对话模式，输入 `quit` 或 `exit` 退出。

## 使用说明

### Web UI 使用

1. 启动 Web UI 后，在浏览器中输入您的需求
2. 支持的功能：
   - **代码审查**：输入 "审查代码: [代码内容]" 或 "review code: [代码]"
   - **代码优化**：输入 "优化代码: [代码内容]" 或 "optimize code: [代码]"
   - **代码生成**：输入 "生成代码: [需求描述]" 或 "generate code: [需求]"
   - **智能聊天**：直接输入问题或对话内容

3. 界面特性：
   - 实时流式输出，逐字显示响应
   - 自动 Markdown 渲染，代码高亮显示
   - 评审信息展示：评分、通过状态、评审意见
   - 多轮对话记忆，保持上下文

### 命令行使用

在命令行模式下，直接输入您的需求，例如：

```
用户: 生成一个计算斐波那契数列的函数
智能体: [生成的代码和审查结果]

用户: 优化这段代码
智能体: [优化后的代码]
```

## 项目结构

```
CodeAssistant2/
├── CodeAsistant.py      # 核心智能体代码
├── app.py               # Flask Web 服务器
├── requirements.txt     # Python 依赖
├── templates/
│   └── index.html      # Web UI 前端页面
└── README.md           # 项目说明文档
```

## 技术栈

- **后端框架**：Flask
- **AI 框架**：LangGraph, LangChain
- **前端技术**：HTML5, CSS3, JavaScript, Marked.js
- **AI 服务**：SiliconFlow API (DeepSeek-V3.1-Terminus)

## 注意事项

1. 首次运行可能需要下载依赖，请确保网络连接正常
2. Web UI 默认运行在 `http://localhost:5000`，确保端口未被占用
3. API 密钥请妥善保管，不要提交到公共代码仓库
4. 日志文件保存在 `code_agent_debug.log` 中，可用于问题排查

## 常见问题

**Q: 启动 Web UI 后浏览器没有自动打开？**  
A: 可以手动在浏览器中访问 `http://localhost:5000`

**Q: 端口 5000 被占用怎么办？**  
A: 修改 `app.py` 最后一行的端口号，例如改为 `port=8080`

**Q: 如何查看详细的运行日志？**  
A: 查看项目目录下的 `code_agent_debug.log` 文件

## 许可证

本项目仅供学习和研究使用。

