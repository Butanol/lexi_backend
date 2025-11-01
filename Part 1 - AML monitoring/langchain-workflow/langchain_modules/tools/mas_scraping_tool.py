from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
import requests
# attempt local import of detector; allow running as script by falling back
try:
    from .pdf_change_detector import compare_with_previous
except Exception:
    try:
        from langchain_modules.tools.pdf_change_detector import compare_with_previous
    except Exception:
        compare_with_previous = None

def fetch_mas_pdfs_with_selenium(url, pattern="mas-notice-626"):
    # Setup Selenium WebDriver (using Chrome)
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")

    # Initialize the WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        # Open the URL
        driver.get(url)

        # Wait for the page to load completely (optional)
        driver.implicitly_wait(5)

        # Find all anchor (<a>) tags on the page
        anchor_tags = driver.find_elements(By.TAG_NAME, "a")

        # Filter out the links that point to PDFs and contain the pattern
        pdf_links = []
        for a in anchor_tags:
            href = a.get_attribute("href")
            if href and href.lower().endswith('.pdf') and pattern in href.lower():
                pdf_links.append(href)

        return pdf_links

    except Exception as e:
        print(f"Error: {e}")
        return []

    finally:
        # Close the driver
        driver.quit()

# Function to download and save the first PDF to a folder
def download_pdf(pdf_url, save_folder="downloads"):
    # Make sure the save folder exists
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    # Get the PDF file name from the URL (e.g., mas-notice-626.pdf)
    pdf_name = pdf_url.split("/")[-1]

    # Path where the PDF will be saved
    pdf_path = os.path.join(save_folder, pdf_name)

    try:
        print(f"Attempting to download PDF from: {pdf_url}")

        # Define headers to simulate a browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/pdf",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

        # Send a GET request to download the PDF (with stream=True to handle large files)
        response = requests.get(pdf_url, stream=True, headers=headers, allow_redirects=True)

        # Debugging: print response status and headers
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Content-Type: {response.headers.get('Content-Type')}")
        print(f"Final URL after redirection: {response.url}")

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Check if the content type is 'application/pdf'
            if 'application/pdf' in response.headers.get('Content-Type', ''):
                # Save the PDF to the specified folder
                with open(pdf_path, 'wb') as f:
                    # Write the content in chunks to avoid memory issues with large PDFs
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:  # Filter out keep-alive new chunks
                            f.write(chunk)
                print(f"Downloaded and saved the PDF: {pdf_path}")
                # After download, run the PDF change detector if available
                if compare_with_previous is not None:
                    try:
                        # Use the downloader's save_folder as the logs/temp dir so
                        # comparisons and archives are colocated with the downloaded file.
                        result = compare_with_previous(pdf_path, logs_temp_dir=save_folder)
                        print(f"PDF change detector result: {result}")
                    except Exception as e:
                        print(f"PDF change detector failed: {e}")
            else:
                print(f"Content is not a PDF: {pdf_url} - Received content type: {response.headers.get('Content-Type')}")
        else:
            print(f"Failed to download the PDF. Status code: {response.status_code}")

    except Exception as e:
        print(f"Error downloading the PDF: {e}")
        
if __name__ == "__main__":
    MAS_URL = "https://www.mas.gov.sg/regulation/notices/notice-626"
    
    # Fetch the PDF links from the page
    pdfs = fetch_mas_pdfs_with_selenium(MAS_URL)

    # Print the found PDF links
    print(f"Found {len(pdfs)} PDF links:")
    for idx, link in enumerate(pdfs, 1):
        print(f"{idx}: {link}")

    # If there are PDFs found, download the first one
    if pdfs:
        download_pdf(pdfs[0], save_folder="Part 1 - AML monitoring/langchain-workflow/logs/temp")  # You can change "downloads" to any folder you prefer

