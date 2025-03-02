import os
import streamlit as st
import google.generativeai as genai
import random
import time
import pandas as pd
from datetime import date
import plotly.express as px  # 그래프 라이브러리 추가
from supabase import create_client  # supabase 라이브러리 임포트

# --- Streamlit 설정 ---
st.set_page_config(
    page_title="초등학생 모의 주식 거래",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS (스타일링) ---
st.markdown(
    """
<style>
/* 전체 폰트 변경 (Nanum Gothic, Google Fonts CDN 사용) */
@import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700&display=swap');
body {
    font-family: 'Nanum Gothic', sans-serif !important;
}

/* 탭 메뉴 스타일 */
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    background-color: #007bff !important;
    color: white !important;
    font-weight: bold;
}
.stTabs [data-baseweb="tab-list"] button {
    background-color: #f0f2f6;
    color: #333;
    border-radius: 8px 8px 0 0;
    padding: 0.75em 1em;
    margin-bottom: -1px; /* border overlap */
}

/* 사이드바 스타일 */
[data-testid="stSidebar"] {
    width: 350px !important;
    background-color: #f8f9fa; /* Light gray sidebar background */
    padding: 20px;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h3 {
    color: #212529; /* Dark gray sidebar headings */
}
[data-testid="stSidebar"] hr {
    border-top: 1px solid #e0e0e0; /* Lighter sidebar hr */
}

/* Metric 스타일 */
.streamlit-metric-label {
    font-size: 16px;
    color: #4a4a4a;
}
.streamlit-metric-value {
    font-size: 28px;
    font-weight: bold;
}

/* 버튼 스타일 */
div.stButton > button {
    background-color: #007bff;
    color: white;
    padding: 12px 24px;
    font-size: 16px;
    border-radius: 8px;
    border: none;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.1); /* Soft shadow */
    transition: background-color 0.3s ease;
}
div.stButton > button:hover {
    background-color: #0056b3;
    box-shadow: 2px 2px 7px rgba(0,0,0,0.15); /* Slightly stronger shadow on hover */
}

/* 보조 버튼 스타일 */
div.stButton > button.secondary-button {
    background-color: #6c757d;
    color: white;
    padding: 10px 20px;
    font-size: 14px;
    border-radius: 6px;
    border: none;
    transition: background-color 0.3s ease;
}
div.stButton > button.secondary-button:hover {
    background-color: #5a6268;
}

/* Expander 스타일 */
.streamlit-expanderHeader {
    font-weight: bold;
    color: #212529;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 8px;
    margin-bottom: 15px;
}

/* Dataframe 스타일 */
.dataframe {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.05); /* Very subtle shadow */
}

/* Info, Success, Error, Warning Box 스타일 (더 부드러운 스타일) */
div.stInfo, div.stSuccess, div.stError, div.stWarning {
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
}
div.stInfo {
    background-color: #e7f3ff;
    border-left: 5px solid #007bff;
}
div.stSuccess {
    background-color: #e6f7ec;
    border-left: 5px solid #28a745;
}
div.stError {
    background-color: #fdeded;
    border-left: 5px solid #dc3545;
}
div.stWarning {
    background-color: #fffbe6;
    border-left: 5px solid #ffc107;
}

/* Toast message 스타일 */
div.streamlit-toast-container {
    z-index: 10000; /* Toast를 항상 맨 위에 표시 */
}
div[data-testid="stToast"] {
    border-radius: 8px;
    padding: 15px;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
}

</style>
""",
    unsafe_allow_html=True,
)


# --- API 키 설정 (Hugging Face Secrets에서 관리 권장) ---
if "GEMINI_API_KEY" not in os.environ:
    st.error(
        "GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. Hugging Face Secrets 또는 환경 변수에 API 키를 설정해주세요."
    )
    st.stop()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# --- Gemini 모델 설정 ---
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 25000,
    "response_mime_type": "text/plain",
}
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",  # 또는 "gemini-pro"
    generation_config=generation_config,
)

# --- 세션 상태 초기화 (Streamlit 앱 상태 관리) ---
if "chat_session" not in st.session_state:
    st.session_state["chat_session"] = model.start_chat(history=[])
if "portfolio" not in st.session_state:
    st.session_state["portfolio"] = {"cash": 10000000, "stocks": {}}
