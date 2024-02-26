import os
import re
import sys
import django
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from manual_provinces import manual_provinces

project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Backend.settings")
django.setup()

from api.models import Websites, Categories, JobOffers

geolocator = Nominatim(user_agent="my-application123")

def get_province(city_name):

    city = re.sub(r"\s*\([^)]*\)", "", city_name).split(',')[0].strip()

    try:
        location = geolocator.geocode(f"{city}, Polska")
        if location:
            display_name = location.raw.get('display_name', '')
            match = re.search(r'województwo (\w+[-\w]*)', display_name)
            if match:
                return f"województwo {match.group(1)}"
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Błąd geokodowania dla {city}: {e}")

    return manual_provinces.get(city)

def transform_date(publication_date):
    publication_date = publication_date.strip().lower()
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    day_before_yesterday = today - timedelta(days=2)

    if "przedwczoraj" in publication_date:
        transformed_date = day_before_yesterday
    elif "wczoraj" in publication_date:
        transformed_date = yesterday
    elif "dzisiaj" in publication_date:
        transformed_date = today
    else:
        try:
            date_obj = datetime.strptime(publication_date, '%d.%m.%Y').date()
            transformed_date = date_obj
        except ValueError:
            print(f"Error transforming date: {publication_date}")
            transformed_date = None

    return transformed_date

def scrapp(site_url, category_name, category_path):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    current_page = 1

    Category, created = Categories.objects.get_or_create(Category_name=category_name)
    Website, created = Websites.objects.get_or_create(Website_name="gowork", Website_url=site_url)

    while True: 
        if current_page == 1:
            page_url = f"{site_url}/praca/{category_path};b"
        else:
            page_url = f"{site_url}/praca/{category_path};b/{current_page};pg"
        driver.get(page_url)

        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-v-20d44b47]')))
        except TimeoutException:
            print("Nie można załadować strony lub brak więcej ofert pracy.")
            break

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        offers = soup.find_all('div', class_='job-item__content')

        for offer in offers:
            position_element = offer.find('h2', class_='g-job-title')
            position = position_element.get_text(strip=True) if position_element else None

            firm_element = offer.find('a', class_='g-company-name')
            if not firm_element:
                firm_element = offer.find('div', class_='g-company-name')
            if not firm_element:
                firm_element = offer.find('span', class_='company-name')

            firm = None
            if firm_element:
                firm_raw = firm_element.get_text(strip=True)
                firm = re.sub(r'\s*\([^)]*\)', '', firm_raw).strip()

            location_element = offer.find('div', class_='g-job-location')
            location = location_element.get_text(strip=True) if location_element else None

            location_element = offer.find('div', class_='g-job-location')
            if location_element:
                location_text = location_element.get_text(strip=True) if location_element else None
            else:
                location_text = None
            location = location_text

            province = get_province(location)

            earnings_element = offer.find('div', class_='g-job-salary')
            if earnings_element:
                earnings_text = earnings_element.get_text(strip=True).split(" (zal. od typu umowy)")[0]
                earnings = earnings_text
            else:
                earnings = None

            divs = offer.find_all("div", class_="g-job-offer-tags")
            job_type = working_hours = job_model = None
            for div in divs:
                text = div.get_text(strip=True).lower()
                if 'umowa' in text or 'b2b' in text or 'inny' in text:
                    job_type = div.get_text(strip=True)
                elif 'etat' in text or 'dodatkowa' in text or 'staż/praktyki' in text or 'praktyki' in text:
                    working_hours = div.get_text(strip=True)
                elif 'stacjonarna' in text or 'zdalna' in text or 'hybrydowa' in text:
                    job_model = div.get_text(strip=True)

            link_element = position_element.find('a')
            link = link_element['href'] if link_element else None
            full_link = site_url + link if link else None

            publication_date_text = offer.select_one('div.job-date').get_text(strip=True)
            publication_date = transform_date(publication_date_text)

            print(f"Pozycja: {position},  Lokacja: {location}, Województwo: {province}, Link: {link}")

            existing_offer = JobOffers.objects.filter(
                Position=position, 
                Location=location, 
                Firm=firm
            ).first()

            if not existing_offer:
                new_offer=JobOffers(
                    Position=position,
                    Location=location,
                    Province=province,
                    Firm=firm,
                    Job_type=job_type,
                    Job_model=job_model,
                    Working_hours=working_hours,
                    Earnings=earnings,
                    Date=publication_date,
                    Link=full_link,
                    Website=Website,
                    Category=Category
                )
                new_offer.save()
                print(f"Zapisano nową ofertę pracy: {position} w {location}.")
            else:
                print("Oferta pracy już istnieje w bazie danych. Pomijanie.")
        
        next_page_exists = driver.find_elements(By.CSS_SELECTOR, 'a.page-link')
        if not next_page_exists:
            print("Brak kolejnych stron, kończenie scrapowania.")
            break
        current_page += 1

    driver.quit()

categories = {
    "Administracja biurowa": "administracja-biurowa",
    "Badania i rozwój": "badania-i-rozwoj",
    "Finanse / Ekonomia / Księgowość": "bankowosc",
    "BHP / Ochrona środowiska": "bhp-ochrona-srodowiska-rolnictwo",
    "Budownictwo / Remonty / Geodezja": "budownictwo",
    "Obsługa klienta i call center": "call-center",
    "Nauka / Edukacja / Szkolenia": "edukacja-szkolenia",
    "Finanse / Ekonomia / Księgowość": "finanse-ksiegowosc",
    "Praca fizyczna": "fizyczna",
    "Franczyza / Własny biznes": "franczyza-wlasny-biznes",
    "Reklama / Grafika / Kreacja / Fotografia": "grafika-kreacja-fotografia",
    "Hotelarstwo / Gastronomia / Turystyka": "hotelarstwo-gastronomia-turystyka",
    "HR": "hr-kadry-i-place",
    "Inżynieria": "inzynieria",
    "IT / telekomunikacja / Rozwój oprogramowania / Administracja": "it",
    "Kadra kierownicza": "kadra-zarzadzajaca",
    "Kontrola jakości": "kontrola-jakosci",
    "Marketing i PR": "marketing-reklama-pr",
    "Media / Sztuka / Rozrywka": "media-sztuka-rozrywka",
    "Nieruchomości": "nieruchomosci",
    "Opieka": "opieka",
    "Opieka": "opieka-zdrowotna",
    "Prawo": "prawo",
    "Produkcja": "produkcja",
    "Sprzedaż": "sprzedaz-i-obsluga-klienta",
    "Transport / Spedycja / Logistyka / Kierowca": "transport-spedycja-logistyka",
    "Ubezpieczenia": "ubezpieczenia",
    "Medycyna / Zdrowie / Uroda / Rekreacja": "uroda-rekreacja-zdrowy-styl-zycia",
}

site_url = "https://www.gowork.pl"
for category_name, category_path in categories.items():
    scrapp(site_url, category_name, category_path)