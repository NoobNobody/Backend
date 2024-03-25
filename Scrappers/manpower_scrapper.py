import re
import sys
import os
import django
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
from helping_functions import get_province, get_location_details

project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Backend.settings")
django.setup()

from api.models import Websites, Categories, JobOffers

def transform_date(publication_date):
    if not publication_date:
        return None
    try:
        date_obj = datetime.strptime(publication_date, '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError as e:
        print(f"Błąd podczas przekształcania daty: {e}")
        return None
    
def scrapp(site_url, category_name, category_path):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    current_page = 1
   
    Category, created = Categories.objects.get_or_create(Category_name=category_name)
    Website, created = Websites.objects.get_or_create(Website_name="manpower", Website_url=site_url)

    while True:
        page_url = f"{site_url}/pl/szukaj-pracy?page={current_page}&industries={category_path}"

        driver.get(page_url)
        print(f"Aktualna strona: {page_url}")
        
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.card-body')))
        except TimeoutException:
            break

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        offers = soup.find_all('div', class_='card-body')

        for offer in offers:

            position_element = offer.select_one('.job-position h2.title a')
            position = position_element.text.strip() if position_element else None

            location_element = offer.select_one('.location')
            if location_element:
                location = location_element.text.strip()
                location = location.split(',')[0].strip()

            location_details = get_location_details(location)
            province = get_province(location)

            job_type_element = offer.select_one('.type')
            job_type = job_type_element.text.strip() if job_type_element else None

            publication_date_element = offer.select_one('.date').text.strip() if offer.select_one('.date') else None
            if not publication_date_element:
                print("Brak daty publikacji. Pomijanie oferty.")
                continue
            publication_date = transform_date(publication_date_element)

            link = position_element['href'] if position_element else None
            full_link = site_url + link

            existing_offer = JobOffers.objects.filter(
                Position=position, 
                Location=location
            ).first()

            if not existing_offer:
                print(f"Pozycja: {position},  Lokalizacja: {location}, Województwo: {province}, Data: {publication_date}")
                new_offer=JobOffers(
                    Position=position,
                    Firm="Manpower",
                    Location=location,
                    Location_Latitude=location_details['latitude'],
                    Location_Longitude=location_details['longitude'],
                    Province=province,
                    Job_type=job_type,
                    Date=publication_date,
                    Link=full_link,
                    Website=Website,
                    Category=Category
                )
                new_offer.save()
                print(f"Zapisano w bazie danych nową ofertę pracy!")
                print()
            else:
                print("Oferta pracy już istnieje w bazie danych. Pomijanie.")
                print()

        next_page_exists = driver.find_elements(By.CSS_SELECTOR, 'a.page-link.more')
        if not next_page_exists:
            print("Brak kolejnych stron, kończenie scrapowania.")
            break
        current_page += 1

    driver.quit()

categories = {
    "Produkcja": "Produkcja&ids={industries:[8f5b8e3a160e42f0914077c3d2550420]}&sf=industries",
    "Prace magazynowe": "Magazyn&ids={industries:[d4c6348f2d9e4650929160ca7715a71a]}&sf=industries",
    "Inżynieria": "Inżynieria&ids={industries:[3858bb14bb7245df970dd015c64c7c65]}&sf=industries",
    "Obsługa klienta i call center": "Obsługa+klienta&ids={industries:[7f52a86281d2493ca2f950c62d87c44f]}&sf=industries",
    "Sprzedaż": "Sprzedaż&ids={industries:[c2d78c75e85746be959ee87dcb524d77]}&sf=industries",
    "Finanse / Ekonomia / Księgowość": "Finanse&ids={industries:[e1ff6be96a264eeabda19ea922d64b93]}&sf=industries",
    "Finanse / Ekonomia / Księgowość": "Księgowość+&ids={industries:[f4f1345a7bd54d588295a5b89326ea86]}&sf=industries",
    "Transport / Spedycja / Logistyka / Kierowca": "Logistyka+i+zaopatrzenie&ids={industries:[c3249aa827fb42e6b6102e41e0731430]}&sf=industries",
    "Transport / Spedycja / Logistyka / Kierowca": "Kierowca&ids={industries:[4e729d2dfed24e51a89d930da706b2d4]}&sf=industries",
    "HR": "HR&ids={industries:[938e32cd5eea48cd814d1cd09c17dec1]}&sf=industries",
    "Administracja biurowa": "Biuro&ids={industries:[ef4874de00eb49379339cec4be76418b]}&sf=industries",
    "Internet / e-Commerce": "E-commerce&ids={industries:[a7a2772f82fd41ceb64560ff4d7ed27a]}&sf=industries",
    "Budownictwo / Remonty / Geodezja": "Budownictwo&ids={industries:[62d1cdbd8f774f53a464d1fa6666ce1f]}&sf=industries",
    "Medycyna / Zdrowie / Uroda / Rekreacja": "Medycyna&ids={industries:[579992e91a47475a91ab8193e27ae5f3]}&sf=industries",
    "Medycyna / Zdrowie / Uroda / Rekreacja": "Farmacja&ids={industries:[f9f5a5be8c884f5886c4a027196baf5a]}&sf=industries",
    "Zakupy": "Zakupy&ids={industries:[e5a11db64c354da7bb0e0aabaf7ca3d1]}&sf=industries",
    "Prawo": "Prawo&ids={industries:[588974fea5814ebdb5ba57dab7a0e45f]}&sf=industries",
    "IT / telekomunikacja / Rozwój oprogramowania / Administracja": "IT&ids={industries:[2057c2d9aaa845f5a15403dbb98d1018]}&sf=industries",
    "IT / telekomunikacja / Rozwój oprogramowania / Administracja": "Zarządzanie+projektami&ids={industries:[77a9519120d54d06b9ac999b2cfb4baf]}&sf=industries",
    "Pracownik sklepu": "Handel+detaliczny&ids={industries:[c9e415c0e7af4f1288ab80007652aaeb]}&sf=industries",
    "Marketing i PR": "Marketing&ids={industries:[0a7f506a5f294e1b842c7b316abfc29e]}&sf=industries",
    "Ubezpieczenia": "Ubezpieczenia&ids={industries:[7f243c710cb24c6bb650976636546294]}&sf=industries",
    "Finanse / Ekonomia / Księgowość": "Podatki&ids={industries:[d3f1b0dd0f134d078ad72c6d8b851be6]}&sf=industries",
    "Laboratorium / Farmacja / Biotechnologia": "Biotechnologia&ids={industries:[590025215e3f43438db5ba0e75d35b1e]}&sf=industries",
    "Laboratorium / Farmacja / Biotechnologia": "Laboratorium&ids={industries:[e2ed731a5ed8462d999bfcfca7cb1432]}&sf=industries"
}

site_url = "https://www.manpower.pl"
for category_name, category_path in categories.items():
    scrapp(site_url, category_name, category_path)