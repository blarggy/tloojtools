import io
import os.path
from requests.exceptions import HTTPError
import requests
import json
import logging
import time
import pandas as pd
from nfl.constants import DATABASE_DIRECTORY
import nfl_data_py as nfl
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from nfl.utils import is_file_older_than_one_week
from nfl.utils import validate_file
from nfl.utils import create_backup
from nfl.utils import logging_steup


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


class Database:
    """
    Instantiate with a json database file, use methods to maniuplate database after stats files are created
    """
    def __init__(self, database_file):
        self.database_file = database_file

    # @TODO: Sleeper's API should return this info but it doesn't give everything, so this needs to be set manually...
    stat_weight = {
        'Passing_Yds': 0.04,  # Passing_Yds.1 is due to yards lost due to sacks. We don't care about that.
        'Passing_TD': 4,
        'Scoring_TD': 6,
        'Scoring_Sfty': 8,
        'Receiving_Rec': 0.5,
        'Rushing_Yds': 0.1,
        'Receiving_Yds': 0.1,
        'Kick Returns_Rt': 0.04,
        'Punt Returns_Ret': 0.04,
        'Passing_Int': -2,
        'Sk': 4,
        'Def Interceptions_Int': 6,
        'Def Interceptions_PD': 4,
        'Tackles_QBHits': 1,
        'Tackles_TFL': 2,
        'Tackles_Solo': 1,
        'Tackles_Ast': 0.5,
        'Fumbles_Fmb': -1,
        'Fumbles_FL': -1,
        'Fumbles_Yds': 0.1,
        'Def Interceptions_Yds': 0.1,
        "blocked_kick": 8,  # PFR doesn't include this information. Maybe someday.
        'Fumbles_FF': 4,
        'Fumbles_FR': 4
    }

    def calculate_fantasy_points(self):
        """
        Calculate the impact of a player's stats on their team (assumes 'gamelogs' database)
        """

        def get_player_stats(database_data, player_data_dict, process_stats_func):
            for roster in database_data:
                for player_data in roster['players_data']:
                    for player_name, stats in player_data.items():
                        player_id = stats[0]['player_id']
                        # Use a unique key to identify each player to avoid situations where players have identical names
                        unique_key = f"{player_name}_{player_id}"
                        player_stats = stats[1]
                        player_data_dict.setdefault(unique_key, [])
                        for year, stats_table in player_stats.items():
                            process_stats_func(unique_key, stats_table)

        def get_points(unique_key, stats_table):
            player_name, player_id = unique_key.rsplit('_', 1)
            logging.info(f"Calculating fantasy points for {player_name} with ID {player_id}")
            for column_header, week_stats in stats_table.items():
                logging.debug(f"{column_header=}, {week_stats=}")
                # TODO: use utils.rename_keys_in_json() to clean up column headers before calling this
                if column_header.startswith("Unnamed"):
                    stat_key = column_header.split('_')[-1]
                else:
                    stat_key = column_header
                logging.debug(f"{stat_key=}")
                stats_dict = {}
                if stat_key in self.stat_weight:
                    for index, stat_value in week_stats.items():
                        try:
                            fantasy_points = self.stat_weight[stat_key] * float(stat_value)
                        except ValueError:
                            fantasy_points = 0
                        stats_dict[index] = round(fantasy_points, 2)
                        logging.debug(f"{index=}, {stat_key=}, {stat_value=}, {fantasy_points=}")
                if stats_dict != {}:
                    player_data_dict[unique_key].append({stat_key: stats_dict})

        def write_points_to_file(unique_key, stats_table):
            if unique_key in player_data_dict:
                fantasy_points_dict = player_data_dict[unique_key][-1]
                if 'combined_stats' in fantasy_points_dict:
                    stats_table["fantasy_points"] = fantasy_points_dict['combined_stats']

        with open(self.database_file) as file:
            database_data = json.load(file)

        create_backup(os.path.abspath(file.name))

        logging.info(f"Calculating fantasy points for each player in {self.database_file}")
        player_data_dict = {}

        # Calculate fantasy points for each player, each section is scored based on the stat_weight dictionary
        get_player_stats(database_data, player_data_dict, get_points)

        logging.debug(f"Before combining stats {player_data_dict=}")

        # Add up all stats for each player to get total fantasy points
        for player_name, stats in player_data_dict.items():
            combined_stats = {}

            for stat_column in stats:
                for stat, value_dict in stat_column.items():
                    for index, value in value_dict.items():
                        if index in combined_stats:
                            combined_stats[index] += round(value, 2)
                        else:
                            combined_stats[index] = round(value, 2)

            player_data_dict[player_name].append({"combined_stats": combined_stats})

        logging.debug(f"After combining stats {player_data_dict=}")

        # Write the fantasy points for each respective player to the existing json file from player_data_dict
        get_player_stats(database_data, player_data_dict, write_points_to_file)

        with open(self.database_file, 'w') as file:
            json.dump(database_data, file, indent=4)

    def calculate_seasonal_impact(self):
        """
        Calculate the impact of a player's stats on their team (assumes 'seasonal' database)
        """
        pass


if __name__ == '__main__':
    logging_steup()
    Database('../data/2023_gamelogs_leagueid_1075600889420845056.json').calculate_fantasy_points()
