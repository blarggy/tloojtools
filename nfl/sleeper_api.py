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
)
import json
import os

import utils
from json_handler import CustomJSONEncoder
from constants import LEAGUE_ID, GLOBAL_NFL_PLAYER_ID_FILE
from constants import DATABASE_DIRECTORY
from constants import GLOBAL_SLEEPER_PLAYER_DATA_FILE
from utils import rename_keys_in_json
import nfl_api
import nfl_stats


class LeagueDatabase:
    """
    League Database object
    """
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
    def generate_league_database(years, method):
        """
        Generates a .json file containing relevant roster information for your league. Make sure there's a player database file to read from, run generate_player_database() first.
        :param years: list, select a year to gather data from (or just one year). Each year generates a separate database.
        :param method: str, specifies data collection method. can be either "seasonal" or "gamelogs". Seasonal data is gathered from PFR's overview page, game log data will scrape each individual player's gamelogs page.
        """

        league = SleeperLeague(LEAGUE_ID)
        rosters = league.get_league_rosters_by_id()
        users = league.get_users_in_league_by_id()

        if not os.path.exists(f"{GLOBAL_SLEEPER_PLAYER_DATA_FILE}"):
            LeagueDatabase.generate_player_database()

        with open(GLOBAL_SLEEPER_PLAYER_DATA_FILE, "r") as file:
            player_data = json.load(file)

        player_id_table = nfl_api.create_player_id_table()

        for year in years:
            logging.info(f'Generating {method=} league database file for {year=}')
            if method == "seasonal":
                passing_stats = nfl_stats.Stats(year=year, position="passing").create_stats()
                scrimmage_stats = nfl_stats.Stats(year=year, position="scrimmage").create_stats()
                defense_stats = nfl_stats.Stats(year=year, position="defense").create_stats()

                final_data = []
                for roster in rosters:
                    for user in users:
                        if roster.owner_id == user.user_id:
                            owner_data = {
                                "owner_id": roster.owner_id,
                                "display_name": user.display_name,
                                "team_name": user.metadata['team_name'],
                                "players_data": []
                            }
                            for player_id in roster.players:
                                if player_id in player_data:
                                    player_name = \
                                        player_id_table.loc[
                                            player_id_table['sleeper_id'] == int(player_id), 'name'].values[0]
                                    player_pfr_id = \
                                        player_id_table.loc[
                                            player_id_table['sleeper_id'] == int(player_id), 'pfr_id'].values[0]
                                    player_info = player_data[player_id]
                                    # Combine stats from PFR into database
                                    player_passing_stats = passing_stats.loc[
                                        passing_stats['Player-additional'].str.contains(str(player_pfr_id))].to_dict(
                                        orient='records')
                                    player_scrimmage_stats = scrimmage_stats.loc[
                                        scrimmage_stats['(\'-additional\', \'-9999\')'].str.contains(
                                            str(player_pfr_id))].to_dict(orient='records')
                                    player_defense_stats = defense_stats.loc[
                                        defense_stats['(\'-additional\', \'-9999\')'].str.contains(
                                            str(player_pfr_id))].to_dict(
                                        orient='records')
                                    stats = {"passing_stats": player_passing_stats,
                                             "scrimmage_stats": player_scrimmage_stats,
                                             "defense_stats": player_defense_stats}
                                    owner_data["players_data"].append({player_name: [player_info, stats]})
                            final_data.append(owner_data)

                league_database_file = os.path.join(DATABASE_DIRECTORY, f"{year}_{method}_leagueid_{LEAGUE_ID}.json")
                with open(league_database_file, "w") as file:
                    json.dump(final_data, file, indent=4)

            elif method == "gamelogs":
                final_data = []
                for roster in rosters:
                    for user in users:
                        if roster.owner_id == user.user_id:
                            owner_data = {
                                "owner_id": roster.owner_id,
                                "display_name": user.display_name,
                                "team_name": user.metadata['team_name'],
                                "players_data": []
                            }
                            for player_id in roster.players:
                                if player_id in player_data:
                                    player_name = \
                                        player_id_table.loc[
                                            player_id_table['sleeper_id'] == int(player_id), 'name'].values[0]
                                    pfr_player_id = \
                                        player_id_table.loc[
                                            player_id_table['sleeper_id'] == int(player_id), 'pfr_id'].values[0]
                                    player_info = player_data[player_id]
                                    if type(pfr_player_id) is float:
                                        logging.error(
                                            f"{pfr_player_id=} is not in the {GLOBAL_NFL_PLAYER_ID_FILE} file. Trying to find the gamelogs page by hand...")
                                        first_name = player_info["first_name"]
                                        last_name = player_info["last_name"]
                                        pfr_player_id_chars = last_name[:4] + first_name[:2]
                                        pfr_player_id_char_list = [pfr_player_id_chars + str(i).zfill(2) for i in
                                                                   range(10)]
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
                                    game_log_data.columns = ['_'.join(map(str, col)).strip() for col in
                                                             game_log_data.columns.values]
                                    stats = {f"{year} stats": game_log_data.to_dict()}
                                    owner_data["players_data"].append({player_name: [player_info, stats]})
                                    # break  # delete later, for debugging only (reduces the search to 1 player per team instead of all :)
                            final_data.append(owner_data)

            league_database_file = os.path.join(DATABASE_DIRECTORY, f"{year}_{method}_leagueid_{LEAGUE_ID}.json")
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

    @staticmethod
    def convert_owner_id_into_username(owner_id):
        pass


if __name__ == '__main__':
    utils.logging_steup()
    # LeagueDatabase.generate_league_database(["2023"], method="seasonal")
    # LeagueDatabase.generate_league_database(["2023"], method="gamelogs")
    print(SleeperLeague(LEAGUE_ID).get_league_by_id())

