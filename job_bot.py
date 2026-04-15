import requests
import json
import os

# 설정
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
KEYWORDS = ["파이썬", "Python", "백엔드", "신입"] # 테스트를 위해 잘 잡힐만한 키워드 추가
CHECK_FILE = 'last_jobs.json'

def get_wanted_jobs(search_keyword):
    # 원티드 API 주소 (파라미터 확인)
    url = f"https://www.wanted.co.kr/api/v4/search?job_sort=job.latest_order&locations=all&years=-1&query={search_keyword}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        print(f"API 요청 시도: {search_keyword} -> 상태 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json().get('data', []) # 구조 확인: 원티드 API에 따라 'data' 또는 'data.jobs'
            # API 구조가 변경되었을 수 있으므로 안전하게 가져오기
            jobs = data.get('jobs', []) if isinstance(data, dict) else []
            print(f"가져온 공고 수: {len(jobs)}개")
            return jobs
    except Exception as e:
        print(f"API 요청 중 오류 발생: {e}")
    return []

def send_discord_message(job, matched_keyword):
    if not DISCORD_WEBHOOK_URL:
        print("에러: DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")
        return

    payload = {
        "embeds": [{
            "title": f"🚀 새 공고: {job['position']}",
            "description": f"**회사명:** {job['company']['name']}\n**키워드:** {matched_keyword}",
            "url": f"https://www.wanted.co.kr/wd/{job['id']}",
            "color": 3447003
        }]
    }
    res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print(f"디스코드 전송 결과: {res.status_code}")

def main():
    # 1. 이전 저장 기록 로드
    if os.path.exists(CHECK_FILE):
        with open(CHECK_FILE, 'r') as f:
            try:
                sent_jobs = json.load(f)
            except:
                sent_jobs = []
    else:
        sent_jobs = []

    print(f"기존에 저장된 공고 개수: {len(sent_jobs)}개")

    new_jobs_found = []
    
    for kw in KEYWORDS:
        jobs = get_wanted_jobs(kw)
        for job in jobs:
            job_id = job['id']
            job_title = job.get('position', '')

            # 중복 확인
            if job_id in sent_jobs or job_id in new_jobs_found:
                continue

            # 제목에 키워드 포함 여부 (대소문자 무시)
            # API에서 이미 검색된 결과이므로, 포함 여부 검사를 조금 더 완만하게 처리
            if any(k.lower() in job_title.lower() for k in KEYWORDS):
                send_discord_message(job, kw)
                new_jobs_found.append(job_id)
                if len(new_jobs_found) >= 5: break # 너무 많이 보내지 않게

    # 2. 결과 업데이트
    # 기존 데이터와 새 데이터를 합쳐서 저장
    final_jobs = list(set(sent_jobs + new_jobs_found))[-100:]
    with open(CHECK_FILE, 'w') as f:
        json.dump(final_jobs, f)
    print(f"새로 발견된 공고: {len(new_jobs_found)}개")
    print(f"최종 저장된 공고 ID 개수: {len(final_jobs)}개")

if __name__ == "__main__":
    main()
