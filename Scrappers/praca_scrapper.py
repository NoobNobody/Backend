import os
import sys
import re
import django
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from helping_functions import get_earnings_type, parse_earnings, get_province, get_location_details

project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Backend.settings")
django.setup()

from api.models import Websites, Categories, JobOffers

def transform_date(publication_date):
    days_pattern = re.compile(r'(\d+)\s+(?:dzie[ńn]|dni)')
    days_match = days_pattern.search(publication_date)
    if days_match:
        days = int(days_match.group(1))
        return (datetime.today() - timedelta(days=days)).date().isoformat()
    elif "godz." in publication_date:
        return datetime.today().date().isoformat()
    else:
        return None
    
def scrapp(site_url, category_name, category_path):
    print(f"Rozpoczynanie scrapowania kategorii: {category_name}")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    current_page = 1
    
    Category, created = Categories.objects.get_or_create(Category_name=category_name)
    Website, created = Websites.objects.get_or_create(Website_name="praca", Website_url=site_url)

    while True:
        if current_page == 1:
            page_url = f"{site_url}/{category_path}.html"
        else:
            page_url = f"{site_url}/{category_path}_{current_page}.html"

        driver.get(page_url)

        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'listing__item')))
        except TimeoutException:
            break

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        offers = soup.find_all('li', class_='listing__item')

        for offer in offers:
            position_element = offer.find('a', class_='listing__title')
            firm_element = offer.find('a', class_='listing__employer-name')

            if not position_element or not firm_element:
                continue
            position = position_element.get_text(strip=True)
            
            if firm_element:
                firm = firm_element.get_text(strip=True)
            else:
                firm = None 

            location_element = offer.find('span', class_='listing__location-name')
            if location_element:
                location_text = location_element.contents[0].strip() if location_element.contents else None
            else:
                location_text = None
            location = location_text

            location_details = get_location_details(location)
            print(location_details)
            
            province = get_province(location)

            working_hours = offer.find('li', attrs={'data-test': 'offer-additional-info-1'}).get_text(strip=True) if offer.find('li', attrs={'data-test': 'offer-additional-info-1'}) else None

            job_model_element = offer.find('span', class_='listing__work-model')
            if job_model_element:
                all_text = job_model_element.get_text(strip=True)
                nested_span = job_model_element.find('span')
                if nested_span:
                    nested_text = nested_span.get_text(strip=True)
                    job_model = all_text.replace(nested_text, nested_text + ' ', 1).strip()
                else:
                    job_model = all_text
            else:
                job_model = None

            details_element = offer.find('div', class_='listing__main-details')
            if details_element:
                details_text = details_element.get_text(separator=' | ', strip=True)
                divided_details = details_text.split(' | ')

                job_type = None
                working_hours = None
                earnings = None

                for detail in divided_details:
                    if "umowa" in detail:
                        job_type = detail.strip()
                    elif "etat" in detail or "etatu" in detail:
                        working_hours = detail.strip()
                    elif "zł" in detail:
                        earnings_text = re.sub(r'\s+', ' ', detail.strip())
                        if "brutto/mies." in details_text:
                            earnings = f"{earnings_text} brutto/mies."
                        elif "brutto/godz." in details_text:
                            earnings = f"{earnings_text} brutto/godz."
                        else:
                            earnings = earnings_text
            else:
                job_type = None
                working_hours = None
                earnings = None


            min_earnings, max_earnings, average_earnings, _ = parse_earnings(earnings)
            earnings_type = get_earnings_type(min_earnings, max_earnings)
            
            publication_date_text = offer.find('div', class_='listing__secondary-details listing__secondary-details--with-teaser').get_text(strip=True) if offer.find('div', class_='listing__secondary-details listing__secondary-details--with-teaser') else 'Brak danych'
            publication_date = transform_date(publication_date_text)
            if publication_date is None:
                print("Data publikacji jest None, pomijanie oferty.")
                continue

            link = offer.find('a', class_='listing__title')['href'] if offer.find('a', class_='listing__title') else None
            
            print(f"Pozycja: {position},  Lokacja: {location}, Województwo: {province}, Link: {link}")

            try:
                check_date = datetime.strptime(publication_date, '%Y-%m-%d').date()
                print(f"Sprawdzana data: {check_date}") 
            except TypeError as e:
                print(f"Błąd przekształcania daty: {e}, dla daty publikacji: {publication_date}")
                continue

            existing_offer = JobOffers.objects.filter(
                Position=position, 
                Location=location, 
                Firm=firm
            ).first()

            if not existing_offer:
                new_offer=JobOffers(
                    Position=position,
                    Location=location,
                    Location_Latitude=location_details['latitude'],
                    Location_Longitude=location_details['longitude'],
                    Province=province,
                    Firm=firm,
                    Job_type=job_type,
                    Job_model=job_model,
                    Working_hours=working_hours,
                    Earnings=earnings,
                    Min_Earnings=min_earnings,
                    Max_Earnings=max_earnings,
                    Average_Earnings=average_earnings,
                    Earnings_Type=earnings_type,
                    Date=publication_date,
                    Link=link,
                    Website=Website,
                    Category=Category
                )
                new_offer.save()
                print(f"Zapisano nową ofertę pracy: {position} w {location}.")
            else:
                print("Oferta pracy już istnieje w bazie danych. Pomijanie.")

        next_page_exists = driver.find_elements(By.CSS_SELECTOR, 'a.pagination__item.pagination__item--next')
        if not next_page_exists:
            print("Brak kolejnych stron, kończenie scrapowania.")
            break
        current_page += 1

    driver.quit()
            
