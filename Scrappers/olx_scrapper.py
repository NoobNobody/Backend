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
from helping_functions import parse_earnings, get_province, get_location_details, get_earnings_type

project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Backend.settings")
django.setup()

from api.models import Websites, Categories, JobOffers

def transform_date(publication_date):
    months = {
        'stycznia': '01', 'lutego': '02', 'marca': '03', 'kwietnia': '04', 'maja': '05', 'czerwca': '06',
        'lipca': '07', 'sierpnia': '08', 'września': '09', 'października': '10', 'listopada': '11', 'grudnia': '12'
    }

    publication_date = publication_date.replace('Odświeżono dnia ', '')

    if "dzisiaj" in publication_date.lower():
        return datetime.today().date().isoformat()
    elif "wczoraj" in publication_date.lower():
        return (datetime.today() - timedelta(days=1)).date().isoformat()
    else:
        for month_pl, month_num in months.items():
            if month_pl in publication_date:
                publication_date = publication_date.replace(month_pl, month_num)
                break
        try:
            date = datetime.strptime(publication_date, '%d %m %Y').date()
            return date.isoformat()
        except ValueError as e:
            return None


def scrapp(site_url, category_name, category_path):
    print(f"Rozpoczynanie scrapowania kategorii: {category_name}")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    current_page = 1

    Category, created = Categories.objects.get_or_create(Category_name=category_name)
    Website, created = Websites.objects.get_or_create(Website_name="olx", Website_url=site_url)

    while True:
        if current_page == 1:
            page_url = f"{site_url}/praca/{category_path}/"
        else:
            page_url = f"{site_url}/praca/{category_path}/?page={current_page}"
        
        driver.get(page_url)
        print(f"Aktualna strona: {page_url}")

        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cy="l-card"]')))
        except TimeoutException:
            break
  
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        offers = soup.find_all('div', {'data-cy': 'l-card'})

        for offer in offers:
            position_element = offer.find('h6', class_='css-1b96xlq')
            if not position_element:
                continue  
            position = position_element.get_text(strip=True)

            divs = offer.find_all('div', class_='css-9yllbh')
            earnings = location = working_hours = job_type = None
            for div in divs:
                if div.find('p', class_='css-1jnbm5x'):
                    earnings = div.get_text(strip=True)
                elif div.find('span', class_='css-d5w927'): 
                    location = div.get_text(strip=True)
                else:
                    text = div.get_text(strip=True)
                    if any(etat in text.lower() for etat in ['pełny etat', 'część etatu', 'współpraca b2b', 'dodatkowa']):
                        working_hours = text
                    elif 'umowa' in text.lower() or 'samozatrudnienie' in text.lower() or 'inny' in text.lower():
                            job_type = text

            location_details = get_location_details(location)

            min_earnings, max_earnings, average_earnings, _ = parse_earnings(earnings)
            earnings_type = get_earnings_type(min_earnings, max_earnings)

            province = get_province(location)

            job_model_element = offer.find('span', string=lambda x: x and x.startswith('Miejsce pracy:'))
            job_model = job_model_element.get_text(strip=True).split(': ')[1] if job_model_element else None

            publication_date_text = offer.find('p', class_='css-l3c9zc').get_text(strip=True) if offer.find('p', class_='css-l3c9zc') else None
            publication_date = transform_date(publication_date_text)

            link = offer.find('a')['href'] if offer.find('a') else None
            full_link = site_url + link if link else None

            existing_offer = JobOffers.objects.filter(
                Position=position, 
                Location=location
            ).first()

            if not existing_offer:
                print(f"Pozycja: {position},  Lokalizacja: {location}, Województwo: {province}, Data: {publication_date}, Zarobki: {earnings}")
                new_offer=JobOffers(
                    Position=position,
                    Location=location,
                    Location_Latitude=location_details['latitude'],
                    Location_Longitude=location_details['longitude'],
                    Province=province,
                    Job_type=job_type,
                    Job_model=job_model,
                    Working_hours=working_hours,
                    Earnings=earnings,
                    Min_Earnings=min_earnings,
                    Max_Earnings=max_earnings,
                    Average_Earnings=average_earnings,
                    Earnings_Type=earnings_type,
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

        next_page_exists = driver.find_elements(By.CSS_SELECTOR, 'a[data-cy="pagination-forward"]')
        if not next_page_exists:
            print("Brak kolejnych stron, kończenie scrapowania.")
            break
        current_page += 1

    driver.quit()

categories = {
    "Administracja biurowa": "administracja-biurowa",
    "Badania i rozwój": "badania-rozwoj",
    "Budownictwo / Remonty / Geodezja": "budowa-remonty",
    "Dostawca, kurier miejski": "dostawca-kurier-miejski",
    "Internet / e-Commerce": "e-commerce-handel-internetowy",
    "Nauka / Edukacja / Szkolenia": "edukacja",
    "Energetyka": "energetyka",
    "Finanse / Ekonomia / Księgowość": "finanse-ksiegowosc",
    "Franczyza / Własny biznes": "franczyza-wlasna-firma",
    "Fryzjerstwo, kosmetyka": "fryzjerstwo-kosmetyka",
    "Hotelarstwo / Gastronomia / Turystyka": "gastronomia",
    "HR": "hr",
    "Hostessa, roznoszenie ulotek": "hostessa-roznoszenie-ulotek",
    "Hotelarstwo / Gastronomia / Turystyka": "hotelarstwo",
    "Inżynieria": "inzynieria",
    "IT / telekomunikacja / Rozwój oprogramowania / Administracja": "informatyka",
    "Transport / Spedycja / Logistyka / Kierowca": "kierowca",
    "Transport / Spedycja / Logistyka / Kierowca": "logistyka-zakupy-spedycja",
    "Marketing i PR": "marketing-pr",
    "Motoryzacja": "mechanika-lakiernictwo",
    "Motoryzacja": "montaz-serwis",
    "Obsługa klienta i call center": "obsluga-klienta-call-center",
    "Ochrona": "ochrona",
    "Opieka": "opieka",
    "Praca za granicą": "praca-za-granica",
    "Prace magazynowe": "prace-magazynowe",
    "Pracownik sklepu": "pracownik-sklepu",
    "Produkcja": "produkcja",
    "Rolnictwo i ogrodnictwo": "rolnictwo-i-ogrodnictwo",
    "Sprzątanie": "sprzatanie",
    "Sprzedaż": "sprzedaz",
    "Wykładanie i ekspozycja towaru": "wykladanie-ekspozycja-towaru",
    "Medycyna / Zdrowie / Uroda / Rekreacja": "zdrowie",
    "Pozostałe oferty pracy": "inne-oferty-pracy",
    "Praktyki / staże": "praktyki-staze",
    "Kadra kierownicza": "kadra-kierownicza",
    "Praca sezonowa": "praca-sezonowa",
    "Praca dla seniorów": "zapraszamy-seniorow",
    "Praca dodatkowa": "praca-dodatkowa",
   }

site_url = "https://www.olx.pl"
for category_name, category_path in categories.items():
        scrapp(site_url, category_name, category_path)