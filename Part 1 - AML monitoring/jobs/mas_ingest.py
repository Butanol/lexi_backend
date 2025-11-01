import requests, re, json, datetime
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
from jigsaw import DataProductWriter   # Jigsaw SDK

BASE = "https://www.mas.gov.sg"
NOTICE_URL = "https://www.mas.gov.sg/regulation/notices/626"

def extract_pdf_urls():
    soup = BeautifulSoup(requests.get(NOTICE_URL).text, "html.parser")
    return [
        (BASE + a["href"]) if a["href"].startswith("/") else a["href"]
        for a in soup.select("a[href$='.pdf']")
    ]

def parse_pdf(url):
    pdf_bytes = requests.get(url).content
    text = extract_text(pdf_bytes)
    return text

def split_rules(text):
    sections = re.split(r"\n(?=\d+\.)", text)
    rules = []
    for sec in sections:
        sec = sec.strip()
        if not re.match(r"^\d+\.", sec): continue
        num = sec.split()[0].replace(".", "")
        rules.append((f"MAS-626-R{num}", sec))
    return rules

def summarize(text):
    t = text.lower()
    if "beneficial owner" in t: return "Verify Beneficial Ownership"
    if "customer due diligence" in t: return "Perform CDD"
    return text[:150] + "..."

def run():
    writer = DataProductWriter("mas_aml_rules")
    notice_version = datetime.date.today().isoformat()

    for pdf_url in extract_pdf_urls():
        text = parse_pdf(pdf_url)
        for rule_id, raw in split_rules(text):
            writer.write({
                "rule_id": rule_id,
                "notice_version": notice_version,
                "raw_text": raw,
                "summary": summarize(raw),
                "source_url": pdf_url,
                "ingested_at": datetime.datetime.utcnow().isoformat()
            })

    writer.commit()

if __name__ == "__main__":
    run()
