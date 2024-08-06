import io
import os.path
from requests.exceptions import HTTPError
import requests
import json
import logging
import time
import pandas as pd
from sleeper.model import League

from nfl.utils import create_backup
from nfl.utils import logging_steup

#TODO: Handle multiple years worth of stats as separate files

class Stats:
    """
    Base class for NFL player stats.

    Attributes:
        year (int): The year for which stats are being fetched.
        pfr_player_id (str): The Pro-Football-Reference player ID.
        PFR_STATS_URL (str): The URL template for fetching player stats.
    """

    def __init__(self, year, pfr_player_id=None):
        """
        Initializes the Stats class with the given year and player ID.

        Args:
            year (int): The year for which stats are being fetched.
            pfr_player_id (str, optional): The Pro-Football-Reference player ID. Defaults to None.
        """
        self.year = year
        self.pfr_player_id = pfr_player_id
        self.PFR_STATS_URL = f"https://www.pro-football-reference.com/years/{self.year}/{self.position}.htm"

    def gamelogs_data(self):
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
