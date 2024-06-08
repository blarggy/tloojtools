import io
from requests.exceptions import HTTPError

import requests

import json
import logging
import time
import traceback

import pandas
import pandas as pd

import json_handler
from constants import DATABASE_DIRECTORY
import nfl_data_py as nfl
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import is_file_older_than_one_week
from utils import validate_file


class Stats:
    """
    Instantiate with year, position (either "passing", "scrimmage" or "defense")
    """
    def __init__(self, year, position=None, pfr_player_id=None):
        self.year = year
        self.position = position
        self.pfr_player_id = pfr_player_id
        self.PFR_STATS_URL = f"https://www.pro-football-reference.com/years/{self.year}/{self.position}.htm"

    def create_stats(self, validate=True):
        def seasonal_data():
            url = self.PFR_STATS_URL
            """
            Without Selenium
            """
            # df = pd.read_html(url)[0]
            # if self.position != "passing":
            #     df[('Unnamed: 1_level_0', 'Player')] = df[('Unnamed: 1_level_0', 'Player')].str.replace('*', '').str.replace('+', "")
            # else:
            #     df['Player'] = df['Player'].str.replace('*', '').str.replace('+', "")

            """
            With Selenium
            """
            driver = webdriver.Chrome()
            driver.get(url)
            share_export = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Share & Export']"))
            )
            share_export.click()
            get_csv_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@tip='Get a link directly to this table on this page']"))
            )
            get_csv_button.click()
            if self.position == "passing":
                csv_type = "csv_passing"
                merge_headers = False
            elif self.position == "scrimmage":
                csv_type = "csv_receiving_and_rushing"
                merge_headers = True
            elif self.position == "defense":
                csv_type = "csv_defense"
                merge_headers = True
            pre_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, csv_type))
            )
            pre_text = pre_element.get_attribute('innerText')
            csv_data = pre_text.split('--- When using SR data, please cite us and provide a link and/or a mention.')[1]
            if merge_headers:
                df = pd.read_csv(io.StringIO(csv_data), header=[0, 1])
            else:
                df = pd.read_csv(io.StringIO(csv_data))
            df = df.fillna("0")
            df = nfl.clean_nfl_data(df)
            df.to_json(file_name, orient='records', indent=4)
            return df

        file_name = f"{DATABASE_DIRECTORY}/nfl_stats_{self.position}_{self.year}.json"
        if validate and validate_file(file_name):
            if is_file_older_than_one_week(file_name):
                seasonal_data()
            else:
                print(f"{file_name} is fresh. Skipping data import.")
                df = pd.read_json(file_name)
                return df
        else:
            seasonal_data()

    def gamelogs_data(self):
        # year = self.year
        # pfr_player_id = self.pfr_player_id
        # url = f"https://www.pro-football-reference.com/players/{pfr_player_id[0]}/{pfr_player_id}/gamelog/{year}/"
        # logging.info(f"Getting gamelogs for {url=}")
        # print(f"Getting gamelogs for {url=}")
        # df = pd.read_html(url)[0]
        # df = df.fillna("0")
        # return df
        year = self.year
        pfr_player_id = self.pfr_player_id
        url = f"https://www.pro-football-reference.com/players/{pfr_player_id[0]}/{pfr_player_id}/gamelog/{year}/"
        logging.info(f"Getting gamelogs for {url=}")
        print(f"Getting gamelogs for {url=}")

        max_retries = 5
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                response = requests.get(url)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)

                df = pd.read_html(io.StringIO(response.text))[0]
                df = df.fillna("null")
                return df

            except HTTPError as http_err:
                if response.status_code in [503, 504]:  # Check for Service Unavailable or Gateway Timeout
                    logging.error(f"HTTP error {response.status_code} occurred: {http_err}. Retrying {attempt + 1}/{max_retries}")
                    print(f"HTTP error {response.status_code} occurred: {http_err}. Retrying {attempt + 1}/{max_retries}")
                    time.sleep(retry_delay)

            except KeyboardInterrupt:
                logging.info("Process interrupted by user.")
                print("Process interrupted by user.")
                return None

        logging.error(f"Failed to retrieve gamelogs after {max_retries} attempts")
        print(f"Failed to retrieve gamelogs after {max_retries} attempts")
        return None





if __name__ == '__main__':
    # player_id_table = pandas.read_csv('json/player_id_table.csv')
    # player_name = "Michael Pittman"
    # player_id = "6819"
    # passing_stats = Stats("2023", "passing").create_stats()
    # scrimmage_stats = Stats("2023", "scrimmage").create_stats()
    # defense_stats = Stats("2023", "defense").create_stats()
    # print(passing_stats.loc[passing_stats['Player'] == player_name].to_string())
    # player_pfr_id = player_id_table.loc[player_id_table['sleeper_id'] == int(player_id), 'pfr_id'].values[0]
    # print(player_pfr_id)
    # player_scrimmage_stats = scrimmage_stats.loc[
    #     scrimmage_stats['(\'-additional\', \'-9999\')'].str.contains(str(player_pfr_id))]
    # player_scrimmage_stats.to_json()
    # print(type(player_scrimmage_stats))
    # print(player_scrimmage_stats)
    # print(scrimmage_stats.loc[scrimmage_stats[('Unnamed: 1_level_0', 'Player')].str.contains(player_name)].to_json())
    # print(defense_stats.loc[defense_stats[('Unnamed: 1_level_0', 'Player')] == player_name].to_string())

    # json_handler.CustomJSONEncoder.normalize_seasonal_json_database_to_excel_format("json/combined_data.json")

    # Stats(year='2023', pfr_player_id='BrowJa09').gamelogs_data()
    pass