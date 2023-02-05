from bs4 import BeautifulSoup


def html_to_text(html_string):
    soup = BeautifulSoup(html_string, 'html.parser')
    text = soup.get_text(strip=True)
    return text