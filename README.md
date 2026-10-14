# NEIS 학교 정보 Discord 봇

나이스 교육정보 개방 포털의 학교 정보, 초·중·고 시간표, 학사일정을 조회하는 한국어 Discord 봇입니다. `discord.py` 2.x의 슬래시 명령과 비동기 `aiohttp` 요청을 사용합니다. 모든 NEIS API는 환경변수 `NEIS_API_KEY` 하나로 호출합니다.


## 주요 기능

- 학교명으로 NEIS 학교 검색, 학교급·주소·학교 코드로 결과 선택
- 사용자별 학교·학년·반 통합 설정 UI
- 오늘·내일·주간·지정 날짜 시간표와 이전/다음 날짜 버튼
- 지정 날짜 및 이번 달 학사일정 조회
- 학교 기본정보와 홈페이지 조회
- 서버 응답은 Ephemeral, 개인 DM 응답은 일반 DM 메시지로 표시
- 사용자 ID 기준 SQLite 설정 저장: 서버와 DM에서 같은 사용자 설정 공유
- NEIS 오류 처리, 페이지네이션, 제한된 네트워크 재시도

## 사용하는 NEIS API

| 용도 | 엔드포인트 |
| --- | --- |
| 학교 기본정보 | `schoolInfo` |
| 초등학교 시간표 | `elsTimetable` |
| 중학교 시간표 | `misTimetable` |
| 고등학교 시간표 | `hisTimetable` |
| 학사일정 | `SchoolSchedule` |

다섯 API 모두 `NEIS_API_KEY` 한 개를 사용합니다. 요청 형식은 JSON이며 페이지 조회에는 `pIndex`와 `pSize`를 사용합니다.

## 명령어

| 명령어 | 설명 |
| --- | --- |
| `/설정` | 학교·학년·반을 검색하고 저장하는 통합 설정 UI |
| `/학교정보` | 내 학교 주소, 교육청, 코드, 공식 홈페이지 |
| `/시간표` | 오늘 시간표와 날짜 이동 버튼 |
| `/내일시간표` | 내일 시간표 |
| `/주간시간표` | 이번 주 월요일~금요일 시간표 |
| `/날짜시간표 날짜` | 지정 날짜 시간표 (`YYYY-MM-DD`) |
| `/오늘일정` | 오늘 학사일정 |
| `/학사일정` | 이번 달 학사일정 |
| `/월간일정` | 이번 달 학사일정 별칭 |
| `/날짜일정 날짜` | 지정 날짜 학사일정 (`YYYY-MM-DD`) |

시간표는 NEIS의 실제 응답을 교시 순서대로 세로 표시합니다. 1~8교시의 미등록 교시는 `-`로 나타내며 9교시 이후 실제 데이터도 표시합니다. NEIS 데이터가 없는 경우 가짜 수업이나 행사를 만들지 않습니다.

## 통합 설정 UI

1. `/설정`을 실행합니다.
2. **학교 검색 및 선택**을 눌러 학교명을 입력합니다.
3. 학교명, 학교급, 주소 및 코드가 표시된 검색 결과에서 학교를 선택합니다.
4. 학교급에 맞는 학년(초등학교 1~6, 중·고등학교 1~3)을 고릅니다.
5. 반 선택에서 1~50 사이의 반 번호를 입력합니다.
6. **설정 저장하기**를 눌러 저장합니다. 저장 전 임시 선택은 데이터베이스에 반영되지 않습니다.

설정 메시지는 서버에서 명령 실행자에게만 보이는 Ephemeral 메시지로, DM에서는 일반 DM 메시지로 표시됩니다. 화면의 버튼과 학교 선택은 명령 실행자만 조작할 수 있습니다.

## 개인 DM 사용 설정

1. Discord Developer Portal에서 애플리케이션을 선택하고 **Installation** 페이지를 엽니다.
2. **Installation Contexts**에서 **Guild Install**과 **User Install**을 모두 활성화합니다.
3. Guild Install에는 `bot`과 `applications.commands` 스코프를 설정합니다. User Install에는 `applications.commands` 스코프를 설정하고 사용자 설치를 활성화합니다.
4. 생성된 설치 링크를 이용해 서버에 봇을 설치하거나 개인 계정에 앱을 설치합니다.
5. 봇과 DM을 열고 `/설정`을 한 번 실행해 학교·학년·반을 저장합니다.
6. 이후 DM에서 `/시간표`, `/주간시간표`, `/학사일정`, `/학교정보`를 사용할 수 있습니다.

