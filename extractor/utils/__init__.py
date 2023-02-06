import csv
import io
from datetime import datetime

from bs4 import BeautifulSoup


def html_to_text(html_string: str):
    _string = html_string.replace("</p>", "</p>\n").replace("<div", "\n<div").replace("\r", " ").replace("<br>", "\n")
    soup = BeautifulSoup(_string, 'html.parser')
    text = soup.get_text(strip=False)
    return text


def _save_to_csv(data):
    csv_file = io.StringIO()
    writer = csv.writer(csv_file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    writer.writerow(["Subject", "receveid_date", "raw_body", "categories"])
    for email in data:
        receveid_date = email.receveid_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(email.receveid_date,
                                                                                        datetime) else email.receveid_date
        writer.writerow([email.subject, receveid_date, email.raw_body, email.categories])

    csv_file.seek(0)
    return csv_file