# 🌧️ TADAC Backend — 202moon

> **2026-1 동국대학교 융합캡스톤디자인 03팀 202moon**의 BE-AI 레포지토리입니다.

---

## 📌 프로젝트 소개

**TADAC**은 유튜브 강의 영상을 기반으로 한 **AI 기반 능동적 학습 플랫폼**입니다.

단순히 영상을 보는 것에서 벗어나, **피젯 모드**와 **집중호우 모드** 두 가지 인터랙티브 학습 모드를 통해 집중력을 높이고 학습 효율을 극대화합니다.

- 🎯 유튜브 URL 입력 → AI가 핵심 키워드 자동 추출
- 🌀 **피젯 모드**: 영상 시청 중 피젯스피너/키캡으로 손 자극 유지
- 🌧️ **집중호우 모드**: 키워드가 화면에 낙하 → 타이핑으로 받아치는 게임형 학습
- 🧠 **뽀모도로 퀴즈**: 15~20분마다 자동 퀴즈 팝업으로 복습
- 📊 **학습 결과 & AI 정리본**: 세션 종료 후 GPT 기반 구조화 요약 제공

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| Language | Python 3.x |
| Framework | Django REST Framework |
| AI | OpenAI Whisper API, GPT API |
| Task Queue | Celery |
| Database | PostgreSQL |
| Auth | JWT (SimpleJWT) |

---

## 📁 프로젝트 구조

```
tadac_backend/
├── auth/           # 인증 (회원가입, 로그인, 토큰)
├── users/          # 유저 프로필, 환경설정
├── sessions/       # 학습 세션 관리
├── game/           # 게임(집중호우 모드) 로직
├── quiz/           # 뽀모도로 퀴즈
├── analytics/      # 학습 결과 및 기록
├── common/         # 공통 모듈
├── logs/           # 로그 관리
├── project/        # Django 프로젝트 설정
└── manage.py
```

---

## 🔌 API 명세

### 🔐 Auth

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/auth/register/` | 회원가입 |
| POST | `/api/auth/login/` | 로그인 |
| POST | `/api/auth/logout/` | 로그아웃 |
| POST | `/api/auth/token/refresh/` | 토큰 재발급 |
| POST | `/api/auth/password/reset-request/` | 비밀번호 찾기 이메일 발송 |
| POST | `/api/auth/password/reset-confirm/` | 새 비밀번호 설정 |
| POST | `/api/auth/survey/` | 온보딩 설문 저장 |

### 👤 Users

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/users/me/` | 내 프로필 조회 |
| PATCH | `/api/users/me/` | 프로필 수정 |
| PUT | `/api/users/me/password/` | 비밀번호 변경 |
| DELETE | `/api/users/me/` | 회원 탈퇴 |
| GET | `/api/users/me/settings/` | 환경설정 조회 |
| PATCH | `/api/users/me/settings/` | 환경설정 수정 |
| GET | `/api/users/me/history/` | 전체 학습 기록 조회 |

### 📹 Session

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/sessions/` | 학습 영상 목록 조회 |
| POST | `/api/sessions/` | 새 세션 생성 (URL/파일 업로드) |
| GET | `/api/sessions/{id}/` | 세션 상세 조회 |
| PATCH | `/api/sessions/{id}/` | 세션 제목 수정 |
| DELETE | `/api/sessions/{id}/` | 세션 삭제 |
| GET | `/api/sessions/{id}/status/` | AI 처리 상태 폴링 |
| POST | `/api/sessions/{id}/process/` | AI 파이프라인 실행 |

### 🎮 Game

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/sessions/{id}/game/start/` | 게임 시작 및 학습 데이터 반환 |
| POST | `/api/sessions/{id}/game/end/` | 게임 종료 |

### 📝 Quiz

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/sessions/{id}/quiz/{qid}/answer/` | 퀴즈 답안 제출 |
| GET | `/api/sessions/{id}/quiz/retry/` | 퀴즈 다시 풀기 |

### 📊 Analytics

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/sessions/{id}/result/` | 세션 학습 결과 조회 |
| GET | `/api/sessions/{id}/summary/` | AI 정리본 조회 |

---

## ✨ 주요 기능 명세

### 🌀 피젯 모드
- 영상 재생 중 피젯스피너 / 키캡 모드 전환 (기본키: Alt)
- 마우스 휠로 스피너 조작 (관성 효과 포함)
- 영상 재생 / 일시정지 / 배속 / Seek bar / 자막 온오프

### 🌧️ 집중호우 모드
- Whisper STT → 단어별 타임스탬프 추출
- GPT 핵심 키워드 추출 → 타임스탬프 매핑
- 키워드 낙하 애니메이션 + 자막 빈칸 동기화
- 타이핑 정답 판정 / 콤보 카운터 / 파티클 이펙트
- 빈칸 개수 & 낙하 속도 자동/수동 조절

### 🧠 뽀모도로 퀴즈
- 15~20분 간격 자동 일시정지 후 퀴즈 팝업
- GPT 자동 생성 4지선다 퀴즈
- 정답/오답 즉각 피드백

### 📊 학습 결과
- 시청 완료율 / 총점 / 콤보 / 타이핑 정확도
- GPT 기반 전체 내용 구조화 요약 자동 생성

---

## 🌿 브랜치 전략

```
upstream (CSID-DGU)
├── main     ← 최종 배포용
└── dev      ← 통합 브랜치 (기본 브랜치)

origin (개인 fork)
├── main
├── dev
└── feat/기능명  ← 작업 브랜치
```

### 작업 흐름

```bash
git checkout dev
git pull upstream dev
git checkout -b feat/기능명
# 작업 후
git push origin feat/기능명
# GitHub에서 upstream/dev 로 PR
```

---

## 👩‍💻 팀원

| 역할 | 이름 |
|------|------|
| Backend | 임수빈 |
| AI | 김연비 |

---

## 📄 커밋 컨벤션

| 타입 | 설명 |
|------|------|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `chore` | 설정, 의존성 등 기타 작업 |
| `docs` | 문서 수정 |
| `refactor` | 리팩토링 |
| `test` | 테스트 코드 |
