# 🚀 Wanted & Uman 채용 공고 멀티채널 자동 알림 봇

원하는 직무와 키워드의 채용 공고가 **원티드(Wanted)**와 **유만(Uman)**에 새로 올라오면, **디스코드(Discord)**와 **텔레그램(Telegram)**으로 실시간 알림을 보내주는 자동화 봇입니다.

원티드 API의 클라우드 IP 차단(`403`) 이슈에 유연하게 대응할 수 있도록 **1) GitHub Actions (서버리스)** 방식과 **2) 로컬 PC (작업 스케줄러)** 방식을 모두 지원합니다.

---

## ✨ 주요 기능
- **멀티 채널 동시 지원**: 푸시 알림이 즉각적인 **텔레그램**과 리치 임베디드가 예쁜 **디스코드**로 동시에 알림 수신
- **디스코드 뱃치 전송(Batching)**: 최대 10개씩 묶어서(Embeds 뱃치) 전송하여 `429 Rate Limit` 및 채널 도배 방지
- **제외 키워드(EXCLUDE_KEYWORDS) 필터링**: '경비', '주차' 등 원치 않는 무관 공고를 원천 차단
- **중복 알림 방지**: `last_jobs.json`에 최근 처리된 공고 ID를 기록하여 절대 중복 알림 방지

---

## 🛠 공통 사전 설정 (Setup)

1. **텔레그램 봇 생성 (선택)**: `@BotFather`를 통해 토큰 발급 및 Chat ID 확인
2. **디스코드 웹훅 생성**: 알림을 받을 채널 설정 ➡️ 연동 ➡️ 웹훅 URL 복사

---

## ⚙️ 환경별 실행 방법 (Choose Your Environment)

### [방법 A] GitHub Actions 방식 (서버리스 / 24시간 무료 클라우드)
*주의: 원티드 측에서 깃허브 클라우드 IP를 차단(`403`)할 경우, 로컬 방식으로 전환이 필요할 수 있습니다.*

1. **GitHub Secrets 등록**
    * 본 저장소의 **Settings** > **Secrets and variables** > **Actions** 메뉴로 이동
    * 아래 시크릿 등록:
        * `DISCORD_WEBHOOK_URL`
        * `TELEGRAM_BOT_TOKEN` (선택)
        * `TELEGRAM_CHAT_ID` (선택)
2. **워크플로우 권한 설정**
    * **Settings** > **Actions** > **General** ➡️ **Workflow permissions**에서 **Read and write permissions** 체크 후 저장 (중복 방지 파일 자동 커밋용)
3. **실행 확인**
    * `.github/workflows/main.yml`에 설정된 `cron` 주기에 따라 자동으로 실행됩니다.

---

### [방법 B] 로컬 PC 방식 (Windows 작업 스케줄러 / IP 차단 우회용)
*GitHub Actions에서 403 에러가 발생할 때 내 PC를 활용하여 상시 구동하는 방법입니다.*

1. **패키지 설치**
   로컬 터미널에서 필요한 라이브러리를 설치합니다.
   ```bash
   pip install beautifulsoup4 requests
   ```
2. **환경 변수 설정 (또는 코드 내 직접 입력)**
   로컬 환경에서는 환경변수 대신 `job_bot.py` 상단에 웹훅 주소를 직접 입력해도 무방합니다.
   ```python
   DISCORD_WEBHOOK_URL = "여기에_디스코드_웹훅_주소_입력"
   ```
3. **배치 파일(`run_bot.bat`) 생성**
   프로젝트 루트 폴더에 실행용 배치 파일을 만듭니다.
   ```cmd
   @echo off
   cd /d D:\경로\를\본인\폴더로\수정\incruit-alert
   python job_bot.py
   python uman_bot.py
   exit
   ```
4. **윈도우 작업 스케줄러 등록**
    * 윈도우 검색창에 **'작업 스케줄러'** 실행
    * 우측 **[작업 만들기]** 클릭
    * **[일반]**: 이름 입력 및 '사용자의 로그온 여부와 관계없이 실행' 체크
    * **[트리거]**: '새로 만들기' ➡️ 원하는 반복 주기 설정 (예: 1시간마다 반복)
    * **[동작]**: '새로 만들기' ➡️ 프로그램 시작 ➡️ 위에서 만든 `run_bot.bat` 선택
    * **[확인]**을 눌러 등록 완료

---

## ⚙️ 개인 맞춤 설정 (Customization)

* **키워드 수정 (`job_bot.py`)**:
  ```python
  KEYWORDS = ["전산", "보안", "인프라", "클라우드", "의료원"]
  EXCLUDE_KEYWORDS = ["단기알바", "경비", "청소", "주차관리"]
  ```
* **GitHub Actions 주기 수정 (`.github/workflows/main.yml`)**:
  ```yaml
  on:
    schedule:
      - cron: '0 * * * *' # 매 정각마다 실행
  ```

---

## 📁 파일 구조
- `job_bot.py`: 원티드 API 수집, 필터링 및 멀티채널 전송 코어 로직
- `uman_bot.py`: 유만 채용 공고 크롤링 봇
- `run_bot.bat`: 로컬 윈도우 환경 실행용 배치 파일
- `last_jobs.json`: 중복 알림 방지용 공고 ID 기록 파일
- `.github/workflows/main.yml`: GitHub Actions 자동화 설정 파일

---

## ⚠️ 주의사항
- 원티드 API는 클라우드 IP(GitHub Actions) 대역에서 간헐적으로 차단(`403 Forbidden`)될 수 있습니다. 차단 발생 시 **[방법 B (로컬 방식)]**으로 전환하는 것을 권장합니다.