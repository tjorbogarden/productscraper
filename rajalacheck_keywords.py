import requests
from bs4 import BeautifulSoup
import subprocess
import hashlib
import os
from datetime import datetime

IMESSAGE_RECIPIENT = "0708944644"
LOG_FILE = os.path.expanduser("~/rajalacheck_log.txt")
SEEN_DIR = os.path.expanduser("~/.rajalacheck_seen")
os.makedirs(SEEN_DIR, exist_ok=True)

# 🔧 Lägg till fler URL:er + nyckelord här
URLS_TO_MONITOR = [
    {
        "url": "https://www.rajalaproshop.se/swap-it/begagnade-kameror/begagnade-leica-kameror",
        "keyword": "moms"
    },
    {
        "url": "https://www.rajalaproshop.se/swap-it/begagnade-objektiv/begagnade-sony-objektiv",
        "keyword": "moms"
    },
    # Lägg till fler här...
]

# Hämtar produkter som innehåller nyckelordet
def fetch_matching_products(url, keyword):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        log(f"[{url}] Fel vid hämtning: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    products = soup.find_all("div", class_="product-item-details")

    matches = []
    for p in products:
        text = p.get_text().lower().strip()
        if keyword.lower() in text:
            matches.append(text)
    return matches

# Unikt filnamn för varje URL + keyword
def get_hash_file_for(url, keyword):
    combined = f"{url}|{keyword}".encode()
    h = hashlib.sha256(combined).hexdigest()
    return os.path.join(SEEN_DIR, f"{h}.txt")

# Läser tidigare träffars hashar
def load_seen_hashes(file_path):
    if not os.path.exists(file_path):
        return set()
    with open(file_path, "r") as f:
        return set(line.strip() for line in f)

# Sparar nya träffars hashar
def save_seen_hashes(file_path, hashes):
    with open(file_path, "a") as f:
        for h in hashes:
            f.write(h + "\n")

# Skickar iMessage
def send_imessage(recipient, message):
    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{recipient}" of targetService
        send "{message}" to targetBuddy
    end tell
    '''
    subprocess.run(["osascript", "-e", script])

# Loggar med tidsstämpel
def log(message):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} {message}\n")
    print(f"{timestamp} {message}")

# Behandla en URL+keyword
def check_site(entry):
    url = entry["url"]
    keyword = entry["keyword"]
    hash_file = get_hash_file_for(url, keyword)

    seen = load_seen_hashes(hash_file)
    matches = fetch_matching_products(url, keyword)

    new_matches = []
    new_hashes = []

    for match in matches:
        h = hashlib.sha256(match.encode()).hexdigest()
        if h not in seen:
            new_matches.append(match)
            new_hashes.append(h)

    for match in new_matches:
        msg = f"Ny produkt med '{keyword}' på:\n{url}\n\n{match[:400]}"
        send_imessage(IMESSAGE_RECIPIENT, msg)
        log(f"[{url}] Ny träff skickad:\n{msg}")

    if new_hashes:
        save_seen_hashes(hash_file, new_hashes)
    else:
        log(f"[{url}] Inga nya träffar med '{keyword}'.")

def main():
    for entry in URLS_TO_MONITOR:
        check_site(entry)

if __name__ == "__main__":
    main()