categories = {
    # "Administracja biurowa": "administracja-biurowa",
    # "Sektor publiczny": "administracja-publiczna-sluzba-cywilna",
    # "Architektura": "architektura",
    # "Badania i rozwój": "badania-i-rozwoj",
    # "Budownictwo / Remonty / Geodezja": "budownictwo-geodezja",
    # "Doradztwo / Konsulting": "doradztwo-konsulting",
    # "Nauka / Edukacja / Szkolenia": "edukacja-nauka-szkolenia",
    # "Energetyka": "energetyka-elektronika",
    # "Laboratorium / Farmacja / Biotechnologia": "farmaceutyka-biotechnologia",
    # "Finanse / Ekonomia / Księgowość": "finanse-bankowosc",
    # "Hotelarstwo / Gastronomia / Turystyka": "gastronomia-catering",
    # "Hotelarstwo / Gastronomia / Turystyka": "turystyka-hotelarstwo",
    # "Reklama / Grafika / Kreacja / Fotografia": "grafika-fotografia-kreacja",
    "Human Resources / Zasoby ludzkie": "human-resources-kadry",
    # "IT / telekomunikacja / Rozwój oprogramowania / Administracja": "informatyka-administracja",
    "IT / telekomunikacja / Rozwój oprogramowania / Administracja": "informatyka-programowanie",
    # "Internet / e-Commerce": "internet-e-commerce",
    # "Inżynieria": "inzynieria-projektowanie",
    # "Kadra kierownicza": "kadra-zarzadzajaca",
    # "Kontrola jakości": "kontrola-jakosci",
    # "Fryzjerstwo, kosmetyka": "kosmetyka-pielegnacja",
    # "Finanse / Ekonomia / Księgowość": "ksiegowosc-audyt-podatki",
    # "Transport / Spedycja / Logistyka / Kierowca": "logistyka-dystrybucja",
    # "Transport / Spedycja / Logistyka / Kierowca": "transport-spedycja",
    # "Marketing i PR": "marketing-reklama-pr",
    # "Media / Sztuka / Rozrywka": "media-sztuka-rozrywka",
    # "Medycyna / Zdrowie / Uroda / Rekreacja": "medycyna-opieka-zdrowotna",
    # "Motoryzacja": "motoryzacja",
    "Nieruchomości": "nieruchomosci",
    "Ochrona": "ochrona-osob-i-mienia",
    "Organizacje pozarządowe / Wolontariat": "organizacje-pozarzadowe-wolontariat",
    "Praca fizyczna": "praca-fizyczna",
    "Praktyki / Staż": "praktyki-staz",
    "Prawo": "prawo",
    "Produkcja": "przemysl-produkcja",
    "Rolnictwo i ogrodnictwo": "rolnictwo-ochrona-srodowiska",
    "Instalacje / Utrzymanie / Serwis": "serwis-technika-montaz",
    "Sport": "sport-rekreacja",
    "Sprzedaż": "sprzedaz-obsluga-klienta",
    "Obsługa klienta i call center": "telekomunikacja",
    "Tłumaczenia": "tlumaczenia",
    "Ubezpieczenia": "ubezpieczenia",
    "Zakupy": "zakupy",
    "Franczyza / Własny biznes": "franczyza",
}

site_url = "https://www.praca.pl"
for category_name, category_path in categories.items():
    scrapp(site_url, category_name, category_path)