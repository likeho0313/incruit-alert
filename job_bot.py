import requests
import json
import os
import urllib.parse

# 1. 설정
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
# 테스트를 위해 범용적인 키워드 위주로 설정
KEYWORDS = ["파이썬", "Python", "백엔드", "Backend", "신입"]
CHECK_FILE = 'last_jobs.json'

def get_wanted_jobs(search_keyword):
    """원티드 API를 사용하여 공고를 가져옵니다."""
    # 키워드 인코딩
    encoded_keyword = urllib.parse.quote(search_keyword)
    
    # 필수 파라미터 포함 (v4/jobs 엔드포인트가 더 안정적입니다)
    url = (
        f"https://www.wanted.co.kr/api/v4/jobs?"
        f"country=kr&"
        f"tag_type_ids=518&"  # 개발 카테고리 (필요시 제거 가능)
        f"locations=all&"
        f"years=-1&"
        f"limit=20&"
        f"offset=0&"
        f"job_sort=job.latest_order&"
        f"query={encoded_keyword}"
    )
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.wanted.co.kr/search",
        "Origin": "https://www.wanted.co.kr"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"[{search_keyword}] API 요청 결과: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('data', [])
            # 'v4/jobs'는 data 자체가 리스트인 경우가 많습니다.
            if isinstance(jobs, list):
                print(f"가져온 공고 수: {len(jobs)}개")
                return jobs
        else:
            print(f"에러 응답: {response.text}") # 422 발생 시 상세 이유 확인용
    except Exception as e:
        print(f"API 요청 중 예외 발생: {e}")
    return []

def send_discord_message(job, matched_keyword):
    """디스코드 알림 전송"""
    if not DISCORD_WEBHOOK_URL:
        print("에러: DISCORD_WEBHOOK_URL이 없습니다.")
        return

    # 공고 정보 추출
    job_title = job.get('position', '제목 없음')
    company_name = job.get('company', {}).get('name', '회사명 없음')
    job_id = job.get('id')
    location = job.get('address', {}).get('location', '지역 미상')

    payload = {
        "embeds": [{
            "title": f"🚀 새 채용 공고: {job_title}",
            "description": f"**🏢 회사:** {company_name}\n**📍 지역:** {location}\n**🔍 매칭 키워드:** {matched_keyword}",
            "url": f"https://www.wanted.co.kr/wd/{job_id}",
            "color": 3447003
        }]
    }
    res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print(f"디스코드 전송 상태: {res.status_code}")

def main():
    # 1. 기존 데이터 로드
    if os.path.exists(CHECK_FILE):
        with open(CHECK_FILE, 'r') as f:
            try:
                sent_jobs = json.load(f)
            except:
                sent_jobs = []
    else:
        sent_jobs = []

    new_jobs_found = []
    
    # 2. 키워드 순회하며 공고 찾기
    for kw in KEYWORDS:
        jobs = get_wanted_jobs(kw)
        if not jobs:
            continue
            
        for job in jobs:
            job_id = job.get('id')
            job_title = job.get('position', '')

            # 이미 보낸 공고이거나 이번 실행에서 찾은 거면 패스
            if not job_id or job_id in sent_jobs or job_id in new_jobs_found:
                continue

            # 제목에 키워드가 포함되는지 최종 확인
            if any(k.lower() in job_title.lower() for k in KEYWORDS):
                send_discord_message(job, kw)
                new_jobs_found.append(job_id)
                # 너무 많은 알림 방지
                if len(new_jobs_found) >= 10:
                    break
        if len(new_jobs_found) >= 10:
            break

    # 3. 새로운 ID 저장
    final_ids = list(set(sent_jobs + new_jobs_found))[-200:] # 최근 200개 유지
    with open(CHECK_FILE, 'w') as f:
        json.dump(final_ids, f)
    
    print(f"--- 실행 완료: 새 공고 {len(new_jobs_found)}개 처리됨 ---")

if __name__ == "__main__":
    main()
