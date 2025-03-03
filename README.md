---
title: 초등학생을 위한 모의 주식
emoji: 📈
colorFrom: yellow
colorTo: red
sdk: streamlit
app_file: app.py
pinned: false
license: cc
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

# 초등 주식 모의투자 앱

## 기능

- 초등학생이 주식 모의투자를 할 수 있는 앱
- gemini로 기사를 생성하고 이를 바탕으로 주식 모의투자를 할 수 있는 앱
- 주식을 모의로 사고 팔 수 있음
- Supabase를 활용한 데이터 저장
- Supabase의 users 테이블에 account에 아이디 저장, pw에 비밀번호 저장, data에 json형식으로 데이터 저장

## 기술 스택

- **프론트엔드**: Python, streamlit
- **데이터베이스**: Supabase
- **AI**: Gemini

## 설치 방법

1. 프로젝트 클론

https://github.com/powerwarez/stocksimulBM.git

2. 패키지 설치

```bash
pip install -r requirements.txt
```

3. 환경 변수 설정

```bash
cp .env.example .env
```

4. 앱 실행

```bash
streamlit run app.py
```

## 프로젝트 구조

```bash
stocksimulBM/
    app.py
    .env
    requirements.txt
    README.md
```
