import os, json, re
from datetime import datetime, timezone
import requests

KEYWORD = "무역협회"
NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"

STATE_DIR = ".state"
STATE_FILE = os.path.join(STATE_DIR, "state.json")

def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").replace("&quot;", "\"").replace("&amp;", "&")

def load_state():
    os.makedirs(STATE_DIR, exist_ok=True)
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_pubdate": None}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def parse_pubdate(pubdate_str: str) -> datetime:
    # 예: "Mon, 15 Dec 2025 12:34:56 +0900"
    return datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")

def fetch_news():
    headers = {
        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"],
        "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"],
    }
    params = {
        "query": KEYWORD,
        "display": 20,
        "start": 1,
        "sort": "date",  # 최신순
    }
    r = requests.get(NAVER_NEWS_URL, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("items", [])

def send_telegram(text: str):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False,
    }
    r = requests.post(url, data=payload, timeout=20)
    r.raise_for_status()

def main():
    state = load_state()
    last_pub = state["last_pubdate"]
    last_dt = parse_pubdate(last_pub) if last_pub else None

    items = fetch_news()

    new_items = []
    for it in items:
        pub = parse_pubdate(it["pubDate"])
        if last_dt is None or pub > last_dt:
            new_items.append((pub, it))

    # 오래된 것부터 보내기(읽기 좋게)
    new_items.sort(key=lambda x: x[0])

    if not new_items:
        print("No new items.")
        return

    # 텔레그램 전송
    for pub, it in new_items:
        title = strip_html(it.get("title", ""))
        desc = strip_html(it.get("description", ""))
        link = it.get("originallink") or it.get("link") or ""
        msg = f"[{KEYWORD}] {title}\n{pub.strftime('%Y-%m-%d %H:%M:%S %z')}\n{link}\n\n{desc}"
        send_telegram(msg)

    # 가장 최신 pubDate 저장
    newest_pub = new_items[-1][1]["pubDate"]
    state["last_pubdate"] = newest_pub
    save_state(state)
    print(f"Sent {len(new_items)} items. Updated last_pubdate={newest_pub}")

if __name__ == "__main__":
    main()
