"""
Wanted 채용 공고 멀티채널 자동 알림 봇 (Discord 2.0 + Telegram 지원)
- 고도화: 신규 공고가 0건일 때도 알림을 받을지 여부(SEND_ZERO_RESULTS) 설정 가능
"""

import requests
import json
import os
import time
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any

# ==================== [환경설정] ====================
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', "https://discord.com/api/webhooks/1493827941841371156/jKY0kA7PSDw9Gj4fqh-7g3Isowoza2aIYs_j2ZSrsqcigFYnfoErdzX2zVEfxqako77A")
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') # 선택사항
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')     # 선택사항

# [NEW] 신규 공고가 0건일 때도 알림 메시지를 보낼 것인가? (True: 보냄, False: 안 보냄)
SEND_ZERO_RESULTS = True  # 평소엔 도배를 막기 위해 False, 테스트 시 True로 변경

# 모니터링할 핵심 키워드
KEYWORDS = ["정규", "전산", "보안", "개발", "의료원",
    # 인프라 & 클라우드
    "인프라", "시스템", "클라우드", "DevOps", "데브옵스", "SRE", "Linux", "리눅스",
    # 보안 & 네트워크
    "정보보안", "보안", "네트워크", "방화벽", "ISMS", "침해사고", "SecOps",
    # DB & 데이터 엔지니어링
    "DBA", "데이터베이스", "PostgreSQL", "Redis", "시계열",
    # 우대 직무명 (공고 제목에 자주 등장)
    "담당자", "엔지니어", "아키텍트"
]

# 제외할 노이즈 키워드 (오탐지 방지)
EXCLUDE_KEYWORDS = ["단기알바", "경비", "청소", "주차관리", "단순노무"]

CHECK_FILE = 'last_jobs.json'

# 원티드 직무 태그 (개발 전체 518, 의료 515, 보안 10566, 전산/교육 10101, 물류 532)
# 시스템,인프라 엔지니어 (태그 ID: 10242 또는 관련 인프라 태그): 서버, 네트워크, 가상화 다루는 직무
# 정보보안 담당자 (태그 ID: 10566): 보안 솔루션, ISMS-P, 인프라 보안
# DevOps / 백엔드 개발자 (태그 ID: 518): 클라우드, 도커, 고성능 서버 개발
# DBA / 데이터 플랫폼 엔지니어 (태그 ID: 10222 등): 대용량 데이터베이스 관리 (석사 논문 역량 활용)
# TAG_IDS = [515, 518, 10566, 10101, 532, 10242, 10222]
# TAG_IDS = [518, 10566, 10242, 10222]
TAG_IDS = []
TAG_PARAMS = "&".join([f"tag_type_ids={tid}" for tid in TAG_IDS])

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.wanted.co.kr/search",
    "Origin": "https://www.wanted.co.kr"
}