if "stocks" not in st.session_state:
    st.session_state["stocks"] = {  # 섹터별 종목 재구성 및 설명 확장
        "기술(Tech)": {
            "삼성전자": {
                "current_price": random.randint(50000, 80000),
                "price_history": [],
                "description": "대한민국을 대표하는 전자 제품 회사, 삼성전자! 텔레비전, 스마트폰, 냉장고, 세탁기, 컴퓨터 칩 등 우리 생활에 필요한 다양한 제품들을 만들고 있어요. 특히 갤럭시 스마트폰은 전 세계에서 아주 인기가 많고, 텔레비전은 최고 화질로 유명해요. 반도체 기술도 세계 최고 수준이라서, 컴퓨터나 스마트폰의 두뇌 역할을 하는 칩을 만들어 다른 회사들에게도 팔고 있답니다. 우리나라 경제 발전에 아주 큰 역할을 하는 회사예요.",
            },
            "SK하이닉스": {
                "current_price": random.randint(80000, 120000),
                "price_history": [],
                "description": "컴퓨터와 스마트폰의 기억력을 책임지는 SK하이닉스!  우리가 사용하는 컴퓨터나 스마트폰이 사진, 영상, 게임 같은 정보를 저장하고 빠르게 불러올 수 있는 건 SK하이닉스 덕분이에요.  이 회사는 'DRAM'과 'NAND 플래시'라는 아주 중요한 반도체를 만드는데, 이 반도체들은 컴퓨터, 스마트폰뿐만 아니라 인공지능, 빅데이터, 자율주행차 같은 미래 기술에도 꼭 필요하답니다.  세계적으로 손꼽히는 반도체 기술력을 가진 회사예요.",
            },
            "LG디스플레이": {
                "current_price": random.randint(20000, 40000),
                "price_history": [],
                "description": "화면을 더욱 선명하게, LG디스플레이!  우리가 매일 보는 텔레비전, 스마트폰, 노트북 화면을 만드는 회사예요.  LG디스플레이는 특히 'OLED'라는 특별한 기술로 화면을 만드는데, OLED는 색깔이 진짜처럼 선명하고, 얇고 가벼워서 미래 디스플레이 기술로 주목받고 있어요.  영화관처럼 생생한 화질의 텔레비전,  얇고 예쁜 스마트폰 화면,  자동차 계기판과 투명 디스플레이까지, LG디스플레이 기술은 우리 생활 곳곳에 사용되고 있답니다.",
            },
        },
        "자동차(Auto)": {
            "현대자동차": {
                "current_price": random.randint(150000, 250000),
                "price_history": [],
                "description": "대한민국 대표 자동차 회사, 현대자동차!  우리가 타고 다니는 자동차를 만드는 회사 중 가장 유명해요.  쏘나타, 아반떼, 팰리세이드, 아이오닉 등 멋진 이름의 자동차들을 디자인하고 만들어서 우리나라뿐 아니라 전 세계에 팔고 있어요.  최근에는 전기자동차와 수소자동차 같은 친환경 자동차를 개발해서 미래 자동차 시장을 이끌고 있답니다.  자동차를 좋아하는 친구라면 누구나 한 번쯤 들어봤을 이름일 거예요.",
            },
            "기아": {
                "current_price": random.randint(70000, 100000),
                "price_history": [],
                "description": "개성 넘치는 디자인, 기아자동차!  현대자동차와 함께 우리나라 자동차 산업을 이끌고 있어요.  K3, K5, 쏘렌토, 스포티지, EV6, EV9  등 이름만 들어도 멋진 자동차들을 만들고 있어요.  기아자동차는 특히 디자인이 예쁘기로 유명하고, 젊은 친구들에게 인기가 많아요.  최근에는 전기차 EV6와 EV9이 세계적으로 디자인 상을 많이 받아서 더욱 유명해졌답니다.  나만의 개성을 표현하고 싶은 친구들에게 딱 맞는 자동차 회사예요.",
            },
            "현대모비스": {
                "current_price": random.randint(200000, 250000),
                "price_history": [],
                "description": "자동차를 튼튼하게, 안전하게, 현대모비스!  자동차 회사는 아니지만, 자동차를 만드는 데 꼭 필요한 부품들을 전문적으로 만드는 회사예요.  자동차의 심장인 엔진 부품부터,  안전을 지켜주는 브레이크, 에어백,  운전을 편리하게 해주는 첨단 장치까지,  자동차 30000여 개 부품을 만들어요.  현대자동차, 기아뿐 아니라 전 세계 자동차 회사에 부품을 공급하는 아주 중요한 회사랍니다.  겉으로 잘 보이지 않지만, 자동차의 안전과 성능을 책임지는 숨은 영웅 같은 회사예요.",
            },
        },
        "에너지(Energy)": {
            "LG에너지솔루션": {
                "current_price": random.randint(300000, 500000),
                "price_history": [],
                "description": "미래 에너지를 만드는 LG에너지솔루션!  우리가 타고 다니는 전기자동차에 꼭 필요한 배터리를 만드는 회사 중 세계 1등이에요.  전기차 배터리뿐 아니라, 스마트폰, 노트북, 에너지 저장 장치(ESS) 등 다양한 곳에 사용되는 배터리를 만들어요.  태양광, 풍력 같은 친환경 에너지를 더욱 효율적으로 사용할 수 있도록 돕는 기술을 개발하고 있답니다.  지구를 깨끗하게 만드는 데 아주 중요한 역할을 하는 회사예요.",
            },
            "SK이노베이션": {
                "current_price": random.randint(100000, 150000),
                "price_history": [],
                "description": "에너지와 화학의 힘, SK이노베이션!  우리가 사용하는 휘발유, 경유 같은 기름을 만들고,  플라스틱, 옷, 타이어 같은 다양한 제품의 원료가 되는 화학 제품도 만들어요.  최근에는 전기차 배터리 사업을 키워서 미래 에너지 시대를 준비하고 있답니다.  오래전부터 우리나라 에너지 산업을 이끌어온 회사이고, 지금은 친환경 에너지 회사로 변신하고 있어요.",
            },
            "두산에너빌리티": {
                "current_price": random.randint(15000, 25000),
                "price_history": [],
                "description": "힘찬 에너지를 만드는 두산에너빌리티!  우리가 사용하는 전기를 만드는 발전소를 짓고, 발전소에 필요한 기계를 만드는 회사예요.  화력 발전소, 원자력 발전소, 수력 발전소, 풍력 발전소 등 다양한 발전소를 건설하고,  바닷물을 깨끗한 물로 바꾸는 해수담수화 설비도 만들어요.  최근에는 친환경 에너지 기술을 개발해서 지구를 위한 깨끗한 에너지를 만드는 데 힘쓰고 있답니다.  우리나라 전력 공급에 아주 중요한 역할을 하는 회사예요.",
            },
        },
        "인터넷(Internet)": {
            "네이버": {
                "current_price": random.randint(200000, 300000),
                "price_history": [],
                "description": "궁금한 건 뭐든지 물어봐, 네이버!  우리나라에서 가장 유명한 인터넷 검색 엔진 '네이버'를 만드는 회사예요.  검색뿐 아니라 뉴스, 쇼핑, 블로그, 카페, 웹툰, 지도, 번역 등 다양한 인터넷 서비스를 제공하고 있어요.  우리가 매일 사용하는 카카오톡처럼,  라인(LINE)이라는 메신저 앱을 만들어서 해외에서도 인기가 많답니다.  우리나라 인터넷 세상을 만들어가는 대표적인 회사예요.",
            },
            "카카오": {
                "current_price": random.randint(40000, 60000),
                "price_history": [],
                "description": "세상을 연결하는 즐거움, 카카오!  국민 메신저 '카카오톡'을 만든 회사예요.  카카오톡뿐 아니라 카카오택시, 카카오페이, 카카오게임, 카카오웹툰, 카카오뱅크, 카카오맵 등 우리 생활을 편리하고 즐겁게 만들어주는 다양한 서비스를 만들고 있어요.  귀여운 카카오프렌즈 캐릭터도 아주 인기가 많죠?  우리나라 사람들의 하루를 카카오 서비스로 시작해서 카카오 서비스로 끝난다고 할 정도로, 우리 생활에 아주 깊숙이 들어와 있는 회사예요.",
            },
            "카카오뱅크": {
                "current_price": random.randint(20000, 30000),
                "price_history": [],
                "description": "내 손안의 은행, 카카오뱅크!  카카오톡을 만든 카카오에서 만든 특별한 은행이에요.  은행에 직접 가지 않아도 스마트폰 앱으로 계좌를 만들고, 돈을 보내고, 대출도 받을 수 있어요.  복잡한 서류 없이 간편하게 이용할 수 있고,  24시간 언제든지 은행 업무를 볼 수 있다는 장점이 있어요.  은행을 딱딱하고 어렵게 생각하지 않고, 쉽고 재미있게 이용할 수 있도록 도와주는 은행이에요.",
            },
        },
        "소비재(Consumer Goods)": {
            "CJ제일제당": {
                "current_price": random.randint(300000, 400000),
                "price_history": [],
                "description": "맛있는 식탁을 책임지는 CJ제일제당!  우리가 먹는 맛있는 음식들을 만드는 회사예요.  햇반, 비비고, 고메, 백설, 다시다 등 유명한 식품 브랜드를 많이 가지고 있어요.  김치, 만두, 햇반 같은 간편 식품부터,  밀가루, 설탕, 식용유 같은 요리 재료까지,  우리의 식탁을 풍요롭게 만들어주는 다양한 식품들을 만들어요.  영화관에서 먹는 팝콘, 뚜레쥬르 빵, 투썸플레이스 케이크도 CJ제일제당에서 만들어요.",
            },
            "아모레퍼시픽": {
                "current_price": random.randint(130000, 170000),
                "price_history": [],
                "description": "예뻐지는 마법, 아모레퍼시픽!  우리나라 대표 화장품 회사예요.  설화수, 라네즈, 마몽드, 이니스프리, 에뛰드하우스 등 다양한 화장품 브랜드를 만들어서,  아름다움을 꿈꾸는 사람들을 도와주고 있어요.  화장품뿐 아니라 샴푸, 치약, 바디워시 같은 생활용품도 만들고,  녹차, 건강기능식품 사업도 하고 있답니다.  우리나라 여성들의 아름다움을 책임지는 회사라고 할 수 있어요.",
            },
            "LG생활건강": {
                "current_price": random.randint(600000, 800000),
                "price_history": [],
                "description": "깨끗하고 아름다운 생활, LG생활건강!  우리 생활에 필요한 다양한 제품들을 만드는 회사예요.  샴푸, 린스, 비누, 치약, 세제 같은 생활용품부터,  오휘, 숨37°, 빌리프, 더페이스샵 같은 화장품 브랜드까지,  우리 생활을 더욱 깨끗하고 아름답게 만들어주는 제품들을 만들어요.  코카콜라, 스프라이트, 환타 같은 음료수도 LG생활건강에서 판매하고 있답니다.  우리 생활 곳곳에서 만날 수 있는 친근한 회사예요.",
            },
        },
        "금융(Finance)": {
            "KB금융": {
                "current_price": random.randint(50000, 60000),
                "price_history": [],
                "description": "든든한 금융 파트너, KB금융!  우리나라 대표 금융 회사 중 하나예요.  KB국민은행, KB증권, KB손해보험, KB국민카드 등 다양한 금융 회사를 가지고 있어서,  은행, 증권, 보험, 카드 등 다양한 금융 서비스를 제공하고 있어요.  우리나라 사람들이 가장 많이 이용하는 은행 중 하나인 KB국민은행을 운영하고 있고,  집을 살 때 돈을 빌려주는 주택담보대출도 많이 해주는 회사예요.  우리나라 경제를 튼튼하게 만드는 데 중요한 역할을 하고 있어요.",
            },
            "신한지주": {
                "current_price": random.randint(30000, 40000),
                "price_history": [],
                "description": "금융을 새롭게, 신한지주!  KB금융과 함께 우리나라 대표 금융 회사로 손꼽혀요.  신한은행, 신한카드, 신한금융투자, 신한생명 등 다양한 금융 회사를 가지고 있어서,  은행, 카드, 증권, 보험 등 모든 금융 서비스를 제공하고 있어요.  특히 젊은 고객들을 위한 다양한 금융 상품과 서비스를 개발하고 있고,  해외 시장에도 적극적으로 진출하고 있답니다.  빠르게 변화하는 금융 시장을 이끌어가는 회사예요.",
            },
            "하나금융지주": {
                "current_price": random.randint(40000, 50000),
                "price_history": [],
                "description": "금융으로 더 나은 미래, 하나금융지주!  우리나라 대표 금융 회사 중 하나예요.  하나은행, 하나증권, 하나카드, 하나생명 등 금융 회사를 가지고 있어서,  은행, 증권, 카드, 보험 등 금융 서비스를 제공하고 있어요.  외국 돈을 사고파는 외환 거래를 오랫동안 해왔고,  해외 투자와 관련된 금융 서비스도 잘 제공하는 회사예요.  글로벌 금융 시장에서 활약하는 회사라고 할 수 있어요.",
            },
        },
        "건설(Construction)": {
            "삼성물산": {
                "current_price": random.randint(100000, 150000),
                "price_history": [],
                "description": "세계를 건설하는 힘, 삼성물산!  삼성 그룹의 뿌리이자, 건설, 상사, 패션, 리조트 등 다양한 사업을 하는 회사예요.  우리나라 랜드마크 건물인 부르즈 할리파,  페트로나스 트윈 타워 건설에 참여했고,  인천국제공항,  싱가포르 지하철 같은 큰 프로젝트들을 많이 했어요.  건설뿐 아니라 옷을 만들고 팔기도 하고 (빈폴, 갤럭시),  에버랜드, 호텔신라 같은 리조트도 운영하는 다재다능한 회사예요.",
            },
            "HD현대": {
                "current_price": random.randint(40000, 60000),
                "price_history": [],
                "description": "바다를 개척하는 HD현대!  배를 만들고, 건설 기계를 만드는 회사예요.  울산에 있는 큰 조선소에서 아주 큰 배들을 만들고,  굴착기, 지게차 같은 건설 현장에서 볼 수 있는 노란색 기계들도 만들어요.  최근에는 로봇, 인공지능 기술을 개발해서 건설 현장을 더욱 스마트하게 만드는 기술을 개발하고 있답니다.  우리나라 조선 산업과 건설 기계 산업을 이끌어가는 회사예요.",
            },
            "GS건설": {
                "current_price": random.randint(30000, 50000),
                "price_history": [],
                "description": "행복을 짓는 GS건설!  우리가 사는 아파트 '자이'를 만드는 회사예요.  자이 아파트는 살기 좋은 아파트로 유명하고,  우리나라 아파트 브랜드 중에서 인기가 많아요.  아파트뿐 아니라 다리, 도로, 터널 같은 사회 기반 시설도 건설하고,  해외에서도 다양한 건설 프로젝트를 하고 있답니다.  우리나라 주거 문화를 만들어가는 대표적인 건설 회사예요.",
            },
        },
        "유통(Retail)": {
            "롯데쇼핑": {
                "current_price": random.randint(150000, 250000),
                "price_history": [],
                "description": "쇼핑의 즐거움, 롯데쇼핑!  우리나라 대표 유통 회사예요.  롯데백화점, 롯데마트, 롯데슈퍼, 롯데아울렛, 롯데ON 등 다양한 쇼핑 공간을 운영하고 있어요.  옷, 화장품, 식품, 가전제품 등 없는 게 없는 백화점부터,  저렴하고 신선한 식재료를 살 수 있는 마트까지,  우리의 쇼핑 생활을 책임지고 있어요.  영화관 롯데시네마, 테마파크 롯데월드도 롯데쇼핑에서 운영해요.",
            },
            "이마트": {
                "current_price": random.randint(100000, 150000),
                "price_history": [],
                "description": "생활 필수품은 모두 다, 이마트!  우리나라 대표 대형 할인 마트예요.  집에서 사용하는 거의 모든 물건을 살 수 있다고 생각하면 돼요.  신선한 채소, 과일, 고기 같은 식품부터,  세제, 샴푸, 휴지 같은 생활용품,  옷, 장난감, 가전제품까지 정말 다양한 상품을 팔고 있어요.  이마트 자체 브랜드인 '노브랜드', '피코크' 제품들도 인기가 많고,  온라인 쇼핑몰 'SSG닷컴'도 운영하고 있답니다.  우리나라 사람들의 장보기 문화를 대표하는 곳이에요.",
            },
        },
        "통신(Telecom)": {
            "KT": {
                "current_price": random.randint(30000, 40000),
                "price_history": [],
                "description": "빠르고 편리한 통신, KT!  우리나라 대표 통신 회사예요.  집에서 사용하는 인터넷,  스마트폰으로 사용하는 이동통신,  텔레비전 방송(IPTV),  기업들이 사용하는 IT 솔루션 등 다양한 통신 서비스를 제공하고 있어요.  오래전부터 우리나라 통신 산업을 이끌어왔고,  지금도 5G, 인공지능 같은 새로운 기술을 개발해서 더욱 편리한 통신 세상을 만들고 있답니다.  우리나라 정보 통신 발전에 큰 역할을 하는 회사예요.",
            },
            "SK텔레콤": {
                "current_price": random.randint(50000, 70000),
                "price_history": [],
                "description": "무선 통신의 강자, SK텔레콤!  우리나라 대표 통신 회사이고, 특히 이동통신 서비스에서 1등이에요.  스마트폰으로 데이터를 빠르게 사용할 수 있도록 5G, LTE 같은 무선 통신 기술을 개발하고,  인공지능, 메타버스 같은 미래 기술에도 투자하고 있어요.  우리가 스마트폰으로 영상 통화를 하고, 게임을 하고, 유튜브를 볼 수 있는 건 SK텔레콤 덕분이라고 할 수 있어요.  우리나라 무선 통신 기술을 이끌어가는 회사예요.",
            },
        },
        "제약/바이오(Pharma/Bio)": {
            "삼성바이오로직스": {
                "current_price": random.randint(700000, 900000),
                "price_history": [],
                "description": "생명을  소중하게, 삼성바이오로직스!  약은 약인데, 그냥 약이 아니라 아주 특별한 '바이오 의약품'을 만드는 회사예요.  우리 몸속 세포를 이용해서 만드는 바이오 의약품은 병을 치료하는 힘이 아주 세다고 해요.  삼성바이오로직스는 다른 제약 회사들을 위해 바이오 의약품을 대신 만들어주는 일을 전문으로 하고 있어요.  공장을 아주 크게 지어서,  최첨단 설비로 최고 품질의 바이오 의약품을 만들고 있답니다.  아픈 사람들을 위한 희망을 만드는 회사라고 할 수 있어요.",
            },
            "셀트리온": {
                "current_price": random.randint(180000, 250000),
                "price_history": [],
                "description": "바이오 의약품으로 질병과 싸우는 셀트리온!  삼성바이오로직스처럼 바이오 의약품을 만드는 회사인데,  셀트리온은 직접 새로운 바이오 의약품을 개발하고, 만들어서 전 세계에 팔고 있어요.  관절염, 암, 자가면역질환 같은 무서운 병들을 치료하는 바이오 의약품을 만들고 있고,  저렴한 가격으로 바이오 의약품을 만들어서 더 많은 사람들이 치료받을 수 있도록 노력하고 있답니다.  바이오 의약품 분야에서 우리나라를 대표하는 회사예요.",
            },
        },
        "화학(Chemical)": {
            "LG화학": {
                "current_price": random.randint(600000, 800000),
                "price_history": [],
                "description": "생활 속 화학, LG화학!  우리가 매일 사용하는 플라스틱, 옷, 신발, 건전지, 자동차 배터리,  화장품 원료까지 정말 다양한 화학 제품을 만드는 회사예요.  눈에 보이지 않지만 우리 생활 곳곳에 LG화학 제품들이 사용되고 있답니다.  최근에는 친환경 플라스틱,  전기차 배터리 소재 같은 미래 기술 개발에도 힘쓰고 있어요.  우리나라 화학 산업을 이끌어가는 대표적인 회사예요.",
            },
            "금호석유화학": {
                "current_price": random.randint(120000, 180000),
                "price_history": [],
                "description": "산업의 기초 소재, 금호석유화학!  자동차 타이어,  건축 자재,  포장재,  장갑,  운동화 밑창 등 다양한 제품의 원료가 되는 합성고무를 만드는 회사예요.  합성고무는 천연고무보다 더 튼튼하고,  다양한 기능을 가질 수 있어서 산업 현장에서 아주 많이 사용된답니다.  우리나라 합성고무 산업을 처음 시작했고, 지금도 세계적인 기술력을 가지고 있어요.  산업 발전에 꼭 필요한 숨은 영웅 같은 회사예요.",
            },
        },
        "철강(Steel)": {
            "POSCO홀딩스": {
                "current_price": random.randint(300000, 400000),
                "price_history": [],
                "description": "철강으로 나라를 튼튼하게, POSCO홀딩스!  우리나라 대표 철강 회사이고,  세계적으로도 아주 큰 철강 회사예요.  자동차, 배, 건물, 다리, 기차,  가전제품 등 우리 생활 곳곳에 사용되는 철강 제품을 만들어요.  철강은 튼튼하고 튼튼해서 오랫동안 사용할 수 있고,  재활용도 잘 돼서 친환경적인 소재이기도 해요.  우리나라 산업 발전에 없어서는 안 될 중요한 회사예요.",
            },
            "현대제철": {
                "current_price": random.randint(50000, 70000),
                "price_history": [],
                "description": "자동차와 건설의 뼈대, 현대제철!  현대자동차 그룹의 철강 회사이고,  자동차와 건설에 사용되는 철강 제품을 전문적으로 만들어요.  자동차 차체를 튼튼하게 만드는 철판,  건물을 짓는 뼈대 역할을 하는 철근,  배를 만드는 데 사용하는 후판 등 다양한 철강 제품을 만들어요.  최근에는 친환경 철강 제조 기술을 개발해서 더욱 깨끗한 환경을 만드는 데 노력하고 있답니다.  현대자동차 그룹의 성장에 큰 힘이 되는 회사예요.",
            },
        },
        "운송(Transportation)": {
            "대한항공": {
                "current_price": random.randint(20000, 30000),
                "price_history": [],
                "description": "하늘을 나는 꿈, 대한항공!  우리나라 대표 항공사이고,  가장 많은 비행기를 가지고 있어요.  우리나라에서 다른 나라로 여행을 가거나,  다른 나라에서 우리나라로 여행을 올 때 대한항공 비행기를 많이 이용해요.  사람뿐 아니라 소중한 물건들을 안전하고 빠르게 전 세계로 운송하는 일도 하고 있답니다.  비행기 조종사, 승무원을 꿈꾸는 친구들이라면 누구나 가고 싶어 하는 회사일 거예요.",
            },
            "HMM": {
                "current_price": random.randint(20000, 30000),
                "price_history": [],
                "description": "바다를 누비는 HMM!  우리나라 대표 해운 회사이고,  아주 큰 배들을 많이 가지고 있어요.  우리가 사용하는 물건들은 대부분 배를 통해서 다른 나라에서 우리나라로, 우리나라에서 다른 나라로 이동한답니다.  HMM은 컨테이너선이라는 큰 배로 물건들을 실어 나르는 일을 전문으로 하고 있어요.  우리나라와 전 세계를 연결하는 중요한 역할을 하는 회사예요.",
            },
        },
        "엔터테인먼트(Entertainment)": {
            "CJ ENM": {
                "current_price": random.randint(80000, 120000),
                "price_history": [],
                "description": "즐거움을 디자인하는 CJ ENM!  텔레비전 방송, 영화, 음악, 공연 등 다양한 엔터테인먼트 사업을 하는 회사예요.  tvN, Mnet, OCN 같은 유명한 텔레비전 채널을 운영하고 있고,  '기생충', '부산행', '겨울왕국 2' 같은 유명한 영화들을 만들거나 투자했어요.  마마, KCON 같은 큰 음악 행사도 만들고,  뮤지컬, 연극 공연도 제작하는 등 우리 생활에 즐거움을 주는 다양한 문화 콘텐츠를 만들고 있어요.",
            },
            "하이브": {
                "current_price": random.randint(200000, 300000),
                "price_history": [],
                "description": "음악으로 세상을 감동시키는 하이브!  전 세계적으로 엄청난 인기를 누리고 있는 방탄소년단(BTS)을 키운 회사예요.  BTS뿐 아니라 투모로우바이투게더(TXT), 세븐틴, 르세라핌, 뉴진스 등 인기 아이돌 그룹들이 많이 소속되어 있어요.  음반 제작, 매니지먼트, 공연뿐 아니라 게임, 웹툰, 교육 사업까지 확장해서 다양한 분야에서 즐거움을 주고 있답니다.  우리나라 대중문화를 세계에 알리는 데 큰 역할을 하는 회사예요.",
            },
        },
        "식품(Food)": {
            "오리온": {
                "current_price": random.randint(120000, 180000),
                "price_history": [],
                "description": "맛있는 과자, 오리온!  우리나라 대표 과자 회사이고,  초코파이, 오!감자, 포카칩, 꼬북칩, 고래밥 등 맛있고 재미있는 과자들을 많이 만들어요.  어린이부터 어른까지 누구나 좋아하는 과자들을 만들어서,  우리나라뿐 아니라 중국, 러시아, 베트남 등 해외에서도 인기가 많답니다.  과자를 좋아하는 친구라면 오리온 과자를 한 번쯤 먹어봤을 거예요.",
            },
            "농심": {
                "current_price": random.randint(300000, 400000),
                "price_history": [],
                "description": "국민 라면, 농심!  우리나라 대표 라면 회사이고,  신라면, 안성탕면, 짜파게티, 너구리, 새우깡 등 오랜 시간 동안 사랑받는 라면과 스낵들을 많이 만들어요.  매콤한 신라면, 구수한 안성탕면,  달콤 짭짤한 짜파게티,  얼큰한 너구리,  고소한 새우깡 등 다양한 맛과 종류의 라면과 스낵을 만들어서,  우리나라 사람들의 입맛을 즐겁게 해주고 있어요.  라면을 좋아하는 친구라면 농심 라면을 꼭 먹어봤을 거예요.",
            },
        },
    }
    for sector in st.session_state["stocks"]:  # 초기 price_history 채우기 (섹터별로 순회)
        for stock_name in st.session_state["stocks"][sector]:
            st.session_state["stocks"][sector][stock_name]["price_history"].append(
                st.session_state["stocks"][sector][stock_name]["current_price"]
            )

