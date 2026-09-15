import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ---------- CONFIG ----------
EXCEL_INPUT = r"C:\Users\Nikhilsh\datan.xlsx"
EXCEL_OUTPUT = r"C:\Users\Nikhilsh\extracted_applicants.xlsx"
BASE_URL = "https://vtu.internyet.in/dashboard/company/view-applicant"

LOGIN_URL = "https://vtu.internyet.in/sign-in"
EMAIL = "<put email here>"
PASSWORD = "<put password here"

PAGE_RETRY_LIMIT = 30
RETRY_DELAY = 1
REFRESH_INTERVAL = 5
SAVE_INTERVAL = 10
HEADLESS = False

# XPaths
XPATH_EMAIL = "/html/body/div/div/main/main/div/div[1]/div[2]/form/fieldset/div[1]/div/div/input"
XPATH_PASSWORD = "/html/body/div/div/main/main/div/div[1]/div[2]/form/fieldset/div[2]/div/div/input"
XPATH_BUTTON = "/html/body/div/div/main/main/div/div[1]/div[2]/form/fieldset/button"

# This element determines if page is "ready"
ANCHOR_XPATH = "//span[normalize-space(text())='Full Name']"
# -----------------------------------------------


def load_paths_from_excel(path):
    df = pd.read_excel(path, engine="openpyxl")
    return [str(x).strip() for x in df.iloc[:, 6].dropna().tolist()]


def start_driver():
    opts = webdriver.ChromeOptions()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--start-maximized")

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=opts
    )
    return driver


def login(driver):
    print("🔐 Auto-login triggered...")

    try:
        driver.get(LOGIN_URL)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, XPATH_EMAIL))
        )

        driver.find_element(By.XPATH, XPATH_EMAIL).clear()
        driver.find_element(By.XPATH, XPATH_EMAIL).send_keys(EMAIL)

        driver.find_element(By.XPATH, XPATH_PASSWORD).clear()
        driver.find_element(By.XPATH, XPATH_PASSWORD).send_keys(PASSWORD)

        driver.find_element(By.XPATH, XPATH_BUTTON).click()

        WebDriverWait(driver, 20).until_not(
            EC.url_contains("sign-in")
        )

        print("✅ Logged in successfully.")
        return True

    except Exception as e:
        print(f"❌ Auto-login failed: {e}")
        return False


def ensure_logged_in(driver):
    if "sign-in" in driver.current_url:
        login(driver)


# --------------- FAST EXTRACTION -----------------
def extract_fields_from_page(driver):
    result = {}

    # Wait ONLY for one field ("Full Name")
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, ANCHOR_XPATH))
        )
    except:
        return {}  # Not ready yet

    # Quick text getter (no waiting)
    def get_text(xpath):
        els = driver.find_elements(By.XPATH, xpath)
        return els[0].text.strip() if els else ""

    # Extract title
    result["Internship"] = get_text("//h1[1]")

    labels = [
        "Full Name", "Email", "Phone Number", "College",
        "Department / Branch", "Semester", "State",
        "City", "Address"
    ]

    for label in labels:
        xpath = f"//span[normalize-space(text())='{label}']/following::p[1]"
        result[label] = get_text(xpath)

    return result


def page_data_loaded(data):
    return any([
        data.get("Full Name"),
        data.get("Email"),
        data.get("Phone Number")
    ])


# -------------------- MAIN -----------------------
def main():
    paths = load_paths_from_excel(EXCEL_INPUT)
    driver = start_driver()

    login(driver)

    extracted = []
    count_since_last_save = 0

    for idx, path in enumerate(paths, start=1):
        full_url = BASE_URL + "/" + path.lstrip("/")
        print(f"\n[{idx}] Opening: {full_url}")

        driver.get(full_url)
        time.sleep(2)

        retries = 0
        data = {}

        while retries < PAGE_RETRY_LIMIT:
            ensure_logged_in(driver)

            data = extract_fields_from_page(driver)

            if page_data_loaded(data):
                print("✔ Data extracted:")
                print(data)
                break

            retries += 1

            if retries % REFRESH_INTERVAL == 0:
                print("🔄 Refreshing page...")
                driver.get(full_url)

            print(f"⏳ Retry {retries}/{PAGE_RETRY_LIMIT}")
            time.sleep(RETRY_DELAY)

        if not page_data_loaded(data):
            print("❌ Could not load data – skipping.")
            data = {k: "" for k in [
                "Internship", "Full Name", "Email", "Phone Number",
                "College", "Department / Branch", "Semester",
                "State", "City", "Address"
            ]}

        data["url"] = full_url
        extracted.append(data)

        count_since_last_save += 1
        if count_since_last_save >= SAVE_INTERVAL:
            pd.DataFrame(extracted).to_excel(EXCEL_OUTPUT, index=False)
            print("💾 Auto-saved (10 entries).")
            count_since_last_save = 0

    pd.DataFrame(extracted).to_excel(EXCEL_OUTPUT, index=False)
    print("🎉 Final save completed.")

    driver.quit()


if __name__ == "__main__":
    main()
