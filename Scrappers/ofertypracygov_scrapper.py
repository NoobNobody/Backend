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
from helping_functions import parse_earnings, get_province, get_location_details

project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Backend.settings")
django.setup()

from api.models import Websites, Categories, JobOffers

def transform_date(publication_date_text):
    if "dzisiaj" in publication_date_text.lower():
        return datetime.today().date().isoformat()
    elif "wczoraj" in publication_date_text.lower():
        return (datetime.today() - timedelta(days=1)).date().isoformat()
    else:
        days_ago_match = re.search(r'(\d+) dni', publication_date_text)
        if days_ago_match:
            days_num = int(days_ago_match.group(1))
            return (datetime.today() - timedelta(days=days_num)).date().isoformat()
    return None

def scrapp(site_url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    
    Category, created = Categories.objects.get_or_create(Category_name="GOV")
    Website, created = Websites.objects.get_or_create(Website_name="oferty.praca.gov", Website_url=site_url)

    while True:
        page_url = f"{site_url}/portal/index.cbop#/listaOfert"
        driver.get(page_url)
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'oferta-pozycja-kontener-pozycji-min')))
        except TimeoutException:
            break
                      
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        offers_container = soup.find_all('div', class_='oferta-pozycja-kontener-pozycji-min')
        all_offers = []

        for container in offers_container:
            offers = container.find_all('div', class_='dane')
            all_offers.extend(offers)

        base_url = "https://oferty.praca.gov.pl/portal/index.cbop"

        for index, offer in enumerate(all_offers, 2):
            position_element = offer.find('span', class_='stanowisko')
            if not position_element:
                continue  
            position = position_element.get_text(strip=True)

            location = (offer.find('span', class_='miejscePracyCzlonPierwszy').get_text(strip=True) + offer.find('span', class_='miejscePracyCzlonDrugi').get_text(strip=True)) if offer.find('span', class_='miejscePracyCzlonPierwszy') and offer.find('span', class_='miejscePracyCzlonDrugi') else None

            location_details = get_location_details(location)
            print(location_details)

            province = get_province(location)

            job_type = offer.find('span', class_='skroconyRodzajZatrudnienia').get_text(strip=True) if offer.find('span', class_='skroconyRodzajZatrudnienia') else None

            firm = offer.find('span', class_='pracodawca').get_text(strip=True) if offer.find('span', class_='pracodawca') else None

            publication_date_text = offer.find('span', class_='dataDodania').get_text(strip=True) if offer.find('span', class_='dataDodania') else None
            publication_date = transform_date(publication_date_text)

            link = offer.find('a', class_='oferta-pozycja-szczegoly-link')['href'] if offer.find('a', class_='oferta-pozycja-szczegoly-link') else None
            full_link = base_url + link if link else None  
                 
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
                    Location_Latitude=location_details['latitude'],
                    Location_Longitude=location_details['longitude'],
                    Province=province,
                    Firm=firm,
                    Job_type=job_type,
                    Date=publication_date,
                    Link=full_link,
                    Website=Website,
                    Category=Category
                )
                new_offer.save()
                print(f"Zapisano nową ofertę pracy: {position} w {location}.")
            else:
                print("Oferta pracy już istnieje w bazie danych. Pomijanie.")

        next_page_exists = driver.find_elements(By.CSS_SELECTOR, 'button.oferta-lista-stronicowanie-nastepna-strona.active')
        if not next_page_exists:
            print("Brak kolejnych stron, kończenie scrapowania.")
            break
        
        driver.execute_script(
            "var nextPageButton = document.querySelector('button.oferta-lista-stronicowanie-nastepna-strona');"
            "if (nextPageButton) { nextPageButton.click(); }"
        )

    driver.quit()    

site_url = "https://oferty.praca.gov.pl"
scrapp(site_url)