if "news_analysis_results" not in st.session_state:
    st.session_state["news_analysis_results"] = {}
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "daily_news" not in st.session_state:
    st.session_state["daily_news"] = None
if "previous_daily_news" not in st.session_state:
    st.session_state["previous_daily_news"] = None
if "news_date" not in st.session_state:
    st.session_state["news_date"] = None
if "news_meanings" not in st.session_state:
    st.session_state["news_meanings"] = {}
if (
    "ai_news_analysis_output" not in st.session_state
):
    st.session_state["ai_news_analysis_output"] = {}
if "day_count" not in st.session_state:
    st.session_state["day_count"] = 1
if "sector_news_impact" not in st.session_state:
    st.session_state["sector_news_impact"] = {}
if 'buy_confirm' not in st.session_state:
    st.session_state['buy_confirm'] = False
if 'sell_confirm' not in st.session_state:
    st.session_state['sell_confirm'] = False


# --- 뉴스 생성 함수 ---
def generate_news():
    day_count = st.session_state["day_count"]
    prompt = f"""
지시:
초등학생 6학년 수준에 맞춰서, 주식 시장과 경제에 관련된 뉴스 기사 5개를 생성해주세요.
각 기사는 12~15문장 정도로 자세하게 작성하고, 특정 회사 이름이나 주식 종목을 직접적으로 언급하지 마세요.
학생들이 뉴스를 읽고 어떤 회사가 유망할지 또는 쇠락할지 스스로 추론할 수 있도록 일반적인 경제 상황이나 산업 동향에 대한 뉴스를 만들어주세요.
긍정적 뉴스, 부정적 뉴스, 중립적 뉴스 다양하게 생성하세요.(긍정, 부정, 중립 이라는 말은 표시하지 마세요.)
뉴스에 따라 주식이 상승하기도 하고 하락하기도 할 수 있습니다.
각 뉴스 기사는 "## 뉴스 [번호]" 로 시작해주세요. (예: ## 뉴스 1, ## 뉴스 2 ...)

**생성된 뉴스 기사:**
"""
    chat_session = st.session_state["chat_session"]
    response = chat_session.send_message(prompt)
    news_text = response.text.strip()

    news_articles = []
    if news_text:
        news_articles = [
            article.strip() for article in news_text.split("## 뉴스 ") if article.strip()
        ]

    return news_articles[:5]


