import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
import os

# ---------------- Configuration ---------------- #
PROMPT_PATH = "prompt.txt"
OUTPUT_CSV = "responses.csv"  # Save results here
BING_CHAT_URL = "https://copilot.microsoft.com/shares/Nn1sb16d2u8yvumH4sYz4"

# ---------------- Setup Edge Browser ---------------- #
options = webdriver.EdgeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
TEMP_PROFILE_DIR = r"C:\\Users\\Vivek Kumar\\AppData\\Local\\Temp\\edge_temp_profile"
options.add_argument(f"user-data-dir={TEMP_PROFILE_DIR}")

# ---------------- Use local EdgeDriver ---------------- #
EDGE_DRIVER_PATH = r"C:\\Users\\Vivek kumar\\Downloads\\edgedriver_win64\\msedgedriver.exe"
service = Service(EDGE_DRIVER_PATH)
driver = webdriver.Edge(service=service, options=options)

# ---------------- Open Bing Chat ---------------- #
driver.get(BING_CHAT_URL)
time.sleep(5)  # wait for page to load

# ---------------- Load prompts ---------------- #
with open(PROMPT_PATH, 'r', encoding="utf-8") as f:
    prompts = [line.strip() for line in f if line.strip()]  # list of prompts

# ---------------- Prepare CSV (append mode) ---------------- #
file_exists = os.path.exists(OUTPUT_CSV)
with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    if not file_exists:
        writer.writerow(["Note: Each entry includes a multi-line response with a Basic Analysis below."])

# ---------------- Loop through prompts ---------------- #
for idx, prompt in enumerate(prompts, 1):
    print(f"➡️ Sending query {idx}/{len(prompts)}: {prompt}")

    # ---------------- Send prompt ---------------- #
    try:
        input_box = driver.find_element(By.TAG_NAME, "textarea")
        input_box.clear()
        input_box.send_keys(prompt)
        input_box.send_keys(Keys.ENTER)
    except NoSuchElementException:
        print("❌ Input box not found!")
        break

    # ---------------- Wait for response & extract text ---------------- #
    print("⌛ Waiting for response...")
    wait = WebDriverWait(driver, 60)
    initial_ai_count = len(driver.find_elements(By.XPATH, "//div[contains(@class,'group/ai-message-item')]"))

    def last_ai_text_ready(d):
        items = d.find_elements(By.XPATH, "//div[contains(@class,'group/ai-message-item')]")
        if len(items) <= initial_ai_count:
            return False

        last = items[-1]
        blocks = last.find_elements(By.XPATH, ".//p | .//li | .//pre | .//code")
        if not blocks:
            blocks = last.find_elements(By.XPATH, ".//span[contains(@class,'whitespace-pre-wrap')]")

        seen = set()
        lines = []
        for b in blocks:
            txt = b.text.strip()
            if txt and txt not in seen:
                seen.add(txt)
                lines.append(txt)

        text = "\n".join(lines).strip() if lines else last.text.strip()
        if not text or text == prompt:
            return False
        return text

    try:
        response_text = wait.until(last_ai_text_ready)

        stable_count = 0
        while stable_count < 3:
            time.sleep(2)
            new_text = last_ai_text_ready(driver)
            if new_text and new_text != response_text:
                response_text = new_text
                stable_count = 0
            else:
                stable_count += 1
    except TimeoutException:
        response_text = ""

    # ---------------- Save response to CSV in required format ---------------- #
    if response_text:
        word_count = len(response_text.split())
        char_count = len(response_text)
        sentence_count = response_text.count('.') + response_text.count('!') + response_text.count('?')

        response_with_analysis = (
            f"RESPONSE {idx}:\n{response_text}\n\n"
            f"--- Basic Analysis ---\n"
            f"Total Words: {word_count}\n"
            f"Total Characters: {char_count}\n"
            f"Total Sentences: {sentence_count}\n"
            f"{'='*50}"
        )

        with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            # ✅ Comma after prompt, multi-line response in second column
            writer.writerow([f"PROMPT {idx}: {prompt},", response_with_analysis])
        print(f"✅ Saved response {idx} in perfect readable format")
    else:
        print(f"❌ No response found for prompt {idx}")

    # ---------------- Rate limiting ---------------- #
    time.sleep(10)  # wait 10 seconds between queries

driver.quit()
print("🚀 Done! All queries processed.")
