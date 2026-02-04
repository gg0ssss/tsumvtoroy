
import requests
import json
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import gspread
from oauth2client.service_account import ServiceAccountCredentials

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB_FILE = "products.json"

CATEGORIES = [
    # Женские сумки
    "https://collect.tsum.ru/women/catalog/povsednevnye-sumki-82",
    "https://collect.tsum.ru/women/catalog/riukzaki-i-poiasnye-sumki-87",
    "https://collect.tsum.ru/women/catalog/dorozhnye-i-sportivnye-sumki-93",
    "https://collect.tsum.ru/women/catalog/klatchi-i-vechernie-sumki-90",
    
    # Женские аксессуары
    "https://collect.tsum.ru/women/catalog/ochki-306",
    "https://collect.tsum.ru/women/catalog/remni-284",
    "https://collect.tsum.ru/women/catalog/koshelki-i-kartkholdery-299",
    "https://collect.tsum.ru/women/catalog/oblozhki-i-futliary-294",
    "https://collect.tsum.ru/women/catalog/aksessuary-dlia-sumok-367",
    
    # Мужские сумки
    "https://collect.tsum.ru/men/catalog/riukzaki-i-poiasnye-sumki-246",
    "https://collect.tsum.ru/men/catalog/povsednevnye-sumki-238",
    "https://collect.tsum.ru/men/catalog/dorozhnye-i-sportivnye-sumki-249",
    
    # Мужские аксессуары
    "https://collect.tsum.ru/men/catalog/sharfy-i-platki-353",
    "https://collect.tsum.ru/men/catalog/ukrasheniia-347",
    "https://collect.tsum.ru/men/catalog/remni-323",
    "https://collect.tsum.ru/men/catalog/oblozhki-i-futliary-332",
    "https://collect.tsum.ru/men/catalog/ochki-344",
    "https://collect.tsum.ru/men/catalog/koshelki-i-kartkholdery-337",
    "https://collect.tsum.ru/men/catalog/golovnye-ubory-326"
]

def send(msg):
    try:
        requests.post(f"{TG_API}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
        
        chat_id_2 = os.environ.get("CHAT_ID_2")
        if chat_id_2:
            requests.post(f"{TG_API}/sendMessage", json={"chat_id": chat_id_2, "text": msg})
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def init_google_sheets():
    """Подключение к Google Sheets"""
    try:
        creds_json = os.environ["GOOGLE_CREDENTIALS"]
        sheet_id = os.environ["SHEET_ID"]
        
        creds_dict = json.loads(creds_json)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(sheet_id).sheet1
        return sheet
    except Exception as e:
        print(f"Ошибка подключения к Google Sheets: {e}")
        return None

def add_to_google_sheets(sheet, brand, price, listing_date, url):
    """Добавляет проданный товар в Google Sheets"""
    try:
        sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([sale_date, brand, price, listing_date, url])
        print(f"  📊 Добавлено в Google Sheets")
    except Exception as e:
        print(f"Ошибка записи в Google Sheets: {e}")

def estimate_listing_date(item_url):
    """Определяет примерный месяц размещения по номеру ITEM"""
    try:
        item_id = item_url.split("/item/")[1].split("/")[0]
        num = int(item_id.replace("ITEM", ""))
        
        if num >= 380446: return "январь 2026"
        elif num >= 378324: return "декабрь 2025"
        elif num >= 375363: return "ноябрь 2025"
        elif num >= 374536: return "октябрь 2025"
        elif num >= 366646: return "август 2025"
        elif num >= 362999: return "июнь 2025"
        elif num >= 350905: return "май 2025"
        elif num >= 332922: return "начало 2025"
        elif num >= 305982: return "конец 2024"
        elif num >= 221563: return "2023-2024"
        else: return "очень давно"
    except:
        return "неизвестно"

def check_product_page(driver, url):
    try:
        driver.get(url)
        time.sleep(3)
        
        try:
            driver.find_element(By.CSS_SELECTOR, "p[class*='noExists']")
            return "sold"
        except:
            pass
        
        try:
            driver.find_element(By.CSS_SELECTOR, "p[class*='reserved']")
            return "reserved"
        except:
            pass
        
        return "available"
    except Exception as e:
        print(f"Ошибка проверки {url}: {e}")
        return "unknown"

# Подключаемся к Google Sheets
google_sheet = init_google_sheets()

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        old_products = json.load(f)
else:
    old_products = {}

new_products = {}

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-software-rasterizer")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36")