def explain_daily_news_meanings(daily_news):
    if daily_news is None:
        return {}

    meanings = {}
    for i, news_article in enumerate(daily_news):
        prompt = f"""
    **신문 기사:**
    {news_article}

    **지시:**
    위 신문 기사의 핵심 의미를 초등학생 6학년이 이해하기 쉽게 3문장 이내로 요약해서 "해설: " 다음에 설명해주세요.
    그리고 이 뉴스와 관련된 주식 섹터 1~2개를 쉼표로 구분해서 "관련 섹터: " 다음에 알려주세요. 관련 섹터가 없다면 "관련 섹터: 없음" 이라고 해주세요.

    뉴스 의미 해설:
    """
        chat_session = st.session_state["chat_session"]
        try:
            response = chat_session.send_message(prompt)
            meaning_text = response.text.strip()

            explanation = ""
            related_sectors = []

            if "해설:" in meaning_text:
                explanation_start_index = meaning_text.find("해설:") + len("해설:")
                explanation_end_index = meaning_text.find("관련 섹터:")
                if explanation_end_index != -1:
                    explanation = meaning_text[explanation_start_index:explanation_end_index].strip()
                else:
                    explanation = meaning_text[explanation_start_index:].strip()

            if "관련 섹터:" in meaning_text:
                related_sectors_str = meaning_text.split("관련 섹터:")[1].strip()
                if related_sectors_str.lower() != "없음":
                    related_sectors = [sector.strip() for sector in related_sectors_str.split(',')]
                else:
                    related_sectors = [] # "없음" explicitly means empty list

            meanings[str(i + 1)] = {"explanation": explanation, "sectors": related_sectors}


        except google.api_core.exceptions.ResourceExhausted as e:
            st.error(
                f"API 할당량 초과 오류가 발생했습니다. 잠시 후 다시 시도해주세요. 오류 메시지: {e}"
            )
            return None
        time.sleep(1)
    return meanings


