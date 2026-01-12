import os
import uuid
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "global_support_2026")

# 1. MongoDB 설정 (IP Access 0.0.0.0/0 확인됨)
mongo_uri = os.getenv("MONGO_URI")
mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
db = mongo_client['chatbot_db']
chats_collection = db['conversations']
knowledge_collection = db['knowledge']

# 2. OpenAI 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 3. 시스템 프롬프트 (주인님 연락처 포함)
SYSTEM_PROMPT = """당신은 지식 창고 기반 전문 상담원입니다. 
지식에 없는 내용은 "정보가 없으니 JINPD(010-2391-0082)에게 문의하세요"라고 답변하세요."""

def get_relevant_knowledge(query):
    try:
        keywords = query.split()
        relevant_docs = list(knowledge_collection.find({
            "$or": [{"content": {"$regex": kw, "$options": "i"}} for kw in keywords]
        }).limit(3))
        return "\n".join([doc['content'] for doc in relevant_docs]) if relevant_docs else ""
    except: return ""

@app.route('/')
def home():
    if 'user_id' not in session: session['user_id'] = str(uuid.uuid4())[:8]
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_id = session.get('user_id', 'Guest')
    user_message = request.json.get("message")
    context = get_relevant_knowledge(user_message)
    chats_collection.insert_one({"user_id": user_id, "role": "user", "message": user_message, "timestamp": datetime.now()})
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "system", "content": SYSTEM_PROMPT.format(context=context)}, {"role": "user", "content": user_message}]
        )
        bot_reply = response.choices[0].message.content
        chats_collection.insert_one({"user_id": user_id, "role": "bot", "message": bot_reply, "timestamp": datetime.now()})
        return jsonify({"reply": bot_reply})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500

@app.route('/admin')
def admin(): return render_template('admin.html')

@app.route('/api/admin/history')
def get_all_history():
    history = list(chats_collection.find({}, {"_id": 0}).sort("timestamp", 1))
    return jsonify(history)

# [수정] 어떤 JSON 구조든 지식으로 변환하는 초강력 업로드 API
@app.route('/api/admin/upload_json', methods=['POST'])
def upload_json():
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({"status": "fail", "message": "파일이 없습니다."}), 400

    success_count = 0
    for file in files:
        if file and file.filename.endswith('.json'):
            try:
                raw_data = file.read().decode('utf-8')
                data = json.loads(raw_data)
                
                # 데이터가 리스트([])인 경우와 사전({})인 경우 모두 처리
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    # 'content', 'text', 'info', 'body' 등 가능한 키를 모두 확인
                    content = item.get('content') or item.get('text') or item.get('info') or item.get('body')
                    
                    # 만약 키 이름을 모른다면 첫 번째 문자열 값을 가져옴
                    if not content:
                        for key in item:
                            if isinstance(item[key], str):
                                content = item[key]
                                break
                    
                    if content:
                        knowledge_collection.insert_one({
                            "content": str(content).strip(),
                            "source": file.filename,
                            "timestamp": datetime.now()
                        })
                        success_count += 1
                print(f"✅ 파일 처리 완료: {file.filename}")
            except Exception as e:
                print(f"❌ 파일 에러 ({file.filename}): {e}")
                continue

    return jsonify({"status": "success", "message": f"{success_count}개의 지식 조각을 학습했습니다!"})

@app.route('/api/admin/knowledge_files')
def get_knowledge_files():
    files = knowledge_collection.distinct("source")
    return jsonify(files)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)