모든 설정은 Discord 사용자 ID를 기준으로 저장됩니다. 따라서 같은 사용자는 서버와 개인 DM에서 같은 학교 및 학급 설정을 사용합니다.

## 설치 및 실행

요구 사항: Python 3.11 이상.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python bot.py
```

`python bot.py`를 실행하기 전에 `.env`에 아래 두 값을 입력합니다. `.env.example`은 빈 템플릿이며 실제 키를 포함하지 않습니다.

```dotenv
DISCORD_TOKEN=
NEIS_API_KEY=
```

### Discord Bot Token 발급

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 애플리케이션을 만들거나 선택합니다.
2. **Bot** 페이지에서 봇 사용자를 추가하고 Bot Token을 발급합니다.
3. Bot Token을 `DISCORD_TOKEN` 값으로 로컬 `.env`에 입력합니다.
4. 토큰을 소스코드, 공개 저장소, 이슈 또는 채팅에 올리지 마세요. 노출된 토큰은 Developer Portal에서 재설정하세요.

### NEIS API Key 발급

1. [나이스 교육정보 개방 포털](https://open.neis.go.kr/)에서 이용 신청 및 인증키 발급 절차를 진행합니다.
2. 발급된 단일 인증키를 로컬 `.env`의 `NEIS_API_KEY` 값으로 설정합니다.
3. 해당 키 하나가 학교정보, 초·중·고 시간표, 학사일정 요청 전체에 사용됩니다.

## 프로젝트 구조

```text
github-release/
├── bot.py
├── config.py
├── database.py
├── services/
│   ├── __init__.py
│   ├── neis.py
│   ├── timetable.py
│   └── schedule.py
├── cogs/
│   ├── __init__.py
│   ├── common.py
│   ├── school.py
│   ├── timetable.py
│   └── schedule.py
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

실행 시 `bot.db`가 생성되며 `.gitignore`에서 제외됩니다. 데이터베이스에는 사용자별 학교명, 학교급, 교육청 코드, 학교 코드, 학년 및 반이 저장됩니다.

## 테스트

```powershell
python -m unittest discover -s tests -v
```

테스트는 NEIS 응답/페이지네이션, 단일 인증키 전달, 사용자별 데이터 저장, 설정 UI, Discord 설치 컨텍스트, 시간표 형식을 확인합니다. 실제 Discord 및 NEIS 계정으로 수행하는 온라인 연동 테스트는 포함하지 않습니다.

## 문제 해결

- **필수 환경변수가 없습니다**: 프로젝트 폴더에서 `.env.example`을 `.env`로 복사하고 두 값을 입력했는지 확인합니다.
- **Discord 401 / Improper token**: Developer Portal의 Bot 페이지에서 토큰을 재설정하고 새 `DISCORD_TOKEN`을 사용합니다.
- **명령어가 안 보입니다**: 봇을 `applications.commands` 스코프로 설치했는지 확인합니다. 전역 슬래시 명령어는 반영에 시간이 걸릴 수 있습니다.
- **DM에서 명령어가 안 보입니다**: Developer Portal의 User Install 및 `applications.commands` 설정을 확인하고, 사용자 계정에 앱을 설치했는지 확인합니다.
- **NEIS 인증 오류 또는 결과 없음**: 키 발급/사용 권한, 학교명, 학교 코드 및 NEIS에 해당 날짜 자료가 있는지 확인합니다.
- **연결 시간 초과 또는 서버 오류**: 봇은 제한된 횟수만 재시도합니다. 잠시 후 다시 요청해 주세요.

## 데이터 출처 및 주의사항

학교정보·시간표·학사일정은 [나이스 교육정보 개방 포털](https://open.neis.go.kr/)에서 요청 시 조회합니다. 자료 제공 여부와 시점은 NEIS 운영 상태 및 학교의 데이터 등록 상황에 따릅니다.

이 프로젝트는 Discord 또는 교육 당국의 공식 제품이 아닙니다. `.env`, 데이터베이스, 로그 등 민감하거나 사용자 정보가 포함될 수 있는 파일은 공개 저장소에 올리지 마세요. `.gitignore`는 이미 Git에 추적된 파일이나 기존 커밋 기록에서 해당 파일을 제거하지 않으므로, 실수로 공개한 키는 재발급하고 Git 기록은 별도로 점검해야 합니다.

이 봇의 일부 코드는 생성형 AI를 활용하여 작성되었습니다.