def buy_stock(stock_name, quantity, sector):
    if (
        sector not in st.session_state["stocks"]
        or stock_name not in st.session_state["stocks"][sector]
    ):
        st.session_state["messages"].append(
            {"type": "error", "text": "존재하지 않는 주식 종목입니다."}
        )
        return

    if quantity <= 0:
        st.session_state["messages"].append(
            {"type": "error", "text": "매수 수량은 1주 이상이어야 합니다."}
        )
        return

    stock_price = st.session_state["stocks"][sector][stock_name]["current_price"]
    max_quantity = st.session_state["portfolio"]["cash"] // stock_price
    if quantity > max_quantity:
        st.session_state["messages"].append(
            {
                "type": "error",
                "text": f"매수 가능 수량을 초과했습니다. (최대 {max_quantity}주까지 매수 가능)",
            }
        )
        st.toast(
            f"매수 가능 수량을 초과했습니다. (최대 {max_quantity}주까지 매수 가능)", icon="❌"
        )
        st.error(f"잔액이 부족합니다. (최대 {max_quantity}주까지 매수 가능)")
        return

    total_price = stock_price * quantity

    if st.session_state["portfolio"]["cash"] >= total_price:
        st.session_state["portfolio"]["cash"] -= total_price
        portfolio_stocks = st.session_state["portfolio"]["stocks"]
        if (
            stock_name in portfolio_stocks
        ):
            portfolio_stocks[stock_name]["quantity"] += quantity
            portfolio_stocks[stock_name]["purchase_price"] = (
                portfolio_stocks[stock_name]["purchase_price"]
                * (portfolio_stocks[stock_name]["quantity"] - quantity)
                + total_price
            ) / portfolio_stocks[stock_name]["quantity"]
        else:
            portfolio_stocks[stock_name] = {
                "quantity": quantity,
                "purchase_price": total_price / quantity,
            }
        st.session_state["messages"].append(
            {
                "type": "success",
                "text": f"{stock_name} {quantity}주 매수 완료. 총 {total_price:,.0f}원 소요.",
            }
        )
        st.success(f"{stock_name} {quantity}주 매수 완료. 총 {total_price:,.0f}원 소요.")
        st.toast(
            f"{stock_name} {quantity}주 매수 완료. 총 {total_price:,.0f}원 소요.", icon="✅"
        )
        st.session_state['buy_confirm'] = False
    else:
        st.session_state["messages"].append(
            {"type": "error", "text": "잔액이 부족합니다."}
        )
        st.toast("잔액이 부족합니다.", icon="❌")
        st.error(f"잔액이 부족합니다. (최대 {max_quantity}주까지 매수 가능)")
        st.session_state['buy_confirm'] = False


def sell_stock(stock_name, quantity):
    if stock_name not in st.session_state["portfolio"]["stocks"]:
        st.session_state["messages"].append(
            {"type": "error", "text": "보유하고 있지 않은 주식입니다."}
        )
        st.error("보유하고 있지 않은 주식입니다.")
        st.toast("보유하고 있지 않은 주식입니다.", icon="❌")
        return

    owned_quantity = st.session_state["portfolio"]["stocks"][stock_name]["quantity"]

    if owned_quantity < quantity:
        st.session_state["messages"].append(
            {"type": "error", "text": "매도 수량이 보유 주식 수를 초과했습니다."}
        )
        st.error("매도 수량이 보유 주식 수를 초과했습니다.")
        st.toast("매도 수량이 보유 주식 수를 초과했습니다.", icon="❌")
        return

    if quantity <= 0:
        st.session_state["messages"].append(
            {"type": "error", "text": "잘못된 매도 수량입니다."}
        )
        st.error("잘못된 매도 수량입니다.")
        st.toast("잘못된 매도 수량입니다.", icon="❌")
        return

    stock_price = 0
    stock_sector = ""
    for sector, stocks in st.session_state["stocks"].items():
        if stock_name in stocks:
            stock_price = stocks[stock_name]["current_price"]
            stock_sector = sector
            break

    if stock_price == 0:
        st.session_state["messages"].append(
            {"type": "error", "text": "주식 정보를 찾을 수 없습니다."}
        )
        return

    sell_price = stock_price * quantity
    st.session_state["portfolio"]["cash"] += sell_price
    st.session_state["portfolio"]["stocks"][stock_name]["quantity"] -= quantity
    if st.session_state["portfolio"]["stocks"][stock_name]["quantity"] == 0:
        del st.session_state["portfolio"]["stocks"][stock_name]

    st.session_state["messages"].append(
        {
            "type": "success",
            "text": f"{stock_name} {quantity}주 매도 완료. 총 {sell_price:,.0f}원 획득.",
        }
    )
    st.toast(
        f"{stock_name} {quantity}주 매도 완료. 총 {sell_price:,.0f}원 획득.", icon="✅"
    )
    st.success(f"{stock_name} {quantity}주 매도 완료. 총 {sell_price:,.0f}원 획득.")
    st.session_state['sell_confirm'] = False


