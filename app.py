import streamlit as st
import requests
import json
import random
import matplotlib.pyplot as plt
import numpy as np
import time
import base64
import platform
import re

# [Matplotlib 한국어 깨짐 방지] 로컬 환경 및 배포 환경 대응
if platform.system() == "Windows":
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == "Darwin":
    plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# 동적 계량기 그래프 생성 함수 (글자 잘림 방지 반영)
def draw_gauge_chart(score=None):
    fig, ax = plt.subplots(figsize=(5, 2.6))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    sizes = [30, 40, 30, 100]
    colors = ['#2ecc71', '#f1c40f', '#e74c3c', 'none']
    ax.pie(sizes, colors=colors, startangle=180, counterclock=False, wedgeprops=dict(width=0.22, edgecolor='none'))

    ax.text(-0.9, -0.12, "안전\n(0% - 30%)", color='#2ecc71', fontsize=9, ha='center', va='top', weight='bold')
    ax.text(0, 1.18, "주의\n(31% - 70%)", color='#f1c40f', fontsize=9, ha='center', va='bottom', weight='bold')
    ax.text(0.9, -0.12, "심각\n(71% - 100%)", color='#e74c3c', fontsize=9, ha='center', va='top', weight='bold')

    if score is not None:
        angle_rad = np.pi * (1 - score / 100.0)
        needle_length = 0.75
        x = needle_length * np.cos(angle_rad)
        y = needle_length * np.sin(angle_rad)

        ax.plot([0, x], [0, y], color='#333333', linewidth=3.0, zorder=5)
        ax.plot(0, 0, marker='o', color='#333333', markersize=9, zorder=6)
        ax.text(0, 0.2, f"{score}%", color='#333333', fontsize=16, ha='center', va='center', weight='bold')

    ax.axis('equal')
    ax.set_ylim(-0.4, 1.5) 
    plt.tight_layout()
    return fig