def get_wanted_jobs(search_keyword: str) -> List[Dict[str, Any]]:
    """원티드 v4 API를 호출합니다. 타임아웃 발생 시 최대 3번까지 재시도합니다."""
    encoded_keyword = urllib.parse.quote(search_keyword)
    url = (
        f"https://www.wanted.co.kr/api/v4/jobs?"
        f"country=kr&"
        f"{TAG_PARAMS}&"
        f"locations=seoul.all&"
        f"years=-1&"
        f"limit=20&"
        f"offset=0&"
        f"job_sort=job.latest_order&"
        f"query={encoded_keyword}"
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 타임아웃을 (연결 5초, 대기 15초)로 살짝 늘림
            response = requests.get(url, headers=HEADERS, timeout=(5, 15))
            if response.status_code == 200:
                data = response.json()
                jobs = data.get('data', [])
                if isinstance(jobs, list):
                    return jobs
            else:
                print(f"[{search_keyword}] API 응답 코드 {response.status_code}: {response.text[:120]}")
                break # 200이 아닌 다른 에러면 재시도 안 함
        except requests.exceptions.RequestException as e:
            print(f"[{search_keyword}] API 요청 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2) # 2초 대기 후 재시도
            else:
                print(f"[{search_keyword}] 최대 재시도 횟수 초과. 이번 조회를 건너뜁니다.")
    return []

def send_discord_batch(new_jobs: List[Dict[str, Any]], is_zero: bool = False):
    """
    디스코드 2.0: 공고 목록 전송 또는 0건 리포트 전송
    """
    if not DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URL == "여기에_디스코드_웹훅_주소_직접입력_가능":
        print("[Discord] DISCORD_WEBHOOK_URL이 올바르게 설정되지 않았습니다.")
        return

    # 신규 공고가 0건이고, 0건 리포트 전송 옵션이 켜져있을 때
    if is_zero:
        payload = {
            "content": f"💤 **[원티드 채용 봇]** {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준, 추가된 신규 매칭 공고가 없습니다."
        }
        try:
            res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            print(f"[Discord] 0건 알림 전송 상태: {res.status_code}")
        except Exception as e:
            print(f"[Discord] 전송 오류: {e}")
        return

    # 일반 신규 공고 뱃치 전송
    chunk_size = 10
    for i in range(0, len(new_jobs), chunk_size):
        chunk = new_jobs[i:i + chunk_size]
        embeds = []

        for item in chunk:
            job = item['job']
            keyword = item['keyword']
            job_id = job.get('id')
            job_title = job.get('position', '제목 없음')
            company = job.get('company', {}).get('name', '회사명 없음')
            location = job.get('address', {}).get('location', '지역 미상')
            reward = job.get('reward', {}).get('formatted_total', '보상금 정보 없음')

            embeds.append({
                "title": f"🚀 새 채용 공고: {job_title}",
                "description": (
                    f"**🏢 회사:** {company}\n"
                    f"**📍 지역:** {location}\n"
                    f"**💰 보상금:** {reward}\n"
                    f"**🔍 매칭 키워드:** `{keyword}`"
                ),
                "url": f"https://www.wanted.co.kr/wd/{job_id}",
                "color": 3447003, # 원티드 블루
                "footer": {
                    "text": "Wanted Job Alert Bot • Local Scheduler"
                }
            })

        payload = {
            "content": f"📢 **원티드에 신규 채용 공고 {len(chunk)}건이 등록되었습니다!**" if i == 0 else None,
            "embeds": embeds
        }

        try:
            res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            print(f"[Discord] 전송 상태: {res.status_code} ({len(chunk)}건)")
            time.sleep(1)
        except Exception as e:
            print(f"[Discord] 전송 오류: {e}")

def send_telegram_alert(new_jobs: List[Dict[str, Any]], is_zero: bool = False):
    """
    텔레그램 알림 전송 (0건일 때도 대응)
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    if is_zero:
        text = f"💤 <b>[원티드 채용 봇]</b> {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준, 추가된 신규 매칭 공고가 없습니다."
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
        try:
            requests.post(telegram_url, json=payload, timeout=5)
        except Exception as e:
            print(f"[Telegram] 0건 전송 실패: {e}")
        return

    for item in new_jobs:
        job = item['job']
        keyword = item['keyword']
        job_id = job.get('id')
        job_title = job.get('position', '제목 없음')
        company = job.get('company', {}).get('name', '회사명 없음')
        location = job.get('address', {}).get('location', '지역 미상')
        link = f"https://www.wanted.co.kr/wd/{job_id}"

        text = (
            f"🚀 <b>원티드 신규 채용 공고</b>\n\n"
            f"📌 <b>직무:</b> {job_title}\n"
            f"🏢 <b>회사:</b> {company}\n"
            f"📍 <b>지역:</b> {location}\n"
            f"🔍 <b>키워드:</b> #{keyword}"
        )

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "🔗 원티드 공고 바로가기", "url": link}
                    ]
                ]
            }
        }

        try:
            requests.post(telegram_url, json=payload, timeout=5)
            time.sleep(0.5)
        except Exception as e:
            print(f"[Telegram] 전송 실패: {e}")

def main():
    # 1. 기존 발송 목록 로드
    sent_jobs = []
    if os.path.exists(CHECK_FILE):
        try:
            with open(CHECK_FILE, 'r', encoding='utf-8') as f:
                sent_jobs = json.load(f)
        except Exception as e:
            print(f"기존 파일 읽기 실패, 초기화: {e}")
            sent_jobs = []

    new_jobs_found = []
    new_items_to_send = []

    # 2. 키워드별 공고 조회 및 필터링
    for kw in KEYWORDS:
        jobs = get_wanted_jobs(kw)
        for job in jobs:
            job_id = job.get('id')
            job_title = job.get('position', '')

            if not job_id or job_id in sent_jobs or job_id in new_jobs_found:
                continue

            # 제외 키워드 필터링
            if any(bad_kw in job_title for bad_kw in EXCLUDE_KEYWORDS):
                continue

            # 키워드 매칭 재확인
            if any(k.lower() in job_title.lower() for k in KEYWORDS):
                new_jobs_found.append(job_id)
                new_items_to_send.append({'job': job, 'keyword': kw})

    # 3. 알림 전송
    if new_items_to_send:
        print(f"새로운 매칭 공고 {len(new_items_to_send)}건 발견. 알림을 발송합니다.")
        send_discord_batch(new_items_to_send, is_zero=False)
        send_telegram_alert(new_items_to_send, is_zero=False)
    else:
        print("새로운 매칭 공고가 없습니다.")
        # [NEW] 설정이 True일 때만 0건 알림 발송
        if SEND_ZERO_RESULTS:
            send_discord_batch([], is_zero=True)
            send_telegram_alert([], is_zero=True)

    # 4. 최근 300개 기록 유지 저장
    final_ids = list(dict.fromkeys(sent_jobs + new_jobs_found))[-300:]
    with open(CHECK_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_ids, f, ensure_ascii=False, indent=2)

    print(f"--- 실행 완료: 신규 {len(new_jobs_found)}건 기록 완료 ---")

if __name__ == "__main__":
    main()