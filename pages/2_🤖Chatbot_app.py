# Set up the query for generating responses
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from openai import AzureOpenAI
#from dotenv import load_dotenv
#import os
import sys
import streamlit as st

try:
    search_credential = AzureKeyCredential(st.secrets["AZURE_SEARCH_API_KEY"])

    openai_client = AzureOpenAI(
        api_version="2024-12-01-preview",
        api_key=st.secrets["AZURE_OPENAI_API_KEY"],
        azure_endpoint=st.secrets["AZURE_OPENAI_ENDPOINT"],
        #azure_deployment=st.secrets["AZURE_DEPLOYMENT_MODEL"]
    )
    
    search_client = SearchClient(
        endpoint=st.secrets["AZURE_SEARCH_ENDPOINT"],
        index_name="mvp-sample-index",
        credential=search_credential    
    )
except ClientAuthenticationError as e:
    print("API KEY를 확인해주세요.")
    sys.exit(1)
except HttpResponseError as e:
    print("엔드포인트를 확인해주세요.")
    sys.exit(1)
except Exception as e:
    print("알 수 없는 오류가 발생했습니다.")
    print(e)
    sys.exit(1)

st.set_page_config(page_title="개발 과제 챗봇", layout="centered")

st.title("KT DS 개발 과제 챗봇")
st.write("개발과제 수용률, 분석 등 관련 관련 질문을 해주세요.")

# This prompt provides instructions to the model
GROUNDED_PROMPT="""
You are a friendly assistant who provides comments on similar development projects, development requirements, and development methodologies based on the monthly development task list.
Please answer the questions concisely and kindly, using only the sources provided below.
Please use only the facts listed in the sources below to answer.
If the information below is insufficient, please say "I don't know."
Please do not submit answers that do not use the sources below.
- When calculating the assignment acceptance rate, please refer to the calculation formula and example below and output the results.
  . Calculation should be based on the month entered by the user.
  . Calculation formula
    - 개발 : (User-entered month) Number of assignments in which the value of the current_month_status field is "개발"
    - 중기 : (User-entered month) Number of assignments in which the value of the current_month_status field is "중기"
    - 이월 : (User-entered month) Number of assignments in which the value of the current_month_status field is "이월"
    - (개발+중기)/(개발+중기+이월) = 수용률 결과값(%)
  . example
    - (사용자입력 월) 개발 과제 수용률
      - 개발 : 10건
      - 중기 : 5건
      - 이월 : 10건
      - 수용률 : 60%
- For inquiries regarding analysis, development task analysis, monthly task analysis, task acceptance rate, acceptance rate, etc., please refer to the page below for accurate analysis data.
'개발 과제 분석 페이지로 이동하려면 <a href="./Data_Analysis" target="_blank">여기 클릭</a> 하세요.'
Query: {query}
Sources:\n{sources}
"""

# 대화 내역 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 이전 대화 출력
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

# 사용자 입력 처리
if prompt := st.chat_input("질문 입력:"):
    # 사용자 메시지 표시 및 저장
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 규칙 기반 응답 생성
    if "분석" in prompt:
        response = '개발 과제 분석 페이지로 이동하려면 <a href="./Data_Analysis" target="_blank">여기 클릭</a> 하세요.'
    # elif "설정" in prompt:
    #     response = '설정 페이지는 <a href="./Settings" target="_blank">여기 클릭</a>에서 확인 가능합니다.'
    else:
        response = openai_client.embeddings.create(
            input=prompt,
            model=st.secrets["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]
        )

        #Search results are created by the search client.
        #Search results are composed of the top 5 results and the fields selected from the search index.
        vector_query = VectorizedQuery(
            vector=response.data[0].embedding,
            k_nearest_neighbors=5,
            #fields="titleVector,requirementsVector",
            fields="titleVector",
            kind="vector",
            exhaustive=True
        )

        results = search_client.search(
            search_text=prompt,  # keyword part
            select=["project_month", "project_id", "project_title", "requirements", "current_month_status", "effort_hours"],
            query_type="semantic",
            semantic_configuration_name="my-semantic-config",
            #top=5,
            include_total_count=True,
            vector_queries=[vector_query]
        )

        search_result_list = list(results)
        sources_formatted = "\n".join([f'{document["project_month"]}:{document["project_id"]}:{document["project_title"]}:{document["requirements"]}:{document["current_month_status"]}:{document["effort_hours"]}' for document in search_result_list])

        # Here is the response from the chat model.
        messages = [
            {"role":"user",
            "content": GROUNDED_PROMPT.format(query=prompt, sources=sources_formatted)}
        ]

        response = openai_client.chat.completions.create(
            model=st.secrets["AZURE_DEPLOYMENT_MODEL"],
            messages=messages
        )

        response = response.choices[0].message.content

    # 챗봇 답변 표시 및 저장
    with st.chat_message("assistant"):
        st.markdown(response, unsafe_allow_html=True)
    st.session_state.messages.append({"role": "assistant", "content": response})