from bs4 import BeautifulSoup


def html_to_text(html_string: str):
    _string = html_string.replace("</p>", "</p>\n").replace("<div", "\n<div").replace("\r", " ").replace("<br>", "\n")
    soup = BeautifulSoup(_string, 'html.parser')
    text = soup.get_text(strip=False)
    return text
