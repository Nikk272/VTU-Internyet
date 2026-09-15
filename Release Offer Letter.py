import pandas as pd
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ---------- LOGIN CONFIG ----------
LOGIN_URL = "https://vtu.internyet.in/sign-in"
BASE_URL = "https://vtu.internyet.in/dashboard/company/view-applicant/"

EMAIL = "<input email here>"
PASSWORD = "<input password here>"

XPATH_EMAIL = "/html/body/div/div/main/main/div/div[1]/div[2]/form/fieldset/div[1]/div/div/input"
XPATH_PASSWORD = "/html/body/div/div/main/main/div/div[1]/div[2]/form/fieldset/div[2]/div/div/input"
XPATH_BUTTON = "/html/body/div/div/main/main/div/div[1]/div[2]/form/fieldset/button"

# ---------- FILE CONFIG ----------
EXCEL_INPUT = r"<input file path>"
COOKIE_FILE = "session_cookies.pkl"
NEW_STATUS = "<input status here>"


# ---------- DRIVER SETUP ----------
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)

    # Hide webdriver flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        },
    )
    return driver


# ---------- COOKIE HANDLING ----------
def save_cookies(driver):
    with open(COOKIE_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)


def load_cookies(driver):
    try:
        with open(COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
        return True
    except:
        return False


# ---------- LOGIN ----------
def login(driver):
    print("🔐 Logging in...")
    driver.get(LOGIN_URL)

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, XPATH_EMAIL))
    )

    driver.find_element(By.XPATH, XPATH_EMAIL).clear()
    driver.find_element(By.XPATH, XPATH_EMAIL).send_keys(EMAIL)

    driver.find_element(By.XPATH, XPATH_PASSWORD).clear()
    driver.find_element(By.XPATH, XPATH_PASSWORD).send_keys(PASSWORD)

    driver.find_element(By.XPATH, XPATH_BUTTON).click()

    WebDriverWait(driver, 120).until_not(
        EC.url_contains("sign-in")
    )

    save_cookies(driver)
    print("✅ Login successful\n")


# ---------- PROFILE UPDATE ----------
def update_profile(driver, wait, url, idx):
    driver.get(url)
    time.sleep(2)

    # Session expired check
    if "sign-in" in driver.current_url:
        print("🔁 Session expired → Re-logging in...")
        login(driver)
        driver.get(url)
        time.sleep(2)

    status_dropdown = wait.until(
        EC.presence_of_element_located(
            (By.XPATH,
             "//label[contains(.,'Application Status')]/following::select[1]")
        )
    )

    current_status = Select(status_dropdown).first_selected_option.text.strip()
    print(f"📌 Current Status → {current_status}")

    if current_status.lower() == "applied":
        print("➡ Updating status to Offer Released...")

        Select(status_dropdown).select_by_visible_text(NEW_STATUS)

        update_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(.,'Update Status')]")
            )
        )
        update_btn.click()

        time.sleep(2)
        print("✔ Status updated successfully\n")
    else:
        print("⏭ Skipped (Not Offer Released)\n")

    # Keep session alive
    if idx % 5 == 0:
        driver.execute_script("window.localStorage.length;")

    time.sleep(2 + (idx % 3))


# ---------- MAIN ----------
def main():
    driver = setup_driver()
    wait = WebDriverWait(driver, 30)

    driver.get(BASE_URL)

    # Try cookie-based login
    if load_cookies(driver):
        driver.refresh()
        time.sleep(3)

        if "sign-in" in driver.current_url:
            login(driver)
    else:
        login(driver)

    df = pd.read_excel(EXCEL_INPUT)
    urls = df.iloc[:, 1].dropna().tolist()

    total = len(urls)
    print(f"📌 Total records: {total}\n")

    for idx, path in enumerate(urls, start=1):
        full_url = BASE_URL + str(path).strip()
        print(f"{idx}/{total} → Processing {full_url}")

        try:
            update_profile(driver, wait, full_url, idx)
        except Exception as e:
            print(f"❌ Error → {e}\n")

    print("🎉 All records processed successfully!")
    driver.quit()


if __name__ == "__main__":
    main()