def update_stock_prices():
    if not st.session_state["daily_news"]:
        return

    sector_impacts = {sector: 0 for sector in st.session_state["stocks"]}

    for i, news_article in enumerate(st.session_state["daily_news"]):
        news_meaning = st.session_state["news_meanings"].get(str(i + 1))
        if news_meaning:
            related_sectors = news_meaning.get("sectors", [])
            news_explanation = news_meaning.get("explanation", "")

            news_sentiment = 0
            if "상승" in news_article or "성장" in news_article or "긍정적" in news_article or "유망" in news_article or "호황" in news_article:
                news_sentiment = 1
            elif "하락" in news_article or "감소" in news_article or "부정적" in news_article or "어려움" in news_article or "침체" in news_article or "위기" in news_article:
                news_sentiment = -1
            else:
                news_sentiment = 0

            for sector in related_sectors:
                if sector in sector_impacts:
                    sector_impacts[sector] += news_sentiment * 0.05

    for sector in st.session_state["stocks"]:
        sector_impact = sector_impacts[sector]
        for stock_name in st.session_state["stocks"][sector]:
            change_rate = random.uniform(-0.02, 0.02) + sector_impact
            change_rate = max(-0.3, min(0.3, change_rate))
            st.session_state["stocks"][sector][stock_name]["current_price"] *= (
                1 + change_rate
            )
            st.session_state["stocks"][sector][stock_name]["current_price"] = max(
                1, int(st.session_state["stocks"][sector][stock_name]["current_price"])
            )
            st.session_state["stocks"][sector][stock_name]["price_history"].append(
                st.session_state["stocks"][sector][stock_name]["current_price"]
            )
    st.session_state["messages"].append({"type": "info", "text": "주가가 변동되었습니다."})
    st.toast("주가가 변동되었습니다.", icon="📈")
    st.info("주가가 변동되었습니다.")
    st.session_state["sector_news_impact"] = sector_impacts


def display_portfolio():
    portfolio = st.session_state["portfolio"]
    cash = portfolio["cash"]
    total_value = cash
    total_purchase_value = 0
    for stock_name, stock_info in portfolio["stocks"].items():
        quantity = stock_info["quantity"]
        purchase_price = stock_info["purchase_price"]
        current_price = 0
        stock_sector = ""
        for sector, stocks in st.session_state["stocks"].items():
            if stock_name in stocks:
                current_price = stocks[stock_name]["current_price"]
                stock_sector = sector
                break
        if current_price != 0:
            stock_value = current_price * quantity
            total_value += stock_value
            purchase_value = purchase_price * quantity
            total_purchase_value += purchase_value

    initial_cash = 10000000
    total_profit_loss = total_value - initial_cash
    total_profit_rate = (
        (total_profit_loss / initial_cash) * 100 if initial_cash != 0 else 0
    )

    return cash, total_value, total_profit_rate


def display_stock_prices():
    stocks_data = []
    for sector, sector_stocks in st.session_state["stocks"].items():
        for stock_name, stock_info in sector_stocks.items():
            price_history = stock_info["price_history"]
            daily_change_rate_str = " - " # 기본값
            if len(price_history) >= 2:
                previous_day_price = price_history[-2]
                current_price = price_history[-1]
                daily_change_rate = (current_price - previous_day_price) / previous_day_price * 100
                daily_change_rate_str = f"{daily_change_rate:.2f}%"

            stocks_data.append(
                {
                    "종목": stock_name,
                    "섹터": sector,
                    "현재 주가": f"{stock_info['current_price']:,} 원",
                    "전일 대비": daily_change_rate_str, # 전일 대비 등락률 추가
                    "price_history": stock_info["price_history"],
                    "description": stock_info["description"],
                }
            )
    stocks_df = pd.DataFrame(stocks_data)
    st.dataframe(stocks_df[["섹터", "종목", "현재 주가", "전일 대비"]], hide_index=True) # "전일 대비" 컬럼 추가

    selected_stock_all_info = st.selectbox(
        "종목 선택 (기업 정보 및 주가 그래프)", stocks_df["종목"].tolist()
    )
    if selected_stock_all_info:
        selected_stock_sector = stocks_df[
            stocks_df["종목"] == selected_stock_all_info
        ]["섹터"].iloc[0]
        col1_info, col2_graph = st.columns([1, 2])

        with col1_info:
            st.subheader("기업 정보")
            st.info(
                f"**{selected_stock_all_info} ({selected_stock_sector})**\n\n{st.session_state['stocks'][selected_stock_sector][selected_stock_all_info]['description']}"
            )

        with col2_graph:
            st.subheader("주가 그래프")
            price_history_df = pd.DataFrame(
                {
                    "날짜": range(
                        1,
                        len(
                            st.session_state["stocks"][selected_stock_sector][
                                selected_stock_all_info
                            ]["price_history"]
                        )
                        + 1,
                    ),
                    "주가": st.session_state["stocks"][selected_stock_sector][
                        selected_stock_all_info
                    ]["price_history"],
                }
            )
            fig = px.line(
                price_history_df,
                x="날짜",
                y="주가",
                title=f"{selected_stock_all_info} ({selected_stock_sector}) 주가 변동",
            )
            st.plotly_chart(fig)
    else:
        st.info("종목을 선택하여 기업 정보와 주가 그래프를 확인하세요.")


def display_portfolio_table():
    portfolio = st.session_state["portfolio"]
    if portfolio["stocks"]:
        portfolio_data = []
        total_value = portfolio["cash"]
        total_purchase_value = 0
        total_profit_loss = 0
        total_profit_rate = 0.0
        for stock_name, stock_info in portfolio["stocks"].items():
            quantity = stock_info["quantity"]
            purchase_price = stock_info["purchase_price"]
            current_price = 0
            stock_sector = ""
            for sector, stocks in st.session_state["stocks"].items():
                if stock_name in stocks:
                    current_price = stocks[stock_name]["current_price"]
                    stock_sector = sector
                    break

            if current_price == 0:
                continue

            stock_value = current_price * quantity
            purchase_value = purchase_price * quantity
            profit_loss = stock_value - purchase_value
            profit_rate = (
                (profit_loss / purchase_value) * 100 if purchase_value != 0 else 0
            )
            total_value += stock_value
            total_purchase_value += purchase_value
            total_profit_loss += profit_loss

            portfolio_data.append(
                {
                    "종목": stock_name,
                    "섹터": stock_sector,
                    "보유 수량": quantity,
                    "매수 단가": f"{purchase_price:,.0f} 원",
                    "현재가": f"{current_price:,.0f} 원",
                    "평가액": f"{stock_value:,.0f} 원",
                    "손익": f"{profit_loss:,.0f} 원",
                    "수익률": f"{profit_rate:.2f}%",
                }
            )
        portfolio_data.append(
            {
                "종목": "현금",
                "섹터": "-",
                "보유 수량": "-",
                "매수 단가": "-",
                "현재가": "-",
                "평가액": f"{portfolio['cash']:,} 원",
                "손익": "-",
                "수익률": "-",
            }
        )
        portfolio_df = pd.DataFrame(portfolio_data)
        st.dataframe(portfolio_df, hide_index=True, height=350)
        st.markdown(
            f"""**현금 잔고:** {portfolio['cash']:,} 원
    **📊 총 평가액:** {total_value:,.0f} 원
    **🛒 총 매수 금액:** {total_purchase_value:,.0f} 원
    **📈📉 총 손익:** {total_profit_loss:,.0f} 원  (🚀 수익률: {total_profit_rate:.2f}%)
    """
        )
    else:
        st.info("보유 주식이 없습니다.")


