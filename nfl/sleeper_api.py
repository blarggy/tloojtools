import logging
import time

from sleeper.api import LeagueAPIClient
from sleeper.api import PlayerAPIClient
from sleeper.enum import Sport
from sleeper.model import (
    League,
    Roster,
    Player,
    User,
    ScoringSettings,
)
import json
import os

from nfl.utils import logging_steup, is_file_older_than_one_week, create_backup
from nfl.json_handler import CustomJSONEncoder
from nfl.constants import LEAGUE_ID, GLOBAL_NFL_PLAYER_ID_FILE, TRANSACTIONS_DIRECTORY
from nfl.constants import DATABASE_DIRECTORY
from nfl.constants import GLOBAL_SLEEPER_PLAYER_DATA_FILE
from nfl.utils import rename_keys_in_json
import nfl.nfl_api as nfl_api
import nfl.nfl_stats as nfl_stats
import pandas as pd

#TODO: create update_league_database() to check for new players and update the database


class FantasyLeagueDatabase:
    """
    Fantasy League Database object
    """
    def __init__(self, league_id):
        self.league_id = league_id
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
    def process_roster(roster, users, player_data, player_id_table, get_logs=False):
        """
        Processes the roster data and returns a dictionary with the owner's display name, team name, and players data.
        :param roster: from league object
        :param users: from league object
        :param player_data: All NFL player data from sleeper's api as json object
        :param player_id_table: from nfl api for mapping IDs to names
        :param get_logs: Bool, set True to Query PFR's site to get gamelogs data. For false just return list of Sleeper player IDs
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
                    for player_id in roster.players:
                        nfl_stats.Stats.fetch_game_log_data(owner_data, player_data, player_id, player_id_table)
                    return owner_data
                else:
                    for player_id in roster.players:
                        if player_id in player_data:
                            owner_data["players_data"].append(player_id)
                    return owner_data
        return None

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

        if not os.path.exists(f"{GLOBAL_NFL_PLAYER_ID_FILE}"):
            logging.info(f"Player ID table not found, generating the database. {GLOBAL_NFL_PLAYER_ID_FILE}")
            player_id_table = nfl_api.create_player_id_table()
        elif is_file_older_than_one_week(GLOBAL_NFL_PLAYER_ID_FILE):
            logging.info(f"Player ID table is older than a week, updating the database. {GLOBAL_NFL_PLAYER_ID_FILE}")
            player_id_table = nfl_api.create_player_id_table()
        else:
            player_id_table = pd.read_csv(GLOBAL_NFL_PLAYER_ID_FILE)

        return rosters, users, player_data, player_id_table

    def diff_rostered_players(self, old_database):
        """
        Pass in the path to an existing database file, returns a dictionary of players that have been added or dropped from a roster since the database was generated
        :return: dict, change_owner_data
        """
        rosters, users, player_data, player_id_table = FantasyLeagueDatabase.initialize_league_data(self.league)
        new_owner_data = []
        for roster in rosters:
            _new_owner_data = FantasyLeagueDatabase.process_roster(roster, users, player_data, player_id_table)
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

        return change_owner_data

    def save_transactions_to_file(self, old_database):
        """
        Saves the transactions data to a file in the 'transactions' directory.
        :param old_database: path to old database file
        :return:
        """
        player_data = FantasyLeagueDatabase.initialize_league_data(self.league)[2]
        change_owner_data = self.diff_rostered_players(old_database)
        roster_changes = []
        for roster in change_owner_data:
            for player_id in roster['players']:
                owner_id = roster['owner_id']
                display_name = roster['display_name']
                player_name = f"{player_data[player_id]['first_name']} {player_data[player_id]['last_name']}"
                player_position = f"{player_data[player_id]['fantasy_positions']}"
                roster_changes.append({
                    "owner_id": owner_id,
                    "display_name": display_name,
                    "player_id": player_id,
                    "player_name": player_name,
                    "player_position": player_position,
                    "transaction": "add"
                })
            for player in roster['players_delete']:
                owner_id = roster['owner_id']
                display_name = roster['display_name']
                player_name = f"{player_data[player]['first_name']} {player_data[player]['last_name']}"
                player_position = f"{player_data[player]['fantasy_positions']}"
                roster_changes.append({
                    "owner_id": owner_id,
                    "display_name": display_name,
                    "player_id": player,
                    "player_name": player_name,
                    "player_position": player_position,
                    "transaction": "remove"
                })

        file_path = f"{TRANSACTIONS_DIRECTORY}/{self.league_id}"

        if not os.path.exists(file_path):
            os.makedirs(file_path)

        roster_changes = json.dumps(roster_changes, indent=4)
        transactions_file = os.path.join(file_path, f"{time.strftime('%Y%m%d')}_{self.league_id}_transactions.json")
        with open(transactions_file, 'w') as file:
            file.write(roster_changes)

        return change_owner_data

    def generate_league_database(self):
        """
        Generates a .json file containing relevant roster information for your league. Make sure there's a player database file to read from, run generate_player_database() first.
        """
        rosters, users, player_data, player_id_table = FantasyLeagueDatabase.initialize_league_data(self.league)

        final_data = []
        logging.info(f'Generating league database file for {self.league_id=}')

        for roster in rosters:
            owner_data = FantasyLeagueDatabase.process_roster(roster, users, player_data, player_id_table, get_logs=True)
            if owner_data:
                final_data.append(owner_data)

        league_database_file = os.path.join(DATABASE_DIRECTORY, f"leagueid_{LEAGUE_ID}.json")
        with open(league_database_file, "w") as file:
            json.dump(final_data, file, indent=4)

        # clean up "Unnamed" columns the json file which comes from PFR
        rename_keys_in_json(league_database_file)

    def update_league_database(self, database_file):
        """
        Updates the league database file for the given year. Make sure there's a player database file to read from, run generate_player_database() first.
        """
        create_backup(database_file)
        rosters, users, player_data, player_id_table = FantasyLeagueDatabase.initialize_league_data(self.league)
        with open(database_file, "r") as file:
            league_data = json.load(file)
        change_owner_data = self.save_transactions_to_file(database_file)

        for change in change_owner_data:
            owner_id = change['owner_id']

            # Find the corresponding owner in league_data
            for owner in league_data:
                if owner['owner_id'] == owner_id:
                    # Handle players to add
                    for player_id in change['players']:
                        if player_id in player_data:
                            player_info = player_data[player_id]
                            player_name = f"{player_info['first_name']} {player_info['last_name']}"
                            logging.info(f"Adding {player_name} to {owner['display_name']}'s roster.")
                            owner['players_data'].append({player_name: [player_info]})

                    # Handle players to delete
                    for player_id in change['players_delete']:
                        for player in owner['players_data']:
                            for player_name, details in player.items():
                                if details[0]['player_id'] == player_id:
                                    logging.info(f"Removing {player_name} from {owner['display_name']}'s roster.")
                                    owner['players_data'].remove(player)
                                    break

        with open(database_file, "w") as file:
            json.dump(league_data, file, indent=4)

    def update_player_stats_in_database(self, database_file, years=None):
        """
        Run update_league_database() first, then this
        Updates the player stats in the league database file for the given year. Make sure there's a player database file to read from, run generate_player_database() first.
        """
        sleeper_player_data, player_id_table = FantasyLeagueDatabase.initialize_league_data(self.league)[2:4]
        with open(database_file, "r") as file:
            league_data = json.load(file)

        for roster in league_data:
            for player in roster['players_data']:
                for player_name, player_data in player.items():
                    player_id = player_data[0]['player_id']
                    nfl_stats.Stats.fetch_game_log_data(owner_data=roster, player_data=sleeper_player_data, player_id=player_id, player_id_table=player_id_table, update=True, update_years=years)

        with open(database_file, "w") as file:
            json.dump(league_data, file, indent=4)

        # clean up "Unnamed" columns the json file which comes from PFR
        rename_keys_in_json(database_file)


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
    # FantasyLeagueDatabase(LEAGUE_ID).save_transactions_to_file('../json/leagueid_1075600889420845056.json')
    FantasyLeagueDatabase(LEAGUE_ID).update_player_stats_in_database('../json/leagueid_1075600889420845056.json')
