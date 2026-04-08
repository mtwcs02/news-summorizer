import streamlit as st
import google.generativeai as genai

st.title("🔍 내 API 키 전용 모델 탐지기")

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    
    st.write("✅ API 키 연결 성공! 구글 창고에서 사용 가능한 모델을 찾고 있습니다...")
    
    # 내 키로 쓸 수 있는 모델 리스트 싹 다 가져오기
    models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            models.append(m.name)
    
    st.success("🎉 찾았습니다! 아래 리스트에 나오는 이름이 진짜입니다.")
    for name in models:
        st.info(name)
        
except Exception as e:
    st.error(f"🚨 에러 발생: {e}")
