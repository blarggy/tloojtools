import logging
import time

from sleeper.api import LeagueAPIClient
from sleeper.api import PlayerAPIClient
from sleeper.enum import Sport
from sleeper.model import (
    League,
    Roster,
    Player,
    User, ScoringSettings,
)
import json
import os

from nfl.utils import logging_steup, is_file_older_than_one_week
from nfl.json_handler import CustomJSONEncoder
from nfl.constants import LEAGUE_ID, GLOBAL_NFL_PLAYER_ID_FILE
from nfl.constants import DATABASE_DIRECTORY
from nfl.constants import GLOBAL_SLEEPER_PLAYER_DATA_FILE
from nfl.utils import rename_keys_in_json
import nfl.nfl_api as nfl_api
import nfl.nfl_stats as nfl_stats
from nfl.nfl_stats import NFLStatsDatabase

#TODO: create update_league_database() to check for new players and update the database


class FantasyLeagueDatabase:
    """
    Fantasy League Database object
    """
    def __init__(self, league_id):
        self.league = SleeperLeague(league_id)

    @staticmethod
    def generate_player_database():
        """
        Generates a copy of the Sleeper player database and saves it as a .json file. They ask not to run this method more than once a day.
        """
        logging.info(f"Generating player database from sleeper")
        player_data = PlayerAPIClient.get_all_players(sport=Sport.NFL)
        player_data_dict = {player_id: Player.to_dict(player) for player_id, player in player_data.items()}
        os.makedirs(DATABASE_DIRECTORY, exist_ok=True)
        player_data_file = os.path.join(DATABASE_DIRECTORY, "player_data.json")

        with open(player_data_file, 'w') as json_file:
            json.dump(player_data_dict, json_file, indent=4, cls=CustomJSONEncoder)
        logging.info(f"{player_data_file=} generated")

    @staticmethod
    def process_roster(roster, users, player_data, year, player_id_table, get_logs=False):
        """
        Processes the roster data and returns a dictionary with the owner's display name, team name, and players data.
        :param roster: from league object
        :param users: from league object
        :param player_data: json file with player data
        :param year: list of years to collect data for
        :param player_id_table: from nfl api for mapping IDs to names
        :param get_logs: Bool, set True to Query PFR's site to get gamelogs data.
        :return: dict, owner_data
        """
        for user in users:
            if roster.owner_id == user.user_id:
                owner_data = {
                    "owner_id": roster.owner_id,
                    "display_name": user.display_name,
                    "team_name": user.metadata['team_name'],
                    "players_data": []
                }
                if get_logs:
                    FantasyLeagueDatabase.fetch_game_log_data(owner_data, player_data, roster, year, player_id_table)
                    return owner_data
                else:
                    for player_id in roster.players:
                        if player_id in player_data:
                            owner_data["players_data"].append(player_id)
                    return owner_data
        return None

    @staticmethod
    def fetch_game_log_data(owner_data, player_data, roster, year, player_id_table):
        """
        Helper function for process_roster()
        Gets the gamelogs data for each player from PFR on the roster and adds it to the owner_data dictionary.
        """
        for player_id in roster.players:
            if player_id in player_data:
                player_name = player_id_table.loc[player_id_table['sleeper_id'] == int(player_id), 'name'].values[0]
                pfr_player_id = player_id_table.loc[player_id_table['sleeper_id'] == int(player_id), 'pfr_id'].values[0]
                player_info = player_data[player_id]
                if type(pfr_player_id) is float:
                    logging.error(f"{pfr_player_id=} is not in the {GLOBAL_NFL_PLAYER_ID_FILE} file. Trying to find the gamelogs page by hand...")
                    first_name = player_info["first_name"]
                    last_name = player_info["last_name"]
                    pfr_player_id_chars = last_name[:4] + first_name[:2]
                    pfr_player_id_char_list = [pfr_player_id_chars + str(i).zfill(2) for i in range(10)]
                    logging.info(f"{pfr_player_id_char_list=}")
                    for id_no in pfr_player_id_char_list:
                        try:
                            game_log_data = nfl_stats.Stats(year=year, pfr_player_id=id_no).gamelogs_data()
                            time.sleep(5)  # respectfully wait
                            break
                        except Exception as e:
                            logging.error(f"The URL for {id_no} is not valid. {e=}")
                            print(f'URL for {id_no} is not valid, trying next...')
                            time.sleep(1)
                else:
                    game_log_data = nfl_stats.Stats(year=year, pfr_player_id=pfr_player_id).gamelogs_data()
                    time.sleep(5)  # respectfully wait
                # some of the columns are tuples, convert them to lists for json serialization
                game_log_data = game_log_data.apply(lambda col: col.map(lambda x: list(x) if isinstance(x, tuple) else x))
                game_log_data.columns = ['_'.join(map(str, col)).strip() for col in game_log_data.columns.values]
                stats = {f"{year}_stats": game_log_data.to_dict()}
                owner_data["players_data"].append({player_name: [player_info, stats]})
                return owner_data

    @staticmethod
    def parse_players():
        pass

    @staticmethod
    def initialize_league_data(league_id):
        rosters = league_id.get_league_rosters_by_id()
        users = league_id.get_users_in_league_by_id()

        if not os.path.exists(f"{GLOBAL_SLEEPER_PLAYER_DATA_FILE}"):
            logging.info(f"Player database file not found, generating the database.")
            FantasyLeagueDatabase.generate_player_database()
        elif is_file_older_than_one_week(GLOBAL_SLEEPER_PLAYER_DATA_FILE):
            logging.info(f"Player database is older than a week, updating the database.")
            FantasyLeagueDatabase.generate_player_database()

        with open(GLOBAL_SLEEPER_PLAYER_DATA_FILE, "r") as file:
            player_data = json.load(file)

        player_id_table = nfl_api.create_player_id_table()

        return rosters, users, player_data, player_id_table

    def diff_rostered_players(self, old_database, years):
        """
        Returns data about players that have been transacted on or off a roster
        :return:
        """
        rosters, users, player_data, player_id_table = FantasyLeagueDatabase.initialize_league_data(self.league)
        new_owner_data = []
        for roster in rosters:
            _new_owner_data = FantasyLeagueDatabase.process_roster(roster, users, player_data, years, player_id_table)
            if _new_owner_data:
                new_owner_data.append(_new_owner_data)
        with open(old_database, "r") as file:
            old_owner_json = json.load(file)
        change_owner_data = []
        for old_roster in old_owner_json:
            _change_owner_data = {
                "owner_id": old_roster['owner_id'],
                "display_name": old_roster['display_name'],
                "team_name": old_roster['team_name'],
                "players": [],
                "players_delete": []
            }
            old_player_list = {}
            # Find which players were dropped from a team's roster since the last update.
            for old_player in old_roster['players_data']:
                for player_name, details in old_player.items():
                    old_player_list.update({details[0]['player_id']: player_name})
                    for new_owner in new_owner_data:
                        if old_roster['owner_id'] == new_owner['owner_id']:
                            if details[0]['player_id'] not in new_owner['players_data']:
                                logging.info(f"{player_name=} id: {details[0]['player_id']} has been dropped from id: {old_roster['owner_id']} {old_roster['display_name']}'s roster.")
                                _change_owner_data["players_delete"].append(details[0]['player_id'])
            # Find which players were added to a team's roster since the last update.
            for new_owner in new_owner_data:
                if old_roster['owner_id'] == new_owner['owner_id']:
                    for new_player_id in new_owner['players_data']:
                        if new_player_id not in old_player_list.keys():
                                player_name = f"{player_data[new_player_id]['first_name']} {player_data[new_player_id]['last_name']}"
                                logging.info(f"{player_name=} id: {new_player_id} has been added to id: {new_owner['owner_id']} {new_owner['display_name']}'s roster.")
                                _change_owner_data["players"].append(new_player_id)
            change_owner_data.append(_change_owner_data)
        print(f"{new_owner_data=}")
        print(f"{change_owner_data=}")

    def generate_league_database(self, years):
        """
        Generates a .json file containing relevant roster information for your league. Make sure there's a player database file to read from, run generate_player_database() first.
        :param years: list, select a year to gather data from (or just one year). Each year generates a separate database.
        """
        rosters, users, player_data, player_id_table = FantasyLeagueDatabase.initialize_league_data(self.league)

        for year in years:
            logging.info(f'Generating league database file for {year=}')

            final_data = []
            for roster in rosters:
                owner_data = FantasyLeagueDatabase.process_roster(roster, users, player_data, year, player_id_table, get_logs=True)
                if owner_data:
                    final_data.append(owner_data)

            league_database_file = os.path.join(DATABASE_DIRECTORY, f"{year}_leagueid_{LEAGUE_ID}.json")
            with open(league_database_file, "w") as file:
                json.dump(final_data, file, indent=4)

            # clean up "Unnamed" columns the json file which comes from PFR
            rename_keys_in_json(league_database_file)