# API 통신 함수
@st.cache_data(show_spinner=False)
def call_pinktax_api(product_name, product_details, image_bytes, mime_type, ai_provider, model_choice, api_key):
    prompt = f"""
    너는 불필요한 미사여구를 모두 빼고 핵심만 냉철하게 지적하는 독립형 '젠더 마케팅 가격 차별 분석 시스템'이야.
    절대 가격을 임의로 상상하거나 과거 데이터로 환각(Hallucination)하지 말고, 사용자가 제공한 상세 정보 및 실시간 검색 결과를 바탕으로 현재 시장에서 유통되는 실제 정가와 실제 판매가(할인가)를 확인하여 분석해.
    너는 구글(Google), 제미나이(Gemini), 오픈라우터(OpenRouter), 젬마(Gemma) 등의 인공지능 모델 또는 회사 이름을 본문에 절대 밝히거나 언급해서는 안 돼. 오직 자체 개발된 전용 분석 프로그램처럼 답변해.

    [🚨 성별 라벨 매칭 절대 준수 규칙]
    1. 분석 대상 제품이 '남성용 제품', '포맨(For Men)', 혹은 남성 전문 브랜드(예: 비레디(Be Ready), 대시랩, 그라펜, 오브제 등)인 경우, 불합리한 가격 차별이 발견되면 최종 판별에 절대로 '핑크택스 현상'을 출력해서는 안 되며, 반드시 [비합리적 젠더 마케팅 의심 상품 (블루택스 현상)]으로 출력해야 함.
    2. 분석 대상 제품이 '여성용 제품', '포우먼(For Women)', 혹은 일반 여성 타겟 마케팅 상품인 경우에 가격 차별이 발견되면, 그때만 [비합리적 젠더 마케팅 의심 상품 (핑크택스 현상)]을 출력해야 함.
    3. 남성 전문 브랜드에 핑크택스 레이블을 붙이는 논리적 모순을 범할 경우 너의 시스템 연산은 실패한 것으로 간주됨. 칼같이 분기할 것.

    [비공개 절대 준수 규칙]
    1. 출력하는 최종 결과의 제목, 항목 이름, 본문 문장을 포함한 모든 영역에 이모티콘이나 이모지(모든 그래픽 아이콘)를 절대 사용하지 마. 오직 담백한 텍스트와 마크다운 기호만 사용해야 해.
    2. "~라고 생각됩니다", "~해 볼 수 있습니다" 같은 진부하고 모호한 AI 말투를 전면 금지하고, PPT 장표에 바로 삽입할 수 있도록 요약형 개조식 명사형 종결 어미(~함, ~ 선택됨, ~ 판단됨 등) 위주로 단도직입적으로 서술해.

    [분석 대상 제품 및 정보]
    - 제품명: {product_name if product_name else '사용자가 사진을 제공함 (사진 속 제품 정보를 기반으로 식별할 것)'}
    - 추가 상세 정보 (사용자가 입력한 가격, 용량 등): {product_details if product_details else '없음 (시장 유통 가격 데이터에 의존할 것)'}

    [출력 요구 양식 - 반드시 이 틀과 철자를 그대로 유지하며 이모티콘은 뺄 것]
    ### 젠더 마케팅 진단 대시보드
    - 분석 대상 제품명: [분석한 제품의 정확한 제조사 및 제품명을 명확히 기록]
    - 위험도 지수: [0% ~ 100% 사이의 퍼센트 수치와 위험 단계 표기]
    - 최종 판별: [비합리적 젠더 마케팅 의심 상품 (핑크택스 현상) / 비합리적 젠더 마케팅 의심 상품 (블루택스 현상) / 정상적인 원가 반영 상품 중 택일하여 정확히 출력]
    - 제품 정가: [확인된 제품의 정가 출력 후 소스 명시]
    - 분석 기준 가격: [확인된 실제 시장 판매가(할인가) 출력 후 소스 명시]

    ---

    ### 3대 가이드라인 칼날 분석
    1. 성분 및 스펙 가성비: [제품의 전성분, 핵심 활성 성분(Active Ingredients), 배합 비율 및 제조 원가 요소를 자체 데이터베이스와 대조하여 가격 차이의 기술적 타당성을 1~2줄로 요약 서술]
    2. 젠더 라벨 왜곡도: [성별 마케팅 라벨(여성용/남성용)을 제외하고 보았을 때 제품 본연의 가치와 가격의 합리성, 그리고 핑크택스 혹은 블루택스 해당 여부의 논리적 근거를 1~2줄로 요약 서술]
    3. 단위당 가격 차별성: [용량 조정, 패키징 변경, 유통 채널 차이에 따른 불합리한 단위당 가격 차이를 1~2줄로 요약 서술]

    ---

    ### 대학생 스마트 대안 소비 가이드
    - 추천 대체 키워드: [이 제품 대신 소비자가 검색창에 입력해야 할 구체적인 대체 키워드]
    - 현실적인 대안 플랜: [대학생의 지갑 사정을 고려한 실질적이고 명확한 해결책 1줄]
    """

    if ai_provider == "Google Gemini":
        parts = [{"text": prompt}]
        if image_bytes and mime_type:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({"inlineData": {"mimeType": mime_type, "data": b64_image}})

        models_to_try = [model_choice, "gemini-2.5-pro" if model_choice == "gemini-2.5-flash" else "gemini-2.5-flash"]
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
            payload = {
                "contents": [{"parts": parts}],
                "tools": [{"googleSearch": {}}], 
                "generationConfig": {"temperature": 0.0}
            }
            for attempt in range(3):
                try:
                    response = requests.post(url, headers=headers, json=payload)
                    response_json = response.json()
                    if "error" in response_json:
                        err_msg = response_json["error"].get("message", "")
                        err_code = response_json["error"].get("code", 0)
                        if err_code == 503 or "high demand" in err_msg.lower() or "overloaded" in err_msg.lower():
                            time.sleep(1.5 + attempt)
                            continue
                        break
                    if "candidates" in response_json:
                        return {"text": response_json['candidates'][0]['content']['parts'][0]['text']}
                except Exception:
                    time.sleep(1)
                    continue
        return {"error": "구글 인프라 전반이 일시적인 트래픽 폭증으로 마비되었습니다. 잠시 후 다시 시도해 주세요."}

    elif ai_provider == "OpenRouter (Gemma 2)":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_choice,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            response_json = response.json()
            if "choices" in response_json:
                return {"text": response_json['choices'][0]['message']['content']}
            elif "error" in response_json:
                return {"error": response_json["error"].get("message", "오픈라우터 내부 에러 발생")}
        except Exception as e:
            return {"error": f"오픈라우터 통신 실패: {e}"}


# --- 메인 웹 화면 구성 ---
st.title("AI 핑크택스 판별기")
st.write("본 시스템은 객관적인 대안 소비 가이드라인에 따라 제품의 젠더 마케팅 가격 차별성을 분석합니다.")

# 핑크택스 개념 안내 디자인 마크다운 박스
st.markdown("""
<div style="background-color: #FFF5F7; border: 1px solid #FF1493; border-left: 6px solid #FF1493; padding: 16px; border-radius: 6px; margin-top: 10px; margin-bottom: 20px;">
    <p style="color: #FF1493; margin: 0 0 6px 0; font-weight: bold; font-size: 17px;">💡 핑크택스(Pink Tax)란?</p>
    <p style="color: #333333; margin: 0; line-height: 1.6; font-size: 14.5px;">
        동일한 성분, 기능, 용량의 제품·서비스임에도 단순히 <b>'여성용'</b> 마케팅 라벨이나 디자인이 적용되었다는 이유로 가격이 더 비싸지는 <b>성별 기반 가격 차별 현상</b>을 뜻합니다.<br>
        <small style="color: #777777; font-style: italic;">(반대로 남성향 전용 라벨을 붙여 단가 거품을 형성하는 현상은 '블루택스'라고 부릅니다.)</small>
    </p>
</div>
""", unsafe_allow_html=True)

st.caption("※ 시스템 이용 유의사항: 본 프로그램의 분석 결과는 자체 지식 지표와 알고리즘에 기반한 추정치입니다. 제조사의 실시간 가격 변동 및 성분 리뉴얼에 따라 미세한 차이가 발생할 수 있으므로 참고용 데이터로만 활용해 주시기 바랍니다.")

# --- 팀 프로젝트 소개 사이드바 ---
with st.sidebar:
    st.header("사이트 정보")
    st.subheader("세계와 시민 (GCP 프로젝트)")
    st.markdown("---")
    st.write("**개발 및 기획 팀: V.I.A**")
    st.caption("- 조원: 배진한, 정수빈, 박단비, 이서희")
    st.markdown("---")

    ai_provider = st.selectbox(
        "메인 AI 플랫폼 인프라 선택",
        ["Google Gemini", "OpenRouter (Gemma 2)"]
    )

    if ai_provider == "Google Gemini":
        model_choice = st.selectbox("시스템 분석 엔진 버전", ["gemini-2.5-flash", "gemini-2.5-pro"])
    else:
        model_choice = st.selectbox("시스템 분석 엔진 버전", ["google/gemma-2-27b-it"])

# 화면 상단 탭 구성
tab1, tab2 = st.tabs(["제품 판별기", "판별 기준 안내"])

