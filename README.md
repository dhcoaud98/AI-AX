# AI-AX: 뒤처지지 않기 위한 나만의 AI 뉴스룸

AX·AI·기업교육 소식을 **매일 자동으로 받아 보고**, **궁금할 때 AI에게 직접 물어볼 수 있도록** 만든 저장소입니다.

| 작업 | 한 마디 정의 | 비유 |
|---|---|---|
| 데일리 브리핑 (예약 작업) | 매일 아침 AX·AI·기업교육 소식을 요약해 자동으로 쌓는 브리핑 | 📬 신문 배달 |
| MCP 6단계 뉴스 도구 | 궁금할 때 AI에게 최신 소식을 물어볼 수 있게 해 주는 뉴스 도구 | 📰 신문 가판대 |

---

## 📬 데일리 브리핑 → [`briefings/`](briefings/)

매일 아침 8시 45분(한국 시간), Claude 예약 작업이 웹에서 소식을 모아 요약한 뒤 이 저장소에 올립니다.

- **영역:** 🤖 AI·개발 / 🏢 AX 기업 / 🎓 기업교육
- **형식:** 소식마다 요약 2~3문장 + **"→ 나에게 의미"** 한 줄 + 출처 링크
- **위치:** `briefings/YYYY/MM/YYYY-MM-DD.md`
- **목록:** [briefings/README.md](briefings/README.md)

```
매일 08:45 → Claude 예약 작업(클라우드) → 웹 검색 → 브리핑 작성 → 이 저장소에 커밋·푸시
```

컴퓨터가 꺼져 있어도 클라우드에서 실행됩니다.

---

## 📰 MCP 뉴스 도구 → [`mcp-class/`](mcp-class/)

MCP 입문 강의 실습 서버입니다. AI에게 도구를 하나씩 달아 주며 MCP를 배우고, 6단계에서 최신 뉴스를 가져오는 도구를 만듭니다.

| 단계 | 도구 | AI가 원래 못 하는 것 |
|---|---|---|
| 1 ⏰ 시계 | `now`, `d_day` | 지금이 언제인지 모름 |
| 2 🎲 주사위 | `roll_dice`, `pick_one` | 진짜 무작위를 못 만듦 |
| 3 📝 메모장 | `save_note`, `list_notes` | 새 채팅을 열면 잊어버림 |
| 4 📊 성적표 | `students://all`, `subject_average`, `students_above` | 내 컴퓨터 파일을 모름 |
| 5 🌤 날씨 | `weather` | 바깥 날씨를 모름 |
| **6 📰 뉴스** | **`latest_news`** | **오늘 나온 소식을 모름** |

**핵심:** 도구는 뉴스 제목과 링크만 **가져오고**, 고르고 요약하고 해석하는 건 **AI가** 합니다.

### 실행하기

```bash
cd mcp-class
uv sync
uv run test_client.py        # 도구 10개 자동 테스트
uv run mcp dev server.py     # 브라우저에서 도구 하나씩 눌러 보기
```

Claude Desktop 연결 방법과 수업 진행 순서는 [강의안](mcp-class/강의안.md)을 참고하세요.

---

## 👥 HR 관점으로 넓히기

HRD(사람을 키우는 일)에서 HR(뽑고, 배치하고, 평가하고, 보상하고, 지키는 일)로 공부 범위를 넓히는 두 서버입니다. mcp-class와 같은 구조라 따로 실행하고 따로 연결합니다.

| 서버 | 한 마디 정의 | mcp-class에서 이어지는 단계 |
|---|---|---|
| [`hr-analytics/`](hr-analytics/) | 인사 데이터를 **집계만** 보여 주는 피플 애널리틱스 서버 | 4단계 📊 성적표 + 3단계 🔒 보안 |
| [`hr-news/`](hr-news/) | 노무·채용 AI·인사제도 뉴스를 매일 읽고 공부노트에 쌓는 서버 | 6단계 📰 뉴스 |

- **hr-analytics 핵심:** AI가 무엇을 볼 수 있는지는 프롬프트가 아니라 **도구 설계**가 정한다. 개인 단위 결과 없음, 3명 미만 집단 숨김, 모든 조회 기록.
- **hr-news 핵심:** 도구가 신문을 가져다주고, Claude가 골라 읽어 주고, 나는 "나에게 의미" 한 줄만 남긴다.

```bash
cd hr-analytics   # 또는 hr-news
uv sync
uv run test_client.py
```

---

## 폴더 구조

```
AI-AX/
├── README.md            ← 지금 보는 파일
├── briefings/           ← 📬 데일리 브리핑 (매일 자동 추가)
│   ├── README.md
│   └── 2026/10/2026-10-19.md ...
├── mcp-class/           ← 📰 MCP 강의 실습 서버
│   ├── 강의안.md
│   ├── server.py
│   ├── test_client.py
│   ├── students.csv
│   └── pyproject.toml
├── hr-analytics/        ← 👥 피플 애널리틱스 + 개인정보 보호
│   ├── README.md
│   ├── server.py
│   ├── employees.csv    ← 가짜 직원 데이터
│   └── test_client.py
└── hr-news/             ← 👥 HR 뉴스 (노무·채용 AI·인사제도)
    ├── README.md
    ├── server.py
    └── test_client.py
```
