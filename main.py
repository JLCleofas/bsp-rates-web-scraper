#!/path/to/project/.venv/bin/python
import time
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright
from dotenv import dotenv_values
from jinja2 import Environment, FileSystemLoader

secrets = dotenv_values('.env')

### CONFIGURATION ###
TARGET_URL = secrets['TARGET_URL']
RECIPIENT_EMAIL = secrets['RECIPIENT_EMAIL']
CC_EMAIL = secrets['CC_EMAIL']
SENDER_EMAIL = secrets['SENDER_EMAIL']
SENDER_PASSWORD = secrets['SENDER_PASSWORD']
SMTP_SERVER = secrets['SMTP_SERVER']
SMTP_PORT: int = secrets['SMTP_PORT']

### END CONFIGURATION ###

### CONFIGURATION VALIDATION ###
if not SENDER_EMAIL or not SENDER_PASSWORD:
    raise ValueError("Missing email credentials")

if not SMTP_SERVER or not SMTP_PORT:
    raise ValueError("Missing SMTP server and port")

### END CONFIGURATION VALIDATION ###
### SETUP JINJA2 ENVIRONMENT ###
env = Environment(loader=FileSystemLoader('templates'))

def send_email(data, date):
    if not data:
        return 'No data to send'

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Cc'] = CC_EMAIL
    msg['Subject'] = f"BSP Reference Rates for USD, JPY, and SGD dated {time.strftime('%B %d, %Y')}"

    # Build HTML Table
    headers = list(data[0].keys())
    table_header = "".join([f"<th>{h}</th>" for h in headers])
    
    table_rows = ""
    for row in data:
        row_html = "".join([f"<td>{row.get(h, '')}</td>" for h in headers])
        table_rows += f"<tr>{row_html}</tr>"
    ### Render HTML Table ###
    template = env.get_template('rates.html')
    html_content = template.render(
        table_header=table_header,
        table_rows=table_rows,
        date=date
    )

    msg.attach(MIMEText(html_content, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print(f"Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")


def run_job():
    print(f'Starting scrape job at {time.strftime("%Y-%m-%d %H:%M:%S")}...')

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                # Set User-agent to avoid being blocked
                page.set_extra_http_headers({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'})
                print(f'Navigating to {TARGET_URL}...')
                page.goto(TARGET_URL, timeout=30000)
                print(f'Scrape job completed successfully at {time.strftime("%Y-%m-%d %H:%M:%S")}')
                # Wait for the exchange rate table to be present in the DOM
                page.wait_for_selector('table#ExRate', timeout=10000)
                # page.wait_for_selector('td#id', timeout=20000)
                content = page.content()
                browser.close()
            except Exception as e:
                print(f'Scrape job failed at {time.strftime("%Y-%m-%d %H:%M:%S")}: {e}')

        # Parsing the HTML content
        soup = BeautifulSoup(content, "html.parser")
        table = soup.find("table", {"id": "ExRate"})
        if not table:
            print('Table with id="ExRate" not found.')
            return

        data = []
        rows = table.find('tbody', {"id": "tb1"}).find_all('tr')

        #Extract date from the DOM of BSP Rates website
        date_element = table.find('td', {"id": "date"})
        date = date_element.get_text(strip=True) if date_element else "Unknown date"

        print(f'Date of rates: {date}')

        thead = table.find('thead', {"id": "2"})
        headers = [cell.get_text(strip=True) for cell in thead.find_all('td')] if thead else []

        # Iterate over data rows
        for row in rows:
            cols = row.find_all('td')
            row_data = {}

            for i, col in enumerate(cols):
                if i < len(headers):
                    row_data[headers[i]] = col.get_text(strip=True)

            if row_data['COUNTRY'] in ['1 UNITED STATES', '2 JAPAN', '7 SINGAPORE']:
                data.append(row_data)

        if data:
            send_email(data, date)
        else:
            print('No data to send.')

    except Exception as e:
        print(f'Scrape job failed at {time.strftime("%Y-%m-%d %H:%M:%S")}: {e}')


###  SCHEDULE JOB TO RUN EVERY DAY AT 9:00 AM ###
if __name__ == "__main__":
    print("BSP rates Web Scraper starting...")

    run_job()

