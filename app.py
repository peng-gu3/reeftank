from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)
DATA_FILE = 'stock_data.json'

# 데이터 불러오기
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# 데이터 저장하기
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/load', methods=['GET'])
def api_load():
    return jsonify(load_data())

@app.route('/api/save', methods=['POST'])
def api_save():
    data = request.json
    save_data(data)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    print("프로그램이 실행되었습니다. 웹브라우저를 켜고 http://127.0.0.1:5000 으로 접속하세요.")
    app.run(debug=True)
