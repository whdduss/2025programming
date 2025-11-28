import streamlit as st
import json
import pandas as pd
import plotly.express as px
from openai import OpenAI
import os

#pip install -r requirements.txt
#pip install plotly==5.17.0 openai==1.3.0 python-dotenv==1.0.0 
#   pip install --upgrade openai
#python -m streamlit run app.py

# API 키 가져오기 (Streamlit Secrets 사용)
def get_api_key():
    """Streamlit Secrets에서 API 키를 안전하게 가져옵니다."""
    try:
        # Streamlit Secrets 사용 (권장)
        if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
            return st.secrets['OPENAI_API_KEY']
    except Exception:
        pass
    
    # 환경 변수에서 가져오기 (대체 방법)
    return os.getenv("OPENAI_API_KEY")
def create_recommendation_prompt(answers, jobs):
    """ChatGPT API를 위한 프롬프트 생성"""
    job_list = "\n".join([f"- {job['name']}: {job['description']}" for job in jobs])
    
    answers_text = "\n".join([f"질문 {i+1}: {answer}" for i, answer in answers.items()])
    
    prompt = f"""
다음은 사용자가 답변한 설문입니다:

{answers_text}

다음은 사용 가능한 IT 직업 목록입니다:

{job_list}

사용자의 답변을 바탕으로 가장 적합한 직업 3개를 추천하고, 각 직업이 왜 적합한지 설명해주세요.
직업 이름은 정확히 위 목록에 있는 이름을 사용해주세요.
"""
    return prompt

def parse_recommendations(text, jobs):
    """ChatGPT 응답에서 직업 이름 추출"""
    recommended = []
    job_names = [job['name'] for job in jobs]
    
    for job_name in job_names:
        if job_name in text:
            recommended.append(job_name)
    
    # 최대 3개까지만
    return recommended[:3] if recommended else []

def recommend_jobs_basic(answers, jobs):
    """기본 추천 로직 (API 키가 없을 때 사용)"""
    scores = {job['name']: 0 for job in jobs}
    
    # 간단한 스코어링 로직
    for job in jobs:
        score = 0
        
        # 답변에 따른 점수 계산
        if "협업" in str(answers.get(0, "")):
            if job['name'] in ["프로젝트 매니저", "데이터 사이언티스트"]:
                score += 2
        elif "혼자" in str(answers.get(0, "")):
            if job['name'] in ["소프트웨어 개발자", "AI/ML 엔지니어"]:
                score += 2
        
        if "연봉" in str(answers.get(1, "")):
            score += job['salary'] / 1000
        elif "균형" in str(answers.get(1, "")):
            score += job['work_life_balance']
        elif "성장" in str(answers.get(1, "")):
            score += job['growth_potential']
        
        if "안정" in str(answers.get(2, "")):
            score += job['stability']
        elif "변화" in str(answers.get(2, "")):
            score += job['growth_potential']
        elif "창의" in str(answers.get(2, "")):
            score += job['creativity']
        
        if "프론트" in str(answers.get(3, "")) or "UI" in str(answers.get(3, "")):
            if job['name'] in ["웹 개발자", "UI/UX 디자이너"]:
                score += 3
        elif "백엔드" in str(answers.get(3, "")) or "시스템" in str(answers.get(3, "")):
            if job['name'] in ["소프트웨어 개발자", "시스템 엔지니어", "데브옵스 엔지니어"]:
                score += 3
        elif "데이터" in str(answers.get(3, "")) or "AI" in str(answers.get(3, "")):
            if job['name'] in ["데이터 사이언티스트", "AI/ML 엔지니어"]:
                score += 3
        
        if "안정" in str(answers.get(4, "")):
            score += job['stability']
        elif "혁신" in str(answers.get(4, "")) or "창의" in str(answers.get(4, "")):
            score += job['creativity']
        elif "성장" in str(answers.get(4, "")) or "학습" in str(answers.get(4, "")):
            score += job['growth_potential']
        
        scores[job['name']] = score
    
    # 상위 3개 직업 반환
    sorted_jobs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [job[0] for job in sorted_jobs[:3]]


# 페이지 설정
st.set_page_config(
    page_title="IT 직업 정보 비교 플랫폼",
    page_icon="💼",
    layout="wide"
)

