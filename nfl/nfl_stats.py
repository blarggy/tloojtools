import io
import os.path

from bs4 import BeautifulSoup
from requests.exceptions import HTTPError
import requests
import json
import logging
import time
import pandas as pd
from sleeper.model import League

import re

from nfl import utils
from nfl.constants import GLOBAL_NFL_PLAYER_ID_FILE
from nfl.utils import create_backup
from nfl.utils import logging_steup


class Stats:
    """
    Base class for NFL player stats.

    Attributes:
        year (int): The year for which stats are being fetched.
        pfr_player_id (str): The Pro-Football-Reference player ID.
    """

    def __init__(self, year=None, pfr_player_id=None):
        """
        Initializes the Stats class with the given year and player ID.

        Args:
            year (int): The year for which stats are being fetched.
            pfr_player_id (str, optional): The Pro-Football-Reference player ID. Defaults to None.
            PFR_PLAYER_PAGE_URL (str): The URL template for fetching base player page.
        """
        self.year = year
        self.pfr_player_id = pfr_player_id

    def check_players_birthday(self):
        try:
            pfr_player_page_url = f"https://www.pro-football-reference.com/players/{self.pfr_player_id[0]}/{self.pfr_player_id}.htm"
            logging.info(f"Getting birth date for {pfr_player_page_url=}")
            response = requests.get(pfr_player_page_url)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)

            soup = BeautifulSoup(response.text, 'html.parser')
            birth_date_element = soup.find('span\"', {'data-birth': True})

            if birth_date_element:
                return birth_date_element.get('data-birth')
            else:
                return None
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"An error occurred: {err}")

    def get_years_of_service(self):
        """
        Get the years of service for a player.
        return: list -> years of service
        """
        pfr_player_page_url = f"https://www.pro-football-reference.com/players/{self.pfr_player_id[0]}/{self.pfr_player_id}.htm"
        logging.info(f"Getting years of service for {pfr_player_page_url=}")
        df = self.query_pfr(pfr_player_page_url)
        logging.debug(f"get_years_of_service() {df=}")
        if df is not None:
            if ('Unnamed: 0_level_0', 'Year') in df.columns:
                years_of_service = df[('Unnamed: 0_level_0', 'Year')].tolist()
            elif 'Year' in df.columns:
                years_of_service = df['Year'].tolist()
            else:
                years_of_service = []

            # Extract only numeric parts of the year values and filter out data that isn't a year
            years_of_service = [re.sub(r'\D', '', item) for item in years_of_service if re.sub(r'\D', '', item).isdigit() and int(re.sub(r'\D', '', item)) > 1000]
            logging.info(f"Years of service for {self.pfr_player_id}: {years_of_service}")

            return years_of_service
        return []

    @staticmethod
    def query_pfr(url, max_retries=5, retry_delay=5):
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
                elif response.status_code == 404:
                    logging.error(f"HTTP error {response.status_code} occurred: {http_err}. {url=} is not valid.")
                    break
                elif response.status_code == 429:
                    logging.error(f"HTTP error {response.status_code} occurred: {http_err}. Too many requests. Wait for a while.")
                    break

            except ValueError as val_err:
                logging.error(f"query_pfr() Value error occurred: {val_err}. {url=} contains no tables.")
                df = pd.DataFrame()
                return df

            except KeyboardInterrupt:
                logging.info("Process interrupted by user.")
                print("Process interrupted by user.")
                return None

        logging.error(f"Failed to retrieve data from {url} {response.status_code}")
        print(f"Failed to retrieve data from {url} {response.status_code}")
        return None

    def gamelogs_data(self, rookie_year=None):
        """
        Fetches game logs data for the player for the specified year.

        Returns:
            DataFrame: A pandas DataFrame containing the gamelogs data.
            None: If the data could not be fetched after multiple attempts.
        """
        year = self.year
        pfr_player_id = self.pfr_player_id
        url = f"https://www.pro-football-reference.com/players/{pfr_player_id[0]}/{pfr_player_id}/gamelog/{year}/"
        logging.info(f"Getting gamelogs for {url=}")
        print(f"Getting gamelogs for {url=}")

        return self.query_pfr(url)

    @staticmethod
    def fetch_game_log_data(owner_data, player_data, player_id, player_id_table, update_years=None):
        """
        Gets the gamelogs data for each player from PFR on the roster and adds it to the owner_data dictionary.
        :param owner_data: dict w/ keys: owner_id, display_name, team_name, players_data (list)
        :param player_data: All NFL player data from sleeper's api as json object
        :param player_id: Sleeper player ID
        :param player_id_table: from nfl api for mapping IDs to names
        :param update_years: str, int or list, List of year(s) to update
        :return:
        """
        if update_years:
            if type(update_years) is str:
                update_years = [update_years]
            if type(update_years) is int:
                update_years = [str(update_years)]

        def normalize_game_log_data(game_log_data, year):
            """
            Normalizes the game log data by converting tuples to lists and renaming columns for json serialization
            Args:
                game_log_data (pd.DataFrame): The game log data to be normalized.
                year (str): The year for which the data is being normalized.
            Returns:
                dict: The normalized game log data.
            """
            game_log_data = game_log_data.apply(lambda col: col.map(lambda x: list(x) if isinstance(x, tuple) else x))
            game_log_data.columns = ['_'.join(map(str, col)).strip() for col in game_log_data.columns.values]
            stats = {f"{year}_stats": game_log_data.to_dict()}
            return stats

        def update_stats(owner_data, player_name, stats):
            """
            Replaces or appends an item in the list dictionary with {player_name: [stats]}.

            Args:
                owner_data (dict): The owner data dictionary containing the players_data list.
                player_name (str): The name of the player.
                stats (dict): The stats to be added for the player.

            Returns:
                None
            """
            for i, item in enumerate(owner_data):
                if isinstance(item, dict) and player_name in item:
                    player_stats = item[player_name]
                    year_key = list(stats.keys())[0]
                    for stat in player_stats:
                        if year_key in stat:
                            stat[year_key] = stats[year_key]
                            logging.info(f'Updating stats for {player_name} for {year_key}')
                            break
                    else:
                        player_stats.append(stats)
                        logging.info(f'Appending stats for {player_name} for {year_key}')
                    break

        def sort_players_data(unsorted_data):
            def sort_key(item):
                key = list(item.keys())[0]
                if key == "hashtag":
                    return 0, key
                elif key.endswith("_stats"):
                    year = int(key.split("_")[0])
                    return 1, year
                else:
                    return 2, key

            unsorted_data.sort(key=sort_key)

        def fetch_and_process_game_logs(pfr_player_id, update_years, owner_data, player_name):
            if update_years:
                years = update_years
            else:
                years = Stats(pfr_player_id=pfr_player_id).get_years_of_service()
            for year in years:
                game_log_data = Stats(year=int(year), pfr_player_id=pfr_player_id).gamelogs_data()
                stats = normalize_game_log_data(game_log_data, year)
                player_exists = any(player_name in player for player in owner_data["players_data"])
                if player_exists:
                    # Update stats if player_name exists
                    update_stats(owner_data["players_data"], player_name, stats)
                else:
                    # Append new player data if player_name does not exist
                    owner_data["players_data"].append({player_name: [stats]})
                time.sleep(5)  # respectfully wait

        unique_cases = {
            "5840": "AlleJo03",  # Josh Allen changed his name so his PFR ID is different than what I'd guess.
        }

        if player_id in player_data:
            player_name = player_id_table.loc[player_id_table['sleeper_id'] == int(player_id), 'name'].values[0]
            pfr_player_id = player_id_table.loc[player_id_table['sleeper_id'] == int(player_id), 'pfr_id'].values[0]
            player_info = player_data[player_id]
            if player_id in unique_cases:
                logging.info(f"Unique case for {player_name=} {player_id=}")
                pfr_player_id = unique_cases[player_id]
                fetch_and_process_game_logs(pfr_player_id, update_years, owner_data, player_name)
            # In the event a player's sleeper ID isn't in the player_id_table, try to guess the player's gamelogs page.
            elif type(pfr_player_id) is float:
                logging.error(f"{player_id=} doesn't have a PFR ID in the {GLOBAL_NFL_PLAYER_ID_FILE} file. Trying to find the gamelogs page by hand...")
                first_name = player_info["first_name"]
                last_name = player_info["last_name"]
                # Use the player's birthday to check if I found the right player page...
                birthday = player_info["birth_date"]
                pfr_player_id_chars = last_name[:4] + first_name[:2]
                pfr_player_id_char_list = [pfr_player_id_chars + str(i).zfill(2) for i in range(10)]
                logging.info(f"{pfr_player_id_char_list=}")
                valid_url_found = False  # flag to stop checking once a valid URL is found
                for id_no in pfr_player_id_char_list:
                    if valid_url_found:
                        break
                    try:
                        # This query is needed to see if this is the right player page.
                        check_bday = Stats(pfr_player_id=id_no).check_players_birthday()
                        if check_bday == birthday:
                            valid_url_found = True
                        else:
                            raise ValueError(f"{player_id} {birthday=} {id_no} {check_bday} Birthday doesn't match.")
                        fetch_and_process_game_logs(id_no, update_years, owner_data, player_name)
                    except Exception as e:
                        logging.error(f"The URL for {id_no} is not valid. {e=}")
                        print(f'URL for {id_no} is not valid, trying next...')
                        time.sleep(1)
            # The player's sleeper ID is in the player_id_table, use it to get the player's gamelogs pages.
            else:
                fetch_and_process_game_logs(pfr_player_id, update_years, owner_data, player_name)

            # Replace stale Sleeper details w/ updated data
            for p in owner_data["players_data"]:
                for p_n, d in p.items():
                    try:
                        if d[0]['player_id'] == player_id:
                            d.pop(0)
                            d.insert(0, player_info)
                    except KeyError:
                        # This is a fresh database w/o details for each player
                        d.insert(0, player_info)

            for player in owner_data["players_data"]:
                for player_name, data in player.items():
                    if data[0]['player_id'] == player_id:
                        sort_players_data(data)

            return owner_data