# --- 주식 용어 사전 ---
def display_stock_glossary():
    glossary = {
        "주식": "회사의 일부분을 나타내는 증서. 주식을 사면 회사의 주인이 되는 거예요.",
        "주가": "주식 1개당 가격. 사람들이 주식을 사고팔 때 가격이 변해요.",
        "매수": "주식을 사는 것.",
        "매도": "주식을 파는 것.",
        "포트폴리오": "내가 가진 주식과 현금 목록.",
        "수익률": "원래 돈에서 얼마나 이익을 보았는지 비율로 나타낸 것. (이익 / 원래 돈) X 100",
        "상승": "주가가 오르는 것.",
        "하락": "주가가 내리는 것.",
        "변동": "주가가 오르락내리락 움직이는 것.",
        "투자": "돈을 넣어 이익을 얻으려고 하는 모든 활동.",
        "섹터": "비슷한 사업을 하는 회사들을 묶어 놓은 그룹 (예: 기술 섹터, 자동차 섹터)",
        "전일 대비 등락률": "오늘 주가가 어제보다 얼마나 변했는지 퍼센트로 나타낸 것. +는 상승, -는 하락.", # 용어 추가
    }
    with st.sidebar.expander("📚 주식 용어 사전", expanded=False):
        for term, definition in glossary.items():
            st.markdown(f"**{term}:** {definition}")
        st.markdown("---")


# --- 로그인 페이지 추가 ---
def login_page():
    import streamlit as st
    # Import 모달 기능을 제공하는 서드파티 라이브러리 사용. (pip install streamlit-modal 필요)
    from streamlit_modal import Modal
    
    # 모달 창 생성
    modal = Modal("로그인", key="login_modal")
    with modal.container():
        st.title("로그인")
        account_input = st.text_input("아이디", key="login_account")
        password_input = st.text_input("비밀번호", type="password", key="login_pw")
        
        if st.button("로그인", key="login_button"):
            try:
                # supabase의 users 테이블에서 account와 pw 컬럼을 조회
                response = supabase.table("users").select("account", "pw").eq("account", account_input).execute()
                
                if response.data and response.data[0]["pw"] == password_input:
                    st.session_state["account"] = account_input
                    modal.close()
                    st.success("로그인 성공!")
                    st.experimental_rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")
            except Exception as e:
                st.error(f"로그인 중 오류 발생: {e}")
    
    # 모달이 닫히지 않은 상태이면 실행을 중단하여 메인페이지가 표시되지 않도록 함
    if "account" not in st.session_state:
        st.stop()


# --- session_state를 Supabase에 저장하는 함수 ---
def save_session_state():
    if 'account' not in st.session_state:
        st.error('로그인 정보가 없습니다. 먼저 로그인해 주세요.')
        return
    supabase_url = os.getenv('SUPABASE_URL')  # .env 파일에서 Supabase URL 불러오기
    supabase_key = os.getenv('SUPABASE_KEY')  # .env 파일에서 Supabase 키 불러오기
    supabase = create_client(supabase_url, supabase_key)
    # session_state에서 저장할 데이터를 선택적으로 구성할 수 있음
    data_to_save = { key: st.session_state[key] for key in st.session_state if key not in ['account'] }
    response = supabase.table('users').update({'data': data_to_save}).eq('account', st.session_state['account']).execute()
    if response.status_code == 200 or response.status_code == 201:
        st.info('세션 상태가 저장되었습니다.')
    else:
        st.error('세션 상태 저장에 실패했습니다.')


