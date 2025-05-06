from selenium import webdriver
from selenium.webdriver.safari.options import Options
from bs4 import BeautifulSoup
import hashlib
import os
from datetime import datetime
import subprocess
import time

# Mottagare av iMessage (mobilnummer eller e-post kopplad till iMessage)
IMESSAGE_RECIPIENT = "0708944644"

# Var loggfilen och "sett tidigare"-filer sparas
LOG_FILE = os.path.expanduser("~/productscraper/rajalacheck_log.txt")
SEEN_DIR = os.path.expanduser("~/productscraper/.rajalacheck_seen")
os.makedirs(SEEN_DIR, exist_ok=True)

# 🔍 Lista på sidor + nyckelord att övervaka
URLS_TO_MONITOR = [
    {
        "url": "https://www.rajalaproshop.se/swap-it/begagnade-kameror/begagnade-leica-kameror",
        "keyword": "moms"
    },
    {
        "url": "https://www.rajalaproshop.se/swap-it/begagnade-objektiv/begagnade-sony-objektiv?manufacturer%5B%5D=Sony&lensmounting%5B%5D=Sony%2520FE&p=1&product_list_order=relevance",
        "keyword": "moms"
    },
    # Lägg till fler sidor + nyckelord här vid behov
]

# 📓 Logga till fil + skriv till terminalen
def log(message):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} {message}\n")
    print(f"{timestamp} {message}")

# 💬 Skicka iMessage
def send_imessage(recipient, message):
    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{recipient}" of targetService
        send "{message}" to targetBuddy
    end tell
    '''
    subprocess.run(["osascript", "-e", script])

# 📦 Unik fil för tidigare träffar, baserat på URL + nyckelord
def get_hash_file_for(url, keyword):
    combined = f"{url}|{keyword}".encode()
    h = hashlib.sha256(combined).hexdigest()
    return os.path.join(SEEN_DIR, f"{h}.txt")

# 🔄 Läser tidigare träffars hash
def load_seen_hashes(file_path):
    if not os.path.exists(file_path):
        return set()
    with open(file_path, "r") as f:
        return set(line.strip() for line in f)

# 💾 Spara nya träffars hash
def save_seen_hashes(file_path, hashes):
    with open(file_path, "a") as f:
        for h in hashes:
            f.write(h + "\n")

# 🌐 Ladda sidan med Selenium + sök träffar
def fetch_products_with_selenium(url, keyword):
    driver = webdriver.Safari()  # Safari behöver inga options
    try:
        driver.get(url)
        time.sleep(5)  # ge sidan tid att ladda JS-innehåll

        soup = BeautifulSoup(driver.page_source, "html.parser")
        products = soup.find_all("div", class_="product-item-details")

        matches = []
        for p in products:
            text = p.get_text().strip()
            if keyword.lower() in text.lower():
                matches.append(text)
        return matches

    except Exception as e:
        log(f"[{url}] Fel i selenium: {e}")
        return []
    finally:
        driver.quit()

# 👁 Kontrollera en specifik sida
def check_site(entry):
    url = entry["url"]
    keyword = entry["keyword"]
    hash_file = get_hash_file_for(url, keyword)

    seen = load_seen_hashes(hash_file)
    matches = fetch_products_with_selenium(url, keyword)

    new_matches = []
    new_hashes = []

    for match in matches:
        h = hashlib.sha256(match.encode()).hexdigest()
        if h not in seen:
            new_matches.append(match)
            new_hashes.append(h)

    if matches:
        log(f"[{url}] Totalt {len(matches)} träff(ar) innehåller '{keyword}'")

    for match in new_matches:
        msg = f"Ny produkt med '{keyword}' på:\n{url}\n\n{match[:400]}"
        send_imessage(IMESSAGE_RECIPIENT, msg)
        log(f"[{url}] Skickade iMessage:\n{msg}")

    if new_hashes:
        save_seen_hashes(hash_file, new_hashes)
    elif not matches:
        log(f"[{url}] Inga produkter med '{keyword}' hittades.")

# ▶ Huvudfunktion
def main():
    for entry in URLS_TO_MONITOR:
        check_site(entry)

if __name__ == "__main__":
    main()
