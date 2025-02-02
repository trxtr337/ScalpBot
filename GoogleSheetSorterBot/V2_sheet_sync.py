import schedule
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Путь к ChromeDriver
chrome_driver_path = 'C:\\Users\\vadik\\Downloads\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe'

# Настройки Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")  # Запуск в фоновом режиме (без графического интерфейса)
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Инициализация веб-драйвера
service = ChromeService(executable_path=chrome_driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# URL сайта
url = 'https://account.leadteh.ru/login?response_type=code&client_id=f62a5a9a-4189-4ee1-b778-001d3cba2a78&redirect_uri=https%3A%2F%2Fapp.leadteh.ru%2Fauthorize'

# Ваши учетные данные
username = 'vcharuh@gmail.com'
password = 'Inn615007563639'

try:
    print("Открытие сайта...")
    driver.get(url)

    print("Ввод логина...")
    username_input = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//input[@name="login"]')))
    username_input.send_keys(username)

    print("Ввод пароля...")
    password_input = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//input[@type="password"]')))
    password_input.send_keys(password)

    print("Нажатие кнопки входа...")
    login_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//button[@type="submit"]')))
    login_button.click()

    # Дождаться успешного входа в систему
    print("Ожидание успешного входа...")
    WebDriverWait(driver, 20).until(EC.url_contains("projects/b2ef2602-8e12-4a2c-b78d-d26d2fa799c0"))  # Измените на правильную часть URL после входа

    # Нажатие на кнопку Standart_Dev
    print("Ожидание кнопки Standart_Dev...")
    standart_dev_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, '//a[@href="/projects/5f31b1f2-3c29-4f68-a156-bf967d4d5684"]'))
    )
    standart_dev_button.click()
    print("Кнопка Standart_Dev нажата.")

    # Дождаться успешного входа в систему
    print("Ожидание успешного входа Standart_Dev...")
    WebDriverWait(driver, 20).until(EC.url_contains("projects/5f31b1f2-3c29-4f68-a156-bf967d4d5684"))  # Измените на правильную часть URL после входа

    # Нажатие на кнопку Scalpix
    print("Ожидание кнопки Scalpix...")
    scalpix_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, '//div[@class="project-items__title" and text()="Scalpix"]'))
    )
    scalpix_button.click()
    print("Кнопка Scalpix нажата.")

    # Дождаться успешного входа в систему
    print("Ожидание успешного входа Scalpix...")
    WebDriverWait(driver, 20).until(EC.url_contains("spreadsheets/50d6cf1e-099f-44b0-8d9d-0e39a0dd48c8"))  # Измените на правильную часть URL после входа
    time.sleep(5)

    # Переход к следующим этапам
    print("Ожидание кнопки Settings...")
    settings_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, '//li[contains(text(), "Settings")]'))
    )
    settings_button.click()
    print("Кнопка Settings нажата.")
    time.sleep(20)

    # Закрытие рекламы, если она появляется
    try:
        print("Проверка наличия рекламы...")
        close_ad_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//jdiv[@class="button_d161 closeButton_b640"]'))
        )
        close_ad_button.click()
        print("Реклама закрыта.")
        time.sleep(5)
    except:
        print("Реклама не найдена или уже закрыта.")

    print("Ожидание кнопки Integration with Google Sheets...")
    integration_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, '//li[contains(text(), "Integration with Google Sheets")]'))
    )
    integration_button.click()
    print("Кнопка Integration with Google Sheets нажата.")
    time.sleep(10)

    # Использование JavaScript для клика по кнопке "Sync Now"
    driver.execute_script("""
        var buttons = document.querySelectorAll('button.el-button.el-button--default span');
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i].textContent.trim() === 'Sync Now') {
                buttons[i].click();
                break;
            }
        }
    """)
    print("Кнопка Sync Now нажата.")
    time.sleep(15)

    print("Ожидание кнопки Save...")
    save_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@type="button" and @class="el-button el-button--primary" and .//span[text()="Save"]]'))
    )
    driver.execute_script("arguments[0].click();", save_button)
    print("Кнопка Save нажата.")
    time.sleep(15)

    driver.refresh()
    print("Синхронизация завершена и страница перезагружена.")
finally:
    driver.quit()

