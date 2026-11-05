"""
Uman 게시판 모니터링 및 디스코드/텔레그램 알림 봇
개선 사항:
1. BeautifulSoup 파싱 실패 시 방어 로직 강화
2. 세션(requests.Session) 재사용으로 네트워크 핸드셰이크 지연 단축
3. 텔레그램 알림 옵션 지원
4. 중복 ID 기록 최대 300건 보존
"""

import requests
import json
import os
import urllib.parse
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

UMAN_URL = "https://www.uman.kr/board/?id=talk4"
CHECK_FILE = 'last_posts.json'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def get_uman_posts():
    posts = []
    try:
        session = requests.Session()
        res = session.get(UMAN_URL, headers=HEADERS, timeout=(5, 10))
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select('tr.list_table_tr')
            for row in rows:
                title_tag = row.select_one('td.subject a')
                if not title_tag:
                    continue
                
                title = title_tag.get_text(strip=True)
                href = title_tag.get('href', '')
                if not href:
                    continue

                link = "https://www.uman.kr" + href if href.startswith('/') else href
                parsed = urllib.parse.urlparse(link)
                qs = urllib.parse.parse_qs(parsed.query)
                post_id = qs.get('no', [None])[0]

                if post_id:
                    posts.append({'id': post_id, 'title': title, 'link': link})
    except Exception as e:
        print(f"[Uman] 게시판 크롤링 오류: {e}")
    return posts

def send_alert(post):
    # 1. 디스코드 전송
    if DISCORD_WEBHOOK_URL:
        payload = {
            "embeds": [{
                "title": "📝 유맨 새 게시글 등록",
                "description": f"**제목:** {post['title']}",
                "url": post['link'],
                "color": 15844367, # 골드/오렌지
                "footer": {"text": "Uman Community Alert"}
            }]
        }
        try:
            requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        except Exception as e:
            print(f"[Uman] 디스코드 발송 실패: {e}")

    # 2. 텔레그램 전송
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"📝 <b>유맨 새 게시글</b>\n\n{post['title']}",
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [[{"text": "게시글 보기", "url": post['link']}]]
            }
        }
        try:
            requests.post(tg_url, json=payload, timeout=5)
        except Exception as e:
            print(f"[Uman] 텔레그램 발송 실패: {e}")

def main():
    sent_posts = []
    if os.path.exists(CHECK_FILE):
        try:
            with open(CHECK_FILE, 'r', encoding='utf-8') as f:
                sent_posts = json.load(f)
        except:
            sent_posts = []

    new_posts = []
    posts = get_uman_posts()
    
    for post in posts:
        if post['id'] not in sent_posts:
            send_alert(post)
            new_posts.append(post['id'])

    final_ids = list(dict.fromkeys(sent_posts + new_posts))[-300:]
    with open(CHECK_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_ids, f, ensure_ascii=False, indent=2)

    print(f"[Uman] 실행 완료: 새 게시글 {len(new_posts)}건 처리")

if __name__ == "__main__":
    main()