# --- 메인 화면 ---
def main():
    col_news, col_main_ui = st.columns([1, 2])

    with col_news:
        st.header(f"📰 Day {st.session_state['day_count']} 뉴스")
        if st.button("뉴스 생성", use_container_width=True, key="news_gen_button"):
            with st.spinner(f"Day {st.session_state['day_count']} 뉴스 생성 중..."):
                current_daily_news = generate_news()
                st.session_state["daily_news"] = current_daily_news
            # 뉴스 생성이 완료되면 session_state 저장
            save_session_state()

        if st.session_state["daily_news"]:
            st.subheader(f"Day {st.session_state['day_count']} 뉴스")
            for i, news in enumerate(st.session_state["daily_news"]):
                with st.expander(f"뉴스 {i+1}", expanded=False):
                    st.write(news)

        if st.session_state["previous_daily_news"] and st.session_state[
            "news_meanings"
        ]:
            st.subheader(f"Day {st.session_state['day_count'] - 1} 뉴스 해설")
            st.info("AI가 분석한 어제 뉴스 해설입니다.")
            with st.expander(f"Day {st.session_state['day_count'] - 1} 뉴스 해설 보기", expanded=False):
                if st.session_state["news_meanings"]:
                    for i, meaning_data in st.session_state["news_meanings"].items():
                        st.markdown(f"**뉴스 {i}**:")
                        st.markdown(f"**AI 해설:** {meaning_data['explanation']}") # Markdown 으로 변경
                        if meaning_data['sectors']:
                            st.markdown(f"**관련 섹터:** {', '.join(meaning_data['sectors'])}") # Markdown 으로 변경
                        else:
                            st.markdown("**관련 섹터:** 없음") # Markdown 으로 변경
                else:
                    st.info("어제 뉴스에 대한 해설이 없습니다.")

        elif not st.session_state["daily_news"]:
            st.info("뉴스 생성 버튼을 눌러 오늘의 뉴스를 받아보세요.")

    with col_main_ui:
        menu = st.tabs(
            ['현재 주가', '내 포트폴리오', '주식 매수', '주식 매도', '어제 뉴스 해설']
        )

        with menu[0]:
            st.subheader("📈 현재 주가 및 기업 정보")
            st.markdown("주식 시장의 현재 가격과 기업 정보를 확인하세요.")
            display_stock_prices()

        with menu[1]:
            st.subheader("📊 내 포트폴리오")
            st.markdown("현재 보유 중인 주식과 자산을 확인하세요.")
            display_portfolio_table()

        with menu[2]:
            st.subheader("💰 주식 매수")
            st.markdown("AI 예측과 뉴스 분석을 바탕으로 주식을 매수해보세요.")
            sector_names = list(st.session_state["stocks"].keys())
            selected_sector_buy = st.selectbox("매수 섹터 선택:", sector_names)
            stock_names_in_sector = list(
                st.session_state["stocks"][selected_sector_buy].keys()
            )
            selected_stock_buy = st.selectbox("매수 종목 선택:", stock_names_in_sector)

            stock_price_buy = st.session_state["stocks"][selected_sector_buy][
                selected_stock_buy
            ]["current_price"]
            st.info(f"**{selected_stock_buy}** 현재 주가: {stock_price_buy:,.0f}원")
            quantity_buy = st.number_input(
                "매수 수량 (주):", min_value=1, value=1, step=1
            )

            if not st.session_state['buy_confirm']:
                if st.button("주식 매수", use_container_width=True, key='buy_button_confirm'):
                    st.session_state['buy_confirm'] = True
            else:
                st.warning("정말 매수하시겠습니까?")
                col_confirm, col_cancel = st.columns([1, 1])
                with col_confirm:
                    if st.button("✅ 매수 확인", use_container_width=True, key='buy_confirm_button'):
                        buy_stock(selected_stock_buy, quantity_buy, selected_sector_buy)
                        save_session_state()

                with col_cancel:
                    if st.button("❌ 매수 취소", use_container_width=True, key='buy_cancel_button', type='secondary'):
                        st.session_state['buy_confirm'] = False
                        st.info("매수를 취소했습니다.")

        with menu[3]:
            st.subheader("📉 주식 매도")
            st.markdown("보유 중인 주식을 판매하고 수익을 실현해보세요.")
            if st.session_state["portfolio"]["stocks"]:
                stock_names_sell = list(st.session_state["portfolio"]["stocks"].keys())
                selected_stock_sell = st.selectbox("매도 종목 선택:", stock_names_sell)
                stock_price_sell = 0
                for sector, stocks in st.session_state["stocks"].items():
                    if selected_stock_sell in stocks:
                        stock_price_sell = stocks[selected_stock_sell]["current_price"]
                        break

                st.info(f"**{selected_stock_sell}** 현재 주가: {stock_price_sell:,.0f}원")
                max_sell_quantity = st.session_state["portfolio"]["stocks"][
                    selected_stock_sell
                ]["quantity"]
                quantity_sell = st.number_input(
                    "매도 수량 (주):",
                    min_value=1,
                    max_value=max_sell_quantity,
                    value=1,
                    step=1,
                )
                if not st.session_state['sell_confirm']:
                    if st.button("주식 매도", use_container_width=True, key='sell_button_confirm'):
                        st.session_state['sell_confirm'] = True
                else:
                    st.warning("정말 매도하시겠습니까?")
                    col_confirm, col_cancel = st.columns([1, 1])
                    with col_confirm:
                        if st.button("✅ 매도 확인", use_container_width=True, key='sell_confirm_button'):
                            sell_stock(selected_stock_sell, quantity_sell)
                            save_session_state()
                    with col_cancel:
                        if st.button("❌ 매도 취소", use_container_width=True, key='sell_cancel_button', type='secondary'):
                            st.session_state['sell_confirm'] = False
                            st.info("매도를 취소했습니다.")
            else:
                st.info("보유 주식이 없습니다. 포트폴리오 탭에서 확인하세요.")

        with menu[4]:
            if st.session_state["previous_daily_news"] and st.session_state[
                "news_meanings"
            ]:
                st.subheader(f"Day {st.session_state['day_count'] - 1} 뉴스 해설")
                st.info("AI가 분석한 어제 뉴스 해설입니다.")
                for i in range(len(st.session_state["previous_daily_news"])):
                    with st.expander(f"뉴스 {i+1}", expanded=False):
                        news_content = st.session_state["previous_daily_news"][i]
                        st.markdown("**뉴스 원문:**")
                        st.write(news_content)
                        meaning_data = st.session_state["news_meanings"].get(str(i+1))
                        if meaning_data:
                            st.markdown("**AI 해설:**")
                            st.info(meaning_data['explanation'])
                            if meaning_data['sectors']:
                                st.markdown("**관련 섹터:**")
                                st.info(', '.join(meaning_data['sectors']))
                            else:
                                st.info("**관련 섹터:** 없음")
                        else:
                            st.warning("뉴스 해설을 생성하지 못했습니다.")
            else:
                st.info(
                    "이전 뉴스 해설이 없습니다. 하루 지나가기 버튼을 눌러 뉴스 해설을 받아보세요."
                )

    with st.sidebar:
        st.markdown("# 💰 초등학생을 위한 모의 주식 거래")
        st.markdown(f"### Day {st.session_state['day_count']}")
        st.markdown("---")
        st.markdown("쉽고 재미있는 주식 투자 📈")
        st.markdown("📰 신문 기사를 읽고 미래를 예측해보세요!")
        cash, total_value, profit_rate = display_portfolio()
        st.metric(label="💰 현금 잔고", value=f"{cash:,.0f} 원")
        st.metric(label="📊 총 평가 금액", value=f"{total_value:,.0f} 원")
        st.metric(label="🚀 총 수익률", value=f"{profit_rate:.2f}%")
        st.markdown("---")

        if st.button("하루 지나기", use_container_width=True, key="day_pass_button"):
            if st.session_state["daily_news"]:
                with st.spinner(f"Day {st.session_state['day_count']} 주가 변동 및 이전 뉴스 분석..."):
                    st.session_state["previous_daily_news"] = st.session_state["daily_news"]
                    meanings = explain_daily_news_meanings(
                        st.session_state["previous_daily_news"]
                    )
                    if meanings:
                        st.session_state["news_meanings"] = meanings
                    update_stock_prices()
                    st.session_state["daily_news"] = generate_news()
                    st.session_state["day_count"] += 1
                    st.rerun()
                    st.info("어제 뉴스 해설 탭에서 AI가 분석한 뉴스 해설을 확인해보세요.")
            else:
                st.warning("오늘의 뉴스를 먼저 생성해주세요.")
        st.markdown("***")

        display_stock_glossary()

        with st.expander("🚀 앱 사용 가이드", expanded=False):
            st.markdown(
                """
        **1단계: 뉴스 생성하기**
        - 왼쪽 '오늘의 뉴스' 영역에서 '뉴스 생성' 버튼을 클릭하세요.
        - AI가 주식 시장 뉴스를 5개 만들어줍니다.

        **2단계: 뉴스 읽고 예측하기**
        - '오늘의 뉴스' 아래 뉴스들을 꼼꼼히 읽어보세요.
        - 각 뉴스를 읽고 '🤔 어떤 회사가 이 뉴스 때문에 돈을 더 많이 벌 수 있을까?' 또는 '😥 손해를 볼 회사는 어디일까?' 생각해 보세요.
        - 초등학생 눈높이에서 쉽고 재미있게, 미래를 예측하는 연습을 할 수 있습니다.

        **3단계: 주가 및 기업 정보 확인하기**
        - 메뉴에서 '📈 현재 주가' 탭을 선택하세요.
        - 현재 여러분이 가진 주식과 현금 잔고, 총 평가액, 수익률 등을 한눈에 볼 수 있습니다.
        - 투자 결과가 어떤지, 얼마나 이익/손해를 봤는지 확인해보세요.

        **4단계: 주식 매수하기**
        - 메뉴에서 '💰 주식 매수' 탭을 선택하세요.
        - '매수 종목 선택' 메뉴에서 원하는 회사를 고르세요.
        - '매수 수량'을 입력하고 '주식 매수' 버튼을 클릭하면, 주식을 살 수 있습니다.
        - **팁:**  여러분의 뉴스 예측을 바탕으로 주식을 골라보세요!

        **5단계: 포트폴리오 확인하기**
        - 메뉴에서 '📊 내 포트폴리오' 탭을 선택하세요.
        - 현재 여러분이 가진 주식과 현금 잔고, 총 평가액, 수익률 등을 한눈에 볼 수 있습니다.
        - 투자 결과가 어떤지, 얼마나 이익/손해를 봤는지 확인해보세요.

        **6단계: 주식 매도하기**
        - 메뉴에서 '📉 주식 매도' 탭을 선택하세요.
        - '매도 종목 선택' 메뉴에서 팔고 싶은 주식을 고르세요.
        - '매도 수량'을 입력하고 '주식 매도' 버튼을 클릭하면, 주식을 팔고 현금을 얻을 수 있습니다.
        - **팁:** 주가가 올랐을 때 팔아서 이익을 남겨보세요!

        **7단계: 하루 지나기 & 이전 뉴스 의미 해설 보기**
        - 사이드바 메뉴의 '하루 지나기' 버튼을 클릭하세요.
        - 주가가 변동되고, 새로운 하루가 시작됩니다.
        - '어제 뉴스 해설' 탭에서 각 뉴스의 '뉴스 의미' 해설이 추가된 것을 확인해보세요.
        - AI가 이전 뉴스 (어제 뉴스)의 핵심 의미를 초등학생 눈높이에 맞춰 쉽게 설명해줍니다.

        **계속해서 배우고 성장하기! 🌱**
        - 모의 주식 거래 앱을 꾸준히 사용하면서, 뉴스-주가 관계를 배우고 투자 감각을 키워보세요.
        - 처음에는 어렵더라도, 계속 연습하면 주식 투자가 더 재미있고 쉬워질 거예요! 😉
        """
            )


if __name__ == "__main__":
    if "account" not in st.session_state:
        login_page()
        st.stop()
    main()