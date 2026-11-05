"""
Wanted 채용 공고 멀티채널 자동 알림 봇 (Discord 2.0 + Telegram 지원)
개선 사항:
1. 뱃치 전송(Batching): 여러 공고가 한 번에 떠도 단 1회 웹훅 요청으로 묶어 429 Rate Limit 방지
2. 제외 키워드(EXCLUDE_KEYWORDS): '경비', '주차' 등 원치 않는 무관 공고 필터링
3. 텔레그램(Telegram) 동시 지원: 폰에서 소리 나는 즉각 푸시 알림 수신
4. 안전한 타임아웃 및 예외 처리: requests에 timeout=(5, 10) 적용
5. 리치 임베드: 회사명, 보상금, 태그, 직무 상세 링크 포맷팅
"""

import requests
import json
import os
import time
import urllib.parse
from typing import List, Dict, Any

# ==================== [환경설정] ====================
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') # 선택사항 (없으면 디스코드만 전송)
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')     # 선택사항

# 모니터링할 핵심 키워드
KEYWORDS = ["정규", "전산", "보안", "개발", "의료원"]

# 제외할 노이즈 키워드 (오탐지 방지)
EXCLUDE_KEYWORDS = ["단기알바", "경비", "청소", "주차관리", "단순노무"]

CHECK_FILE = 'last_jobs.json'

# 원티드 직무 태그 (개발 전체 518, 의료 515, 보안 10566, 전산/교육 10101, 물류 532)
TAG_IDS = [515, 518, 10566, 10101, 532]
TAG_PARAMS = "&".join([f"tag_type_ids={tid}" for tid in TAG_IDS])

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.wanted.co.kr/search",
    "Origin": "https://www.wanted.co.kr"
}

def get_wanted_jobs(search_keyword: str) -> List[Dict[str, Any]]:
    """원티드 v4 API를 호출하여 최신 공고를 조회합니다."""
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
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=(5, 10))
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('data', [])
            if isinstance(jobs, list):
                return jobs
        else:
            print(f"[{search_keyword}] API 응답 코드 {response.status_code}: {response.text[:120]}")
    except requests.exceptions.RequestException as e:
        print(f"[{search_keyword}] API 요청 실패: {e}")
    return []

def send_discord_batch(new_jobs: List[Dict[str, Any]]):
    """
    디스코드 2.0: 여러 공고를 최대 10개씩 묶어(Batch) 전송하여
    Rate Limit(429)을 방지하고 채널 도배를 막습니다.
    """
    if not DISCORD_WEBHOOK_URL:
        print("[Discord] DISCORD_WEBHOOK_URL이 설정되지 않아 전송을 건너뜁니다.")
        return

    # 디스코드는 1회 요청당 최대 10개의 embeds를 지원합니다
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
                    "text": "Wanted Job Alert Bot • GitHub Actions 자동 알림"
                }
            })

        payload = {
            "content": f"📢 **원티드에 신규 채용 공고 {len(chunk)}건이 등록되었습니다!**" if i == 0 else None,
            "embeds": embeds
        }

        try:
            res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            print(f"[Discord] 전송 상태: {res.status_code} ({len(chunk)}건)")
            time.sleep(1) # 연속 요청 시 짧은 딜레이
        except Exception as e:
            print(f"[Discord] 전송 오류: {e}")

def send_telegram_alert(new_jobs: List[Dict[str, Any]]):
    """
    텔레그램 알림 전송 (인라인 키보드 버튼 탑재):
    스마트폰에서 즉각적인 소리/진동 푸시를 제공합니다.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

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

    # 3. 알림 전송 (디스코드 뱃치 + 텔레그램)
    if new_items_to_send:
        print(f"새로운 매칭 공고 {len(new_items_to_send)}건 발견. 알림을 발송합니다.")
        send_discord_batch(new_items_to_send)
        send_telegram_alert(new_items_to_send)
    else:
        print("새로운 매칭 공고가 없습니다.")

    # 4. 최근 300개 기록 유지 저장
    final_ids = list(dict.fromkeys(sent_jobs + new_jobs_found))[-300:]
    with open(CHECK_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_ids, f, ensure_ascii=False, indent=2)

    print(f"--- 실행 완료: 신규 {len(new_jobs_found)}건 기록 완료 ---")

if __name__ == "__main__":
    main()
