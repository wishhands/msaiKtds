import streamlit as st

st.set_page_config(page_title="KT DS 개발 과제 대시보드", layout="wide")

st.title("KT DS 개발 과제 수용률 및 분석 대시보드")
st.write("이 곳에서 개발 과제 수용률, 과제 분석 등 현황을 확인할 수 있습니다.")

# 플로팅 버튼 HTML/CSS/JS
#chatbot_url = "http://localhost:8501/Chatbot_app"
chatbot_url = "./Chatbot_app"

floating_button = f"""
    <style>
    .chatbot-button {{
        position: fixed;
        bottom: 30px;
        right: 30px;
        background-color: #ff4b4b;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 50px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.2);
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 8px;
        text-decoration: none;
    }}
    .chatbot-button:hover {{
        background-color: #ff1e1e;
    }}
    .chatbot-button img {{
        height: 24px;
        width: 24px;
    }}
    </style>
    <a href="{chatbot_url}" target="_blank" class="chatbot-button">
        <img src="https://img.icons8.com/?size=100&id=9Otd0Js4uSYi&format=png&color=000000" alt="chatbot icon" />
    </a>
"""

st.markdown(floating_button, unsafe_allow_html=True)

st.info("좌측 사이드바를 통해 원하는 페이지로 이동하세요.")