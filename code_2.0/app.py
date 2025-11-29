from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import json
import os
import time
from CodeAsistant import CodeQualityAgent
import logging

app = Flask(__name__)
CORS(app)

# 初始化智能体
api_key = os.getenv("OPENAI_API_KEY", "sk-yalxlthqsmnmwsowcbwjxusjrveuzugihjrwuedgkgwkgwwy")
agent = CodeQualityAgent(api_key)

# 存储对话历史（按thread_id）
conversations = {}

@app.route('/')
def index():
    """返回主页面"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """处理聊天请求，返回完整响应"""
    try:
        data = request.json
        user_input = data.get('message', '')
        thread_id = data.get('thread_id', 'default')
        
        if not user_input:
            return jsonify({"error": "消息不能为空"}), 400
        
        # 获取或创建配置
        config = {"configurable": {"thread_id": thread_id}}
        
        # 处理消息并获取详细信息
        result = agent.process_message_with_details(user_input, config)
        
        # 保存对话历史
        if thread_id not in conversations:
            conversations[thread_id] = []
        conversations[thread_id].append({
            "role": "user",
            "content": user_input
        })
        conversations[thread_id].append({
            "role": "assistant",
            "content": result["output"],
            "review_score": result.get("review_score", 0),
            "review_comments": result.get("review_comments", ""),
            "review_passed": result.get("review_passed", False)
        })
        
        return jsonify({
            "success": True,
            "response": result["output"],
            "review_score": result.get("review_score", 0),
            "review_comments": result.get("review_comments", ""),
            "review_passed": result.get("review_passed", False),
            "generated_code": result.get("generated_code", ""),
            "optimized_code": result.get("optimized_code", ""),
            "current_intent": result.get("current_intent", ""),
            "execution_time": result.get("execution_time", 0)
        })
    except Exception as e:
        logging.error(f"处理聊天请求时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """处理流式聊天请求"""
    try:
        data = request.json
        user_input = data.get('message', '')
        thread_id = data.get('thread_id', 'default')
        
        if not user_input:
            return jsonify({"error": "消息不能为空"}), 400
        
        # 获取或创建配置
        config = {"configurable": {"thread_id": thread_id}}
        
        def generate():
            try:
                # 处理消息（非流式，因为LangGraph的流式处理比较复杂）
                result = agent.process_message_with_details(user_input, config)
                
                # 保存对话历史
                if thread_id not in conversations:
                    conversations[thread_id] = []
                conversations[thread_id].append({
                    "role": "user",
                    "content": user_input
                })
                
                # 流式输出响应内容（按词或短句发送，更自然）
                output = result["output"]
                words = output.split(' ')
                chunk_size = 3  # 每次发送3个词
                
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:i+chunk_size])
                    if i + chunk_size < len(words):
                        chunk += ' '  # 添加空格（最后一个chunk不加）
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                    # 添加小延迟使流式效果更明显
                    time.sleep(0.05)
                
                # 发送元数据
                yield f"data: {json.dumps({'type': 'metadata', 'review_score': result.get('review_score', 0), 'review_comments': result.get('review_comments', ''), 'review_passed': result.get('review_passed', False), 'generated_code': result.get('generated_code', ''), 'optimized_code': result.get('optimized_code', ''), 'current_intent': result.get('current_intent', '')})}\n\n"
                
                # 结束标记
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
                # 保存助手响应
                conversations[thread_id].append({
                    "role": "assistant",
                    "content": output,
                    "review_score": result.get("review_score", 0),
                    "review_comments": result.get("review_comments", ""),
                    "review_passed": result.get("review_passed", False)
                })
                
            except Exception as e:
                logging.error(f"流式处理时出错: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    except Exception as e:
        logging.error(f"处理流式聊天请求时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/history/<thread_id>', methods=['GET'])
def get_history(thread_id):
    """获取对话历史"""
    history = conversations.get(thread_id, [])
    return jsonify({"success": True, "history": history})

@app.route('/api/history/<thread_id>', methods=['DELETE'])
def clear_history(thread_id):
    """清空对话历史"""
    if thread_id in conversations:
        del conversations[thread_id]
    return jsonify({"success": True, "message": "历史已清空"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

