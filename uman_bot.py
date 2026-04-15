import requests
import json
import os
import urllib.parse
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
UMAN_URL = "https://www.uman.kr/board/?id=talk4"
CHECK_FILE = 'last_posts.json'

def get_uman_posts():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    posts = []
    try:
        res = requests.get(UMAN_URL, headers=headers)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # 유맨 게시판 구조에 따른 선택자
            rows = soup.select('tr.list_table_tr')
            for row in rows:
                title_tag = row.select_one('td.subject a')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = "https://www.uman.kr" + title_tag['href']
                    # 주소에서 no=1234 추출
                    post_id = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get('no', [None])[0]
                    if post_id:
                        posts.append({'id': post_id, 'title': title, 'link': link})
    except: pass
    return posts

def main():
    if os.path.exists(CHECK_FILE):
        with open(CHECK_FILE, 'r') as f:
            try: sent_posts = json.load(f)
            except: sent_posts = []
    else: sent_posts = []

    new_posts = []
    posts = get_uman_posts()
    
    for post in posts:
        if post['id'] not in sent_posts:
            payload = {"embeds": [{"title": f"📝 유맨 새 게시글", "description": f"**제목:** {post['title']}", "url": post['link'], "color": 15844367}]}
            requests.post(DISCORD_WEBHOOK_URL, json=payload)
            new_posts.append(post['id'])

    with open(CHECK_FILE, 'w') as f:
        json.dump((sent_posts + new_posts)[-200:], f)

if __name__ == "__main__":
    main()
