"""Theo dõi trạng thái Open/Closed của Vietnam Working Holiday Visa (INZ)
và gửi thông báo đẩy qua ntfy khi có thay đổi."""
import html
import json
import os
import re
import sys
import time
import urllib.request
 
URL = "https://www.immigration.govt.nz/visas/vietnam-working-holiday-visa/"
STATE_FILE = "state.json"
TOPIC = os.environ["NTFY_TOPIC"]
 
 
def fetch_page():
    req = urllib.request.Request(
        URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "en-NZ,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")
 
 
def to_lines(raw):
    raw = re.sub(r"(?is)<(script|style).*?</\1>", "", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|section)>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(raw)
    lines = (re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n"))
    return [ln for ln in lines if ln]
 
 
def get_status(lines):
    """Tìm dòng 'Open' hoặc 'Closed' (+ dòng 'This visa will open ...' nếu có)."""
    for i, ln in enumerate(lines):
        if ln in ("Open", "Closed"):
            detail = ""
            if i + 1 < len(lines) and lines[i + 1].startswith("This visa"):
                detail = lines[i + 1]
            return {"status": ln, "detail": detail}
    return {"status": "UNKNOWN", "detail": ""}
 
 
def notify(title, message, priority="high"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,  # chỉ dùng ký tự ASCII trong header
            "Priority": priority,
            "Tags": "bell,new_zealand",
            "Click": URL,
        },
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30).read()
 
 
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return None
 
 
def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
 
 
def handle(previous, current):
    if previous is None:
        notify(
            "NZ visa watcher started",
            f"Bắt đầu theo dõi. Trạng thái hiện tại: {current['status']}. {current['detail']}",
            priority="default",
        )
    elif previous != current:
        if current["status"] == "Open":
            notify(
                "NZ VISA: CONG DA MO!",
                "Cổng Vietnam Working Holiday Visa đã MỞ. Vào đăng ký ngay!",
                priority="urgent",
            )
        elif current["status"] == "Closed":
            notify("NZ visa: cong da DONG", f"Cổng đã đóng. {current['detail']}")
        else:
            notify(
                "NZ visa: trang thay doi",
                "Không đọc được trạng thái Open/Closed (trang có thể đã đổi cấu trúc). "
                "Hãy mở trang kiểm tra thủ công.",
            )
 
 
def main():
    loop_seconds = int(os.environ.get("LOOP_SECONDS", "330"))
    interval = int(os.environ.get("INTERVAL", "20"))
    deadline = time.time() + loop_seconds
    previous = load_state()
 
    while True:
        try:
            current = get_status(to_lines(fetch_page()))
            print(time.strftime("%H:%M:%S"), current, flush=True)
            if previous != current:
                handle(previous, current)
                save_state(current)
                previous = current
        except Exception as exc:
            print("Loi (se thu lai):", exc, file=sys.stderr, flush=True)
        if time.time() + interval >= deadline:
            break
        time.sleep(interval)
 
 
if __name__ == "__main__":
    main()
 
