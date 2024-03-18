import sys
import re
import os
from datetime import datetime
import django
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from helping_functions import parse_earnings, get_province, get_location_details, get_earnings_type

project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Backend.settings")
django.setup()

from api.models import Websites, Categories, JobOffers
        
def transform_date(publication_date):
    months = {
        'stycznia': '01',
        'lutego': '02',
        'marca': '03',
        'kwietnia': '04',
        'maja': '05',
        'czerwca': '06',
        'lipca': '07',
        'sierpnia': '08',
        'września': '09',
        'października': '10',
        'listopada': '11',
        'grudnia': '12'
    }

    try:
        data_str = publication_date.replace('Opublikowana: ', '')
        for polish_month, month_num in months.items():
            if polish_month in data_str:
                data_str = data_str.replace(polish_month, month_num)
                break

        data_obj = datetime.strptime(data_str, '%d %m %Y')
        return data_obj.strftime('%Y-%m-%d')
    except ValueError as e:
        return None


def scrapp(site_url, category_name, category_path):
    print(f"Rozpoczynanie scrapowania kategorii: {category_name}")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    current_page = 1
    
    Category, created = Categories.objects.get_or_create(Category_name=category_name)
    Website, created = Websites.objects.get_or_create(Website_name="pracuj", Website_url=site_url)
    
    while True:
        if current_page == 1:
            page_url = f"{site_url}/praca/{category_path}"
        else:
            page_url = f"{site_url}/praca/{category_path}?pn={current_page}"

        driver.get(page_url)

        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'tiles_c1m5bwec')))
        except TimeoutException:
            break

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        offers = soup.find_all('div', class_='tiles_c1m5bwec')

        for offer_index, offer in enumerate(offers, 1):
            position_element = offer.find('h2', attrs={'data-test': 'offer-title'})
            if not position_element:
                continue
            position = position_element.get_text(strip=True)

            firm = offer.find('h4', attrs={'data-test': 'text-company-name'}).get_text(strip=True) if offer.find('h4', attrs={'data-test': 'text-company-name'}) else None

            earnings = offer.find('span', attrs={'data-test': 'offer-salary'}).get_text(strip=True) if offer.find('span', attrs={'data-test': 'offer-salary'}) else None

            min_earnings, max_earnings, average_earnings, _ = parse_earnings(earnings)
            earnings_type = get_earnings_type(min_earnings, max_earnings)

            working_hours = offer.find('li', attrs={'data-test': 'offer-additional-info-1'}).get_text(strip=True) if offer.find('li', attrs={'data-test': 'offer-additional-info-1'}) else None

            info_elements = offer.find_all('li', class_='tiles_iwlrcdk')

            job_model = info_elements[-1].get_text(strip=True) if info_elements else None
            job_type = offer.find('li', attrs={'data-test': 'offer-additional-info-2'}).get_text(strip=True) if offer.find('li', attrs={'data-test': 'offer-additional-info-2'}) else None
            publication_date_text = offer.find('p', attrs={'data-test': 'text-added'}).get_text(strip=True) if offer.find('p', attrs={'data-test': 'text-added'}) else None
            publication_date = transform_date(publication_date_text)

            location_element = offer.find('h5', attrs={'data-test': 'text-region'})
            if location_element:
                location_text = location_element.get_text(strip=True)

                if re.search(r'\d+', location_text):
                    driver.execute_script("document.querySelectorAll('div.tiles_s1g23iln').forEach(button => button.click());")

                    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.tiles_lov4ye4')))

                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    offer = soup.find_all('div', class_='tiles_c1m5bwec')[offer_index-1]
                    additional_locations = offer.find_all('div', class_='tiles_lov4ye4')

                    for lok in additional_locations:
                        location = lok.a.get_text(strip=True)
                        link = lok.a['href']

                        location_details = get_location_details(location)
                        print(location_details)

                        province = get_province(location)

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
                            continue
                    driver.execute_script("document.querySelectorAll('div.tiles_s1g23iln').forEach(button => button.click());")
                else:
                    location = location_element.get_text(strip=True) if location_element else None
                    link = offer.find('a', attrs={'data-test': 'link-offer'})['href'] if offer.find('a', attrs={'data-test': 'link-offer'}) else None
                    
                    location_details = get_location_details(location)
                    print(location_details)

                    province = get_province(location)

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
                                Job_model=job_model,
                                Working_hours=working_hours,
                                Earnings=earnings,
                                Min_Earnings=min_earnings,
                                Max_Earnings=max_earnings,
                                Average_Earnings=average_earnings,
                                Date=publication_date,
                                Link=link,
                                Website=Website,
                                Category=Category
                            )
                        new_offer.save()
                        print(f"Zapisano nową ofertę pracy: {position} w {location}.")
                    else:
                        print("Oferta pracy już istnieje w bazie danych. Pomijanie.")
                        continue

        next_page_exists = driver.find_elements(By.CSS_SELECTOR, 'button[data-test="bottom-pagination-button-next"]')
        if not next_page_exists:
            print("Brak kolejnych stron, kończenie scrapowania.")
            break
        current_page += 1

    driver.quit()