try:
    send("Ищу дорогую ненужную хуйню🥶")
    
    # Пробуем запустить Chrome несколько раз
    driver = None
    for attempt in range(3):
        try:
            driver = webdriver.Chrome(options=chrome_options)
            break
        except Exception as e:
            print(f"Попытка {attempt + 1}/3 запустить Chrome: {e}")
            time.sleep(5)
    
    if not driver:
        raise Exception("Не удалось запустить Chrome после 3 попыток")
    
    for category_url in CATEGORIES:
        print(f"\nПарсинг: {category_url}")
        
        try:
            driver.get(category_url)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/item/ITEM']")))
        except Exception as e:
            print(f"Ошибка загрузки категории {category_url}: {e}")
            continue
        
        attempts = 0
        while attempts < 200:
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            except:
                print("Ошибка прокрутки, пропускаем")
                break
                
            try:
                button = driver.find_element(By.XPATH, "//p[contains(text(), 'Показать больше товаров')]")
                driver.execute_script("arguments[0].click();", button)
                time.sleep(3)
            except:
                break
            attempts += 1
        
        cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/item/ITEM']")
        print(f"  Найдено: {len(cards)} товаров")
        
        for card in cards:
            try:
                url = card.get_attribute("href")
                if url in new_products:
                    continue
                
                # Парсим цену
                try:
                    price_elem = card.find_element(By.CSS_SELECTOR, "span[class*='price']")
                    price_text = price_elem.text.strip()
                    if not price_text:
                        price_text = "Цена неизвестна"
                except:
                    price_text = "Цена неизвестна"
                
                # Бренд из старой базы или парсим
                if url in old_products and old_products[url].get("title") != "Товар":
                    brand_name = old_products[url]["title"]
                else:
                    try:
                        brand_img = card.find_element(By.CSS_SELECTOR, "img[data-brandlogo='true']")
                        brand_name = brand_img.get_attribute("alt") or "Товар"
                    except:
                        brand_name = "Товар"
                
                new_products[url] = {
                    "title": brand_name,
                    "price": price_text,
                    "in_stock": True
                }
            except Exception as e:
                continue
    
    print(f"\n✅ Всего товаров: {len(new_products)}")
    
    sold_count = 0
    for old_url, old_data in old_products.items():
        if old_data["in_stock"] and old_url not in new_products:
            print(f"Проверяю: {old_url}")
            
            try:
                status = check_product_page(driver, old_url)
            except:
                print(f"  ⚠️ Ошибка проверки, пропускаем")
                continue
            
            if status == "sold":
                price_info = old_data.get('price', 'Цена неизвестна')
                listing_date = estimate_listing_date(old_url)
                
                if google_sheet:
                    add_to_google_sheets(google_sheet, old_data['title'], price_info, listing_date, old_url)
                
                send(f"❌ ПРОДАНО\n\n{old_data['title']}\nЦена: {price_info}\nВыставлено: {listing_date}\n\n{old_url}")
                sold_count += 1
                print(f"  ✅ ПРОДАНО: {old_data['title']} за {price_info}")
            elif status == "reserved":
                print(f"  В резерве - игнорируем")
    
    if driver:
        driver.quit()
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(new_products, f, ensure_ascii=False, indent=2)
    
    send(f"✅ Нашел дэм🫨\nТоваров: {len(new_products)}\nПродано: {sold_count}")

except Exception as e:
    send(f"⚠️ Ошибка: {str(e)}")
    print(f"ERROR: {e}")
    try:
        if driver:
            driver.quit()
    except:
        pass
