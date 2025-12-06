import streamlit as st
import json

st.set_page_config(page_title="열쇠 수리공", page_icon="🔧")

st.title("🔧 로봇 열쇠 수리 도구")
st.info("아래 칸에 메모장에 있는 '로봇 열쇠(JSON)' 내용을 전부 붙여넣으세요.")

# 1. JSON 입력받기
json_input = st.text_area("여기에 붙여넣기 (Ctrl+V)", height=300)

if json_input:
    try:
        # 2. JSON 청소 및 수리
        # 눈에 안 보이는 엔터나 공백을 제거하고 다시 만듭니다.
        creds = json.loads(json_input)
        
        # 3. Secrets용 TOML 포맷으로 변환
        toml_output = "[gcp_service_account]\n"
        toml_output += 'info = """\n'
        toml_output += json.dumps(creds, indent=2) # 깔끔하게 정리
        toml_output += '\n"""'
        
        st.success("✅ 수리 완료! 아래 코드를 복사해서 Secrets에 덮어씌우세요.")
        st.code(toml_output, language="toml")
        
    except json.JSONDecodeError as e:
        st.error(f"❌ 아직 복사가 잘 안됐어요. 괄호 '{{' 부터 '}}' 까지 빠짐없이 복사했는지 확인하세요.\n에러 내용: {e}")
