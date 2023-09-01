import os
import csv

import requests
from bs4 import BeautifulSoup


class ScrapingHandler:
    def __init__(self, url, folder_path, course, year):
        self.url = url
        self.folder_path = folder_path
        self.course = course
        self.year = year
        self.subdirectory = f"{folder_path}/{course}/{year}"
        if not os.path.exists(self.subdirectory):
            os.makedirs(self.subdirectory)

    def scrape_data(self):
        response = requests.get(self.url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        tables = soup.find_all('table')
        filenames = []
        for i, table in enumerate(tables):
            file_name = f"scraped_data_tab_{i + 1}_{self.course}_{self.year}.csv"
            filenames.append(file_name)
            with open(
                f"{self.subdirectory}/{file_name}",
                'w',
                newline='',
                encoding='utf-8',
            ) as csvfile:
                csvwriter = csv.writer(csvfile)
                for row in table.find_all('tr'):
                    csv_row = []
                    for cell in row.find_all(['td', 'th']):
                        csv_row.append(cell.get_text())
                    csvwriter.writerow(csv_row)
        return filenames