class NFLStatsDatabase:
    """
    Instantiate with a json database file and a league object, use methods to maniuplate database after stats files are created
    """

    def __init__(self, database_file, league: League):
        self.database_file = database_file
        self.League = league
        # TODO: To make this scalable, I'll need to get EVERY possible Sleeper scoring stat from API. I only account for TLOOJ atm.
        self.stat_weight = {
            'Passing_Yds': league.scoring_settings.pass_yd,  # Passing_Yds.1 is due to yards lost due to sacks. We don't care about that.
            'Passing_TD': league.scoring_settings.pass_td,
            'Receiving_TD': league.scoring_settings.rec_td,
            'Rushing_TD': league.scoring_settings.rush_td,
            'Kick Returns_TD': league.scoring_settings.st_td,  # Might need to check this, kr_td is a different stat I think for D/ST?
            'Punt Returns_TD': league.scoring_settings.st_td,
            'Fumbles_TD': league.scoring_settings.idp_def_td,
            'Def Interceptions_TD': league.scoring_settings.idp_def_td,
            'Scoring_Sfty': league.scoring_settings.idp_safe,
            'Receiving_Rec': league.scoring_settings.rec,
            'Rushing_Yds': league.scoring_settings.rush_yd,
            'Receiving_Yds': league.scoring_settings.rec_yd,
            'Kick Returns_Yds': league.scoring_settings.kr_yd,
            'Punt Returns_Yds': league.scoring_settings.pr_yd,
            'Passing_Int': league.scoring_settings.pass_int,
            'Sk': league.scoring_settings.idp_sack,
            'Def Interceptions_Int': league.scoring_settings.idp_int,
            'Def Interceptions_PD': league.scoring_settings.idp_pass_def,
            'Tackles_QBHits': league.scoring_settings.idp_qb_hit,
            'Tackles_TFL': league.scoring_settings.idp_tkl_loss,
            'Tackles_Solo': league.scoring_settings.idp_tkl_solo,
            'Tackles_Ast': league.scoring_settings.idp_tkl_ast,
            'Fumbles_Fmb': league.scoring_settings.fum,
            'Fumbles_FL': league.scoring_settings.fum_lost,
            'Fumbles_Yds': league.scoring_settings.fum_ret_yd,
            'Def Interceptions_Yds': league.scoring_settings.int_ret_yd,
            "blocked_kick": league.scoring_settings.idp_blk_kick,  # PFR doesn't include this information. Maybe someday.
            'Fumbles_FF': league.scoring_settings.idp_ff,
            'Fumbles_FR': league.scoring_settings.idp_fum_rec,
            'Scoring_2PM': league.scoring_settings.pass_2pt  # PFR doesn't specify if a 2 pt conversion was a pass or rush, but sleeper scores for it. Assume pass.
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
                        #TODO: This is where the logic needs to be different to handle multiple years of stats
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
                        except (ValueError, TypeError):
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


if __name__ == '__main__':
    logging_steup()
    with open('../data/test.json', 'r') as file:
        database = json.load(file)
    with open('../json/player_data.json', 'r') as file:
        sleeper_player_data = json.load(file)
    with open('../json/player_id_table.csv', 'r') as file:
        player_id_table = pd.read_csv(file)
    for roster in database:
        for player in roster['players_data']:
            for player_name, player_data in player.items():
                player_id = player_data[0]['player_id']
                Stats.fetch_game_log_data(owner_data=roster, player_data=sleeper_player_data, player_id=player_id, player_id_table=player_id_table, update=True)

    with open('../data/test2.json', "w") as file:
        json.dump(database, file, indent=4)

    # clean up "Unnamed" columns the json file which comes from PFR
    utils.rename_keys_in_json('../data/test2.json')
    # test = Stats(pfr_player_id="WardCh00")
    # print(Stats.check_players_birthday(test))