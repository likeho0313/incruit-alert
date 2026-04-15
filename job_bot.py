import requests
import json
import os

# 1. 설정
# GitHub Secrets에 등록했다면 os.getenv를 사용하고, 로컬 테스트라면 문자열을 직접 넣으세요.
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1493827941841371156/jKY0kA7PSDw9Gj4fqh-7g3Isowoza2aIYs_j2ZSrsqcigFYnfoErdzX2zVEfxqako77A')

# 감시할 키워드 리스트 (여기에 원하는 키워드를 계속 추가하세요)
KEYWORDS = ["파이썬", "Python", "백엔드", "Backend", "데이터 엔지니어", "신입"]

CHECK_FILE = 'last_jobs.json'

def get_wanted_jobs(search_keyword):
    """원티드 API를 통해 특정 키워드로 검색된 공고를 가져옵니다."""
    url = f"https://www.wanted.co.kr/api/v4/search?job_sort=job.latest_order&locations=all&years=-1&query={search_keyword}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('data', {}).get('jobs', [])
    except Exception as e:
        print(f"API 요청 중 오류 발생 ({search_keyword}): {e}")
    return []

def send_discord_message(job, matched_keyword):
    """조건에 맞는 공고를 디스코드로 전송합니다."""
    payload = {
        "embeds": [{
            "title": f"✨ 새 공고 발견! (키워드: {matched_keyword})",
            "description": f"**직무:** {job['position']}\n**회사:** {job['company']['name']}\n**지역:** {job['address']['location']}",
            "url": f"https://www.wanted.co.kr/wd/{job['id']}",
            "color": 5814783 # 연보라색
        }]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def main():
    # 이전에 보낸 공고 ID 불러오기
    if os.path.exists(CHECK_FILE):
        with open(CHECK_FILE, 'r') as f:
            try:
                sent_jobs = json.load(f)
            except:
                sent_jobs = []
    else:
        sent_jobs = []

    current_iteration_jobs = [] # 이번 실행에서 확인한 모든 ID 저장용
    new_found_count = 0

    # 각 키워드별로 검색 실행
    for search_term in KEYWORDS:
        print(f"검색 중: {search_term}...")
        jobs = get_wanted_jobs(search_term)
        
        for job in jobs:
            job_id = job['id']
            job_title = job['position']
            
            # 중복 검사 (이미 이번 실행에서 처리했거나 이전에 보낸 경우 제외)
            if job_id in sent_jobs or job_id in current_iteration_jobs:
                continue

            # 공고명에 키워드 리스트 중 하나라도 포함되어 있는지 확인 (대소문자 무시)
            # 원티드 API 검색 결과라 이미 관련이 있겠지만, 한 번 더 필터링합니다.
            matched = [k for k in KEYWORDS if k.lower() in job_title.lower()]
            
            if matched:
                send_discord_message(job, matched[0])
                print(f"알림 전송 성공: {job_title}")
                new_found_count += 1
                current_iteration_jobs.append(job_id)
                
                # 너무 많은 알림 방지 (한 번 실행에 최대 10개까지만)
                if new_found_count >= 10:
                    break
        
        if new_found_count >= 10:
            break

    # 최신 상태 업데이트 (기존 ID + 새로 발견된 ID 유지)
    updated_jobs = list(set(sent_jobs + current_iteration_jobs))[-100:] # 최근 100개만 유지
    with open(CHECK_FILE, 'w') as f:
        json.dump(updated_jobs, f)

if __name__ == "__main__":
    main()
