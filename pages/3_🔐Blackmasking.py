import streamlit as st
import cv2
import numpy as np
import io
from PIL import Image
import re
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

# Azure 설정
#AZURE_SERVICE_ENDPOINT = ""
#AZURE_SERVICE_KEY = ""

client = DocumentIntelligenceClient(
    endpoint=st.secrets["AZURE_SERVICE_ENDPOINT"],
    credential=AzureKeyCredential(st.secrets["AZURE_SERVICE_KEY"])
)

st.title("🆔 신분증 블랙 마스킹 (Azure + OpenCV)")

uploaded_file = st.file_uploader("신분증 이미지를 업로드하세요", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 이미지 MIME 타입 얻기 (e.g. 'image/jpeg')
    content_type = uploaded_file.type

    # 이미지 바이너리 읽기 (한 번만!)
    image_bytes = uploaded_file.read()
    
    # 예시: bytes_source 활용
    analyze_request = AnalyzeDocumentRequest(bytes_source=image_bytes)
    
    # BytesIO로 감싸고 포인터 맨 앞으로
    image_stream = io.BytesIO(image_bytes)
    image_stream.seek(0)

    # 원본 이미지 표시
    #st.image(image_bytes, caption="원본 이미지", use_column_width=True) # 이미지 크기를 화면에 맞춤
    st.image(image_bytes, caption="원본 이미지")
    
    # PIL → OpenCV 변환
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # Azure Document Intelligence 호출
    with st.spinner("Azure AI로 신분증 분석 중..."):
        poller = client.begin_analyze_document(
            model_id="prebuilt-idDocument",
            body=analyze_request
        )
    result = poller.result()

    
    def id_pattern_search(result_driverLicense):
        for page in result_driverLicense.pages:
            for line in page.lines:
                text = line.content

                if re.search(r"\d{6}-\d{7}", text):  # 주민번호 패턴 찾기
                    print(line.content)
                    print("좌표:", line.polygon)
                    return line.polygon


    # 마스킹 필드
    sensitive_fields = ["FirstName", "DocumentNumber", "Address"]

    # 필드별 마스킹
    for doc in result.documents:
        st.write(f"🆔 문서 타입: {doc.doc_type}")  # 예: "idDocument.driverLicense", "idDocument.passport"
        for field_name, field in doc.fields.items():
            st.write(f"감지된 필드: {field_name} - 값: {field.content}") # 감지된 필드 출력
            if field_name in sensitive_fields:
                if not field.bounding_regions:
                    st.warning(f"{field_name} 필드에는 bounding box 정보가 없어 마스킹할 수 없습니다.")
                    continue
                for region in field.bounding_regions:
                    for page in result.pages:
                        if page.page_number == region.page_number:
                            polygon = region.polygon
                            #if polygon and len(polygon) == 4:
                            # if polygon:
                            #     st.write(polygon)
                            #     h, w = cv_image.shape[:2]
                            #     if isinstance(polygon[0], float):  # float 리스트 처리
                            #         pts = [(int(polygon[i] * w / 200), int(polygon[i+1] * h / 200)) for i in range(0, len(polygon), 2)]
                            #     else:  # 객체 리스트 처리 (기존 코드)
                            #         pts = [(int(p.x * w), int(p.y * h)) for p in polygon]
                            #     x_coords = [p[0] for p in pts]
                            #     y_coords = [p[1] for p in pts]
                            #     x_min, y_min = min(x_coords), min(y_coords)
                            #     x_max, y_max = max(x_coords), max(y_coords)
                            #     st.write(x_min, y_min, x_max, y_max)
                            #     cv2.rectangle(cv_image, (x_min, y_min), (x_max, y_max), (0, 0, 0), 1)
                            #     st.write(f"✅ 마스킹 처리됨: {field_name}")
                            
                            if polygon and (len(polygon) == 8 or isinstance(polygon[0], object)):
                                #st.write("📌 polygon:", polygon)
                                if doc.doc_type == "idDocument.driverLicense" and field_name == "DocumentNumber":
                                    polygon = id_pattern_search(result)
                                
                                h, w = cv_image.shape[:2]

                                # float 리스트일 경우 (normalized 좌표: 0~200 기준)
                                if isinstance(polygon[0], float):
                                    if len(polygon) % 2 == 0:
                                        pts = [(int(polygon[i] * w / 400), int(polygon[i+1] * h / 250)) for i in range(0, len(polygon), 2)]
                                    else:
                                        st.warning("⚠️ 잘못된 polygon 길이 (float list)")
                                        pts = []
                                else:
                                    # 객체 리스트일 경우
                                    try:
                                        pts = [(int(p.x * w), int(p.y * h)) for p in polygon]
                                    except AttributeError:
                                        st.warning("⚠️ polygon 객체에 x/y 속성이 없음")
                                        pts = []

                                if len(pts) >= 2:
                                    x_coords = [p[0] for p in pts]
                                    y_coords = [p[1] for p in pts]
                                    x_min, y_min = min(x_coords), min(y_coords)
                                    x_max, y_max = max(x_coords), max(y_coords)
                                    st.write("✅ Bounding box:", x_min, y_min, x_max, y_max)

                                    # 마스킹: 사각형 그리기
                                    cv2.rectangle(cv_image, (x_min, y_min), (x_max, y_max), (0, 0, 0), -1)  # -1 = 내부 채우기

                                    st.write(f"✅ 마스킹 처리됨: {field_name}")
                                else:
                                    st.warning("⚠️ 유효한 좌표가 부족하여 마스킹 생략됨")


    # 결과 표시
    st.success("분석 및 마스킹 완료!")
    #st.image(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB), caption="마스킹된 이미지", use_column_width=True)
    st.image(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB), caption="마스킹된 이미지")
    
    # st.write(cv_image.shape[:2])
    # cv2.polylines(cv_image, [np.array(pts)], isClosed=True, color=(0,255,0), thickness=2)
    # st.image(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))