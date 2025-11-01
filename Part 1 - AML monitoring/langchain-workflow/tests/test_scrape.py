# mas_pdf_scraper_test.py
import requests
from bs4 import BeautifulSoup

# MAS Notices URL
MAS_URL = "https://www.mas.gov.sg/regulation/banking/regulations-and-guidance"

def fetch_mas_pdfs(url):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error fetching URL: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    pdf_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().endswith('.pdf'):
            # Make full URL if relative
            full_url = href if href.startswith('http') else f"https://www.mas.gov.sg{href}"
            pdf_links.append(full_url)
    return pdf_links

if __name__ == "__main__":
    pdfs = fetch_mas_pdfs(MAS_URL)
    print(f"Found {len(pdfs)} PDF links:")
    for idx, link in enumerate(pdfs, 1):
        print(f"{idx}: {link}")