# 데이터 로드
@st.cache_data
def load_jobs_data():
    try:
        with open('data/jobs_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error("❌ 데이터 파일을 찾을 수 없습니다. data/jobs_data.json 파일이 존재하는지 확인해주세요.")
        st.stop()
    except json.JSONDecodeError:
        st.error("❌ 데이터 파일 형식이 올바르지 않습니다. JSON 형식을 확인해주세요.")
        st.stop()
    except Exception as e:
        st.error(f"❌ 데이터 로드 중 오류가 발생했습니다: {str(e)}")
        st.stop()

# 세션 상태 초기화
if 'selected_job' not in st.session_state:
    st.session_state.selected_job = None

# 데이터 로드
try:
    data = load_jobs_data()
    jobs = data['jobs']
    categories = data['categories']
except Exception:
    st.stop()

# 사이드바 네비게이션
st.sidebar.title("📋 메뉴")
page = st.sidebar.radio(
    "페이지 선택",
    ["직업 정보", "직업별 비교", "나의 직업 찾기"]
)

# 직업 정보 페이지
if page == "직업 정보":
    st.title("💼 IT 직업 정보")
    st.markdown("---")
    
    st.subheader("직업 목록")
    
    # 직업 목록을 그리드로 표시
    cols = st.columns(3)
    for idx, job in enumerate(jobs):
        col_idx = idx % 3
        with cols[col_idx]:
            if st.button(job['name'], key=f"job_{idx}", use_container_width=True):
                st.session_state.selected_job = job
    
    st.markdown("---")
    
    # 선택된 직업 정보 표시
    if st.session_state.selected_job:
        job = st.session_state.selected_job
        st.subheader(f"📌 {job['name']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 기본 정보")
            st.write(f"**설명:** {job['description']}")
        
        with col2:
            st.markdown("### 상세 정보")
            st.metric("연봉", f"{job['salary']:,}만원")
            st.metric("성장 가능성", f"{job['growth_potential']}/10")
            st.metric("업무환경", f"{job['work_environment']}/10")
            st.metric("워라밸", f"{job['work_life_balance']}/10")
            st.metric("창의성", f"{job['creativity']}/10")
            st.metric("안정성", f"{job['stability']}/10")

# 직업별 비교 페이지
elif page == "직업별 비교":
    st.title("📊 직업별 비교")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("직업 선택")
        selected_jobs = []
        for job in jobs:
            if st.checkbox(job['name'], key=f"compare_job_{job['name']}"):
                selected_jobs.append(job)
    
    with col2:
        st.subheader("비교 카테고리 선택")
        category_options = list(categories.keys())
        
        selected_category = st.selectbox(
            "비교할 카테고리를 선택하세요",
            [None] + category_options,
            format_func=lambda x: categories.get(x, "선택하세요") if x else "선택하세요"
        )
    
    st.markdown("---")
    
    # 비교 버튼
    can_compare = (
        selected_category is not None and 
        len(selected_jobs) >= 2
    )
    
    if not can_compare:
        if selected_category is None:
            st.warning("⚠️ 비교할 카테고리를 선택해주세요.")
        elif len(selected_jobs) == 0:
            st.warning("⚠️ 비교할 직업을 최소 2개 이상 선택해주세요.")
        elif len(selected_jobs) == 1:
            st.warning("⚠️ 비교를 위해서는 최소 2개 이상의 직업을 선택해야 합니다.")
    
    if st.button("비교하기", disabled=not can_compare, use_container_width=True):
        if can_compare:
            # 비교 데이터 준비
            compare_data = []
            for job in selected_jobs:
                compare_data.append({
                    '직업': job['name'],
                    categories[selected_category]: job[selected_category]
                })
            
            df = pd.DataFrame(compare_data)
            
            # 바 차트 생성
            fig = px.bar(
                df,
                x='직업',
                y=categories[selected_category],
                title=f"직업별 {categories[selected_category]} 비교",
                labels={
                    '직업': '직업',
                    categories[selected_category]: categories[selected_category]
                },
                color='직업',
                text=categories[selected_category]
            )
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            fig.update_layout(
                xaxis_title="직업",
                yaxis_title=categories[selected_category],
                showlegend=False,
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 데이터 테이블
            st.subheader("비교 데이터")
            st.dataframe(df, use_container_width=True)

# 나의 직업 찾기 페이지
elif page == "나의 직업 찾기":
    st.title("🔍 나의 직업 찾기")
    st.markdown("---")
    st.markdown("설문에 답변하여 본인에게 가장 적합한 IT 직업을 찾아보세요!")
    
    # 설문지 질문
    questions = [
        {
            "question": "1. 어떤 업무 스타일을 선호하나요?",
            "options": [
                "혼자 집중해서 일하는 것",
                "팀과 협업하며 일하는 것",
                "고객과 소통하며 일하는 것"
            ]
        },
        {
            "question": "2. 가장 중요하게 생각하는 것은?",
            "options": [
                "높은 연봉",
                "업무와 삶의 균형",
                "성장 가능성과 도전"
            ]
        },
        {
            "question": "3. 선호하는 업무 환경은?",
            "options": [
                "안정적이고 예측 가능한 환경",
                "빠르게 변화하는 동적인 환경",
                "창의적이고 자유로운 환경"
            ]
        },
        {
            "question": "4. 어떤 기술 분야에 관심이 있나요?",
            "options": [
                "프론트엔드/UI 개발",
                "백엔드/시스템 개발",
                "데이터/AI/ML"
            ]
        },
        {
            "question": "5. 업무에서 가장 중요하게 생각하는 가치는?",
            "options": [
                "안정성과 보장",
                "혁신과 창의성",
                "성장과 학습"
            ]
        }
    ]
    
    # 설문 응답 저장
    answers = {}
    
    st.subheader("설문지")
    for q_idx, q in enumerate(questions):
        answer = st.radio(
            q['question'],
            q['options'],
            key=f"q_{q_idx}",
            index=None
        )
        answers[q_idx] = answer
    
    st.markdown("---")
    
    # 모든 질문에 답변했는지 확인
    all_answered = all(answers.get(i) is not None for i in range(len(questions)))
    
    if not all_answered:
        st.info("💡 모든 질문에 답변해주세요.")
    
    # 직업 찾기 버튼
    if st.button("직업 찾기", disabled=not all_answered, use_container_width=True):
        if all_answered:
            with st.spinner("AI가 분석 중입니다..."):
                # OpenAI API를 사용하여 직업 추천
                api_key = get_api_key()
                
                if not api_key:
                    st.info("💡 OPENAI_API_KEY가 설정되지 않았습니다. 기본 추천 기능을 사용합니다.")
                    st.info("더 정확한 추천을 원하시면 `.streamlit/secrets.toml` 파일에 API 키를 추가해주세요.")
                    st.info("📝 설정 방법: `.streamlit/secrets.toml.example` 파일을 참고하여 `secrets.toml` 파일을 생성하세요.")
                    
                    # 기본 추천 로직 (API 키가 없을 때)
                    recommended_jobs = recommend_jobs_basic(answers, jobs)
                    
                    if recommended_jobs:
                        st.success("✅ 분석 완료!")
                        st.markdown("### 추천 결과")
                        st.info("다음은 설문 답변을 기반으로 추천된 직업입니다.")
                else:
                    try:
                        client = OpenAI(api_key=api_key)
                        
                        # 프롬프트 생성
                        prompt = create_recommendation_prompt(answers, jobs)
                        
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "당신은 IT 직업 상담 전문가입니다. 사용자의 답변을 바탕으로 가장 적합한 IT 직업을 추천해주세요."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.7
                        )
                        
                        recommendation_text = response.choices[0].message.content
                        
                        # 추천된 직업 추출 (간단한 파싱)
                        recommended_jobs = parse_recommendations(recommendation_text, jobs)
                        
                        st.success("✅ 분석 완료!")
                        st.markdown("### AI 추천 결과")
                        st.markdown(recommendation_text)
                        
                    except Exception as e:
                        st.warning(f"⚠️ API 호출 중 오류가 발생했습니다: {str(e)}")
                        st.info("기본 추천 기능을 사용합니다.")
                        recommended_jobs = recommend_jobs_basic(answers, jobs)
                
                # 추천 직업 표시
                if recommended_jobs:
                    st.markdown("---")
                    st.subheader("🎯 추천 직업")
                    
                    for job_name in recommended_jobs:
                        job = next((j for j in jobs if j['name'] == job_name), None)
                        if job:
                            with st.expander(f"📌 {job['name']}", expanded=True):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**설명:** {job['description']}")
                                with col2:
                                    st.metric("연봉", f"{job['salary']:,}만원")
                                    st.metric("성장 가능성", f"{job['growth_potential']}/10")
                                    st.metric("업무환경", f"{job['work_environment']}/10")
                else:
                    st.warning("⚠️ 추천할 직업을 찾을 수 없습니다. 다시 시도해주세요.")