categories = {
    "Administracja biurowa": "administracja%20biurowa;cc,5001",
    "Badania i rozwój": "badania%20i%20rozwój;cc,5002",
    "Bankowość": "bankowość;cc,5003",
    "BHP / Ochrona środowiska": "bhp%20ochrona%20środowiska;cc,5004",
    "Budownictwo / Remonty / Geodezja": "budownictwo;cc,5005",
    "Obsługa klienta i call center": "call%20center;cc,5006",
    "Doradztwo / Konsulting": "doradztwo%20konsulting;cc,5037",
    "Energetyka": "energetyka;cc,5036",
    "Nauka / Edukacja / Szkolenia": "edukacja%20szkolenia;cc,5007",
    "Finanse / Ekonomia / Księgowość": "finanse%20ekonomia;cc,5008",
    "Franczyza / Własny biznes": "franczyza%20własny%20biznes;cc,5009",
    "Hotelarstwo / Gastronomia / Turystyka": "hotelarstwo%20gastronomia%20turystyka;cc,5010",
    "Human Resources / Zasoby ludzkie": "human%20resources%20zasoby%20ludzkie;cc,5011",
    "Internet / e-Commerce": "internet%20e-commerce%20nowe%20media;cc,5013",
    "Inżynieria": "inżynieria;cc,5014",
    "IT / telekomunikacja / Rozwój oprogramowania / Administracja": "it%20-%20administracja;cc,5015",
    "IT / telekomunikacja / Rozwój oprogramowania / Administracja": "it%20-%20rozwój%20oprogramowania;cc,5016",
    "Kontrola jakości": "kontrola%20jakości;cc,5034",
    "Łańcuch dostaw": "łańcuch%20dostaw;cc,5017",
    "Marketing i PR": "marketing;cc,5018",
    "Media / Sztuka / Rozrywka": "media%20sztuka%20rozrywka;cc,5019",
    "Nieruchomości": "nieruchomości;cc,5020",
    "Obsługa klienta i call center": "obsługa%20klienta;cc,5021",
    "Praca fizyczna": "praca%20fizyczna;cc,5022",
    "Prawo": "prawo;cc,5023",
    "Produkcja": "produkcja;cc,5024",
    "Public Relations": "public%20relations;cc,5025",
    "Reklama / Grafika / Kreacja / Fotografia": "reklama%20grafika%20kreacja%20fotografia;cc,5026",
    "Sektor publiczny": "sektor%20publiczny;cc,5027",
    "Sprzedaż": "sprzedaż;cc,5028",
    "Transport / Spedycja / Logistyka / Kierowca": "transport%20spedycja%20logistyka;cc,5031",
    "Ubezpieczenia": "ubezpieczenia;cc,5032",
    "Zakupy": "zakupy;cc,5033",
    "Medycyna / Zdrowie / Uroda / Rekreacja": "zdrowie%20uroda%20rekreacja;cc,5035",
    "Pozostałe oferty pracy": "inne;cc,5012",
}

site_url = "https://www.pracuj.pl"
for category_name, category_path in categories.items():
    scrapp(site_url, category_name, category_path)