# --- 1번 탭: 제품 판별기 ---
with tab1:
    if ai_provider == "Google Gemini":
        product_name = st.text_input("판별하고 싶은 제품의 제품명을 입력하세요 (사진을 올릴 경우 생략 가능)", placeholder="예: 비레디 웨이크업 생기 립밤")
        uploaded_file = st.file_uploader("제품 전면 사진 또는 전성분 표기 사진을 업로드하세요 (선택사항)", type=["jpg", "jpeg", "png"])
    else:
        product_name = st.text_input("판별하고 싶은 제품의 제품명을 입력하세요", placeholder="예: 비레디 웨이크업 생기 립밤")
        st.caption("ℹ️ **안내**: 현재 선택하신 *Gemma 2* 엔진은 텍스트 전용 최적화 모델입니다. 사진 업로드 및 멀티모달 분석 기술을 사용하시려면 왼쪽 사이드바에서 **Google Gemini** 플랫폼을 선택해 주시기 바랍니다.")
        uploaded_file = None

    product_details = st.text_area("제품의 상세 정보나 가격, 용량 차이가 있다면 적어주세요 (선택사항)", placeholder="")

    if st.button("판별 요청하기"):
        if not product_name and not uploaded_file:
            st.warning("제품명을 입력하거나 제품 사진을 업로드해 주세요.")
        elif ai_provider == "OpenRouter (Gemma 2)" and not product_name:
            st.warning("제품명을 입력해 주세요.")
        else:
            with st.spinner(f"현재 {ai_provider} 인프라를 통해 인터넷 데이터 대조 분석 중..."):

                image_bytes = None
                mime_type = None
                if uploaded_file is not None:
                    image_bytes = uploaded_file.read()
                    mime_type = uploaded_file.type

                if ai_provider == "Google Gemini":
                    api_key = st.secrets["GEMINI_API_KEY"]
                else:
                    api_key = st.secrets["OPENROUTER_API_KEY"]

                result = call_pinktax_api(product_name, product_details, image_bytes, mime_type, ai_provider, model_choice, api_key)

                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success("분석 결과 도출이 완료되었습니다.")

                    ai_text = result["text"]
                    score_value = 0
                    try:
                        score_match = re.search(r"위험도\s*지수\s*:\s*(\d+)\s*%", ai_text)
                        if score_match:
                            score_value = int(score_match.group(1))
                        else:
                            score_match_alt = re.search(r"(\d+)\s*%", ai_text)
                            if score_match_alt:
                                score_value = int(score_match_alt.group(1))
                    except Exception:
                        score_value = 0

                    st.write("**[실시간 위험도 시각화 대시보드]**")
                    st.pyplot(draw_gauge_chart(score_value))

                    st.markdown(ai_text)
                    st.markdown("---")
                    st.caption("본 분석 리포트는 전성분 기반 원가 예측 모델의 결과물이며 법적 효력을 가지지 않는 참고용 자료입니다.")

# --- 2번 탭: 판별 기준 안내 ---
with tab2:
    st.subheader("시스템 알고리즘 판단 기준")
    st.write("본 프로그램은 대학생 대안 소비 유도 및 합리적 자원 배분을 위해 설정된 3대 가이드라인을 기반으로 점수를 산정합니다.")
    st.markdown("---")
    st.write("**[위험도 지수별 단계 가이드]**")

    st.pyplot(draw_gauge_chart())
    st.markdown("---")

    st.markdown("""
    ### 1. 성분 및 스펙 가성비 분석
    - 자체 축적된 화학 성분 지식 데이터를 바탕으로 제품의 핵심 활성 성분(Active Ingredients), 정제수 외 주요 배합 원료, 제조 원가 요소를 정밀 분석합니다.
    - 성별 분할 제품 간에 가격 차이를 정당화할 만한 고가의 원료 차이나 기술적 스펙 차이가 존재하지 않는데도 고가로 책정된 경우 감점 요인이 됩니다.

    ### 2. 젠더 라벨 왜곡도 분석
    - 제품명과 홍보 문구에 포함된 '여성용', '남성용', '포 맨(For Men)', '포 우먼(For Women)' 등 성별 고정관념을 자극하는 마케팅 요소를 강제로 걷어냅니다.
    - 여성향 라벨에 가격 프리미엄이 붙은 **핑크택스(Pink Tax)** 및 남성향 전문 라벨에 단가 거품이 형성된 **블루택스(Blue Tax)** 현상을 전방위적으로 추적 및 대조하여 분석합니다.

    ### 3. 단위당 가격 차별성 분석
    - 용량을 의도적으로 쪼개어 파는 편법(쉬링크플레이션형 차별)이나, 특정 성별이 주로 이용하는 유통 채널의 마찰 비용을 분석합니다.
    - 단순 총액이 아닌 1ml당 가격, 1g당 가격 등 단위당 가격을 엄격하게 대조하여 불합리한 가격 차별성을 추적합니다.
    """)
