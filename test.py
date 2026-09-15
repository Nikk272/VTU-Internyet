import time
import os
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ---------- SETTINGS ----------
BASE_URL = "https://vtu.internyet.in/dashboard/company/applicants?status=6"
START_PAGE = 1
END_PAGE = 5
EXPECTED_ROWS = 18
OUTPUT_FILE = "datan.xlsx"
# ------------------------------

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# LOGIN
driver.get("https://vtu.internyet.in/sign-in")
print("Waiting 40 seconds for you to login manually...")
time.sleep(40)

print("\nLogin complete. Starting extraction...\n")

all_data = []
report = []   # <-- summary report list

# PAGE LOOP
for page in range(START_PAGE, END_PAGE + 1):

    url = f"{BASE_URL}&page={page}"
    print(f"\n====================================")
    print(f" Loading & Extracting Page {page}")
    print(f"====================================")

    driver.get(url)

    extracted_count = 0
    attempts = 0
    temp_data = []

    # WAIT for EXACT 18 rows
    while extracted_count < EXPECTED_ROWS:
        soup = BeautifulSoup(driver.page_source, "lxml")
        rows = soup.find_all("tr")

        temp_data = []

        for tr in rows:
            cols = tr.find_all("td")
            if len(cols) < 7:
                continue
            temp_data.append(cols)

        extracted_count = len(temp_data)
        attempts += 1

        if extracted_count < EXPECTED_ROWS:
            print(
                f"Waiting... only {extracted_count}/18 rows found (Attempt {attempts})")
            time.sleep(5)

        if attempts > 20:
            print("⚠ Page did not load fully after 120s.")
            break

    # SUMMARY ENTRY
    if extracted_count == EXPECTED_ROWS:
        report.append(
            f"Page {page:<3} ............................... Extracted {extracted_count} Rows")
    else:
        report.append(
            f"Page {page:<3} ............................... FAILED (Extracted {extracted_count})")

    print(f"Page {page} loaded with {extracted_count} rows. Extracting...")

    # EXTRACT ROW DATA
    for cols in temp_data:

        ID = cols[0].text.strip()
        Name = cols[1].text.strip()
        Email = cols[2].text.strip()
        Internship = cols[3].text.strip()
        Date = cols[4].text.strip()
        Status = cols[5].text.strip()

        action_links = cols[6].find_all("a")
        view_link = action_links[0]["href"] if len(action_links) > 0 else ""
        edit_link = action_links[1]["href"] if len(action_links) > 1 else ""

        row_data = {
            "ID": ID,
            "Name": Name,
            "Email": Email,
            "Internship": Internship,
            "Date": Date,
            "Status": Status,
            "View Link": view_link,
            "Edit Link": edit_link,
            "Page": page
        }

        all_data.append(row_data)

    # SAVE AFTER EACH PAGE
    df = pd.DataFrame(all_data)
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"✓ Page {page} saved to Excel.")

print("\n====================================")
print(" ALL PAGES COMPLETED — FINAL REPORT")
print("====================================\n")

# PRINT REPORT
for line in report:
    print(line)

print(f"\nFinal Excel File → {OUTPUT_FILE}")
driver.quit()