class SleeperLeague:
    def __init__(self, league_id):
        self.league_id = league_id

    def get_league_by_id(self) -> League:
        """
        Returns league specific settings
        """
        league: League = LeagueAPIClient.get_league(league_id=self.league_id)
        return league

    def get_league_rosters_by_id(self) -> list[Roster]:
        """
        Provided league ID, returns all the roster data for every team in the league
        """
        league_rosters: list[Roster] = LeagueAPIClient.get_rosters(league_id=self.league_id)
        return league_rosters

    def get_users_in_league_by_id(self) -> list[User]:
        """
        Provided league ID, returns all users associated with league
        """
        league_users = LeagueAPIClient.get_users_in_league(league_id=self.league_id)
        return league_users

    def get_league_scoring_settings(self) -> ScoringSettings:
        league = self.get_league_by_id()
        return league.scoring_settings

    @staticmethod
    def convert_owner_id_into_username(owner_id):
        pass


if __name__ == '__main__':
    """
    Until this gets built out, this is a good starting point to use this tool.
    1. Generate the Fantasy League database
        FantasyLeagueDatabase.generate_league_database(["2023"], method="gamelogs")
    2. Pass the result database .json object to NFLStatsDatabase to calculate fantasy points
        NFLStatsDatabase('../json/database_filename.json', league).calculate_fantasy_points()
    3. Convert the database object to .csv object
        CustomJSONEncoder.normalize_gamelog_json_database_to_csv_format('../json/database_filename.json')
    4. Pass the .csv to R script to generate cluster svgs
    """
    logging_steup()
    FantasyLeagueDatabase(LEAGUE_ID).diff_rostered_players('../json/2023_gamelogs_leagueid_1075600889420845056.json',["2023"])
