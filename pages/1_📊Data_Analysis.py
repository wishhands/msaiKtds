# Set up the query for generating responses
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from openai import AzureOpenAI
import sys
import streamlit as st
#import matplotlib.pyplot as plt
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
import platform


try:
    search_credential = AzureKeyCredential(st.secrets["AZURE_SEARCH_API_KEY"])

    # openai_client = AzureOpenAI(
    #     api_version="2024-12-01-preview",
    #     api_key=st.secrets["AZURE_OPENAI_API_KEY"],
    #     azure_endpoint=st.secrets["AZURE_OPENAI_ENDPOINT"],
    # )
    
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


def getProjectCount(status,strFilter):
    results = search_client.search(
    search_text=status, 
    search_fields=['current_month_status'], 
    select='project_month,current_month_status,project_title,requirements',
    filter="search.ismatch("+strFilter+")",
    include_total_count=True)

    return results.get_count()


st.title("개발 과제 분석")
st.write("이 페이지에서는 개발 과제 분석 결과를 볼 수 있습니다.")

if platform.system() == 'Linux':
    plt.rcParams['font.family'] ='NanumGothic'
else:
    plt.rcParams['font.family'] ='Malgun Gothic'
plt.rcParams['axes.unicode_minus'] =False

# 예시 데이터
months = ['6월', '7월', '8월']
months_tag = ['6month*', '7month*', '8month*']
group1 = [0,0,0]
group2 = [0,0,0]
group3 = [0,0,0]
line_values = [0,0,0]  # 라인 그래프 데이터


# 현재 날짜 기준
now = datetime.now()
current_year = now.year
current_month_num = now.month

years = [2023, 2024, 2025]
months_all = [f'{m}월' for m in range(1, 13)]

selected_year = st.selectbox('연도 선택', years, index=years.index(current_year))
selected_month_str = st.selectbox('월 선택', months_all, index=current_month_num-1)

if st.button("검색"):
    # 현재 선택 연월 문자열 (예: '8month*')
    month_num = selected_month_str.replace('월', '')

    # M-2월 계산: 숫자형 월 - 2 (1,2월 선택 시 전년도 11,12월 처리 가능하도록 확장 필요)
    target_month_num = int(month_num) - 2
    target_year = selected_year
    if target_month_num <= 0:
        target_month_num += 12
        target_year -= 1

    months[0] = f"'{target_month_num}월'"
    months_tag[0] = f"''{target_month_num}month*''"
    months[1] = f"'{target_month_num+1}월'"
    months_tag[1] = f"''{target_month_num+1}month*''"
    months[2] = f"'{target_month_num+2}월'"
    months_tag[2] = f"''{target_month_num+2}month*''"


    group1[0] = getProjectCount("개발","'"+months_tag[0]+"'")
    group2[0] = getProjectCount("이월","'"+months_tag[0]+"'")
    group3[0] = getProjectCount("보류","'"+months_tag[0]+"'")
    line_values[0] = group1[0]+group2[0]+group3[0]

    group1[1] = getProjectCount("개발","'"+months_tag[1]+"'")
    group2[1] = getProjectCount("이월","'"+months_tag[1]+"'")
    group3[1] = getProjectCount("보류","'"+months_tag[1]+"'")
    line_values[1] = group1[1]+group2[1]+group3[1]

    group1[2] = getProjectCount("개발","'"+months_tag[2]+"'")
    group2[2] = getProjectCount("이월","'"+months_tag[2]+"'")
    group3[2] = getProjectCount("보류","'"+months_tag[2]+"'")
    line_values[2] = group1[2]+group2[2]+group3[2]


    data = pd.DataFrame({
        '월': months,
        '그룹1': group1,
        '그룹2': group2,
        '그룹3': group3,
        '라인': line_values
    })

    st.title('📊 월별 개발과제 상태 그래프')

    fig, ax1 = plt.subplots(figsize=(5, 3))

    bar_width = 0.25
    x = np.arange(len(months))

    # 막대 그래프 3개 그리기
    ax1.bar(x - bar_width, data['그룹1'], width=bar_width, label='개발', color='skyblue')
    ax1.bar(x, data['그룹2'], width=bar_width, label='이월', color='orange')
    ax1.bar(x + bar_width, data['그룹3'], width=bar_width, label='보류', color='green')
    #ax1.set_xlabel('월')
    ax1.set_ylabel('막대그래프 값(개수)')
    ax1.set_xticks(x)
    ax1.set_yticks([0, 10, 20, 30, 40])  # y축 틱 위치 지정
    ax1.set_xticklabels(data['월'])
    ax1.legend(loc='upper left')

    # 라인 그래프를 위한 두 번째 y축 생성
    ax2 = ax1.twinx()
    ax2.plot(x, data['라인'], color='red', marker='o', linewidth=2, label='라인그래프')
    ax2.set_ylabel('라인그래프 값(개수)', color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    ax2.set_yticks([30, 40, 50, 60])  # y축 틱 위치 지정
    ax2.legend(loc='upper right')

    st.pyplot(fig)


    data['과제 수용률'] = (data['그룹1'] / (data['그룹1']+data['그룹2']) * 100).round(1).astype(str) + '%'

    data = data.rename(columns={'그룹1': '개발'})
    data = data.rename(columns={'그룹2': '이월'})
    data = data.rename(columns={'그룹3': '보류'})

    # 필요한 열만 출력
    result = data[['월', '개발', '이월', '보류','과제 수용률']]

    # Streamlit 출력
    st.title("📅 3개월 과제 수용률 현황")
    st.dataframe(result, use_container_width=True)