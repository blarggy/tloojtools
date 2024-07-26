import json
import logging

from sleeper.enum.nfl.NFLPlayerStatus import NFLPlayerStatus
from sleeper.enum.Sport import Sport
from sleeper.enum.SportTeam import SportTeam
from sleeper.enum.PlayerPosition import PlayerPosition
from sleeper.enum.PlayerStatus import PlayerStatus
from sleeper.enum.InjuryStatus import InjuryStatus
from sleeper.enum.PracticeParticipation import PracticeParticipation
from datetime import date, datetime
import pandas as pd


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, NFLPlayerStatus):
            return obj.name
        if isinstance(obj, Sport):
            return obj.name
        if isinstance(obj, SportTeam):
            return obj.name
        if isinstance(obj, PlayerPosition):
            return obj.name
        if isinstance(obj, PlayerStatus):
            return obj.name
        if isinstance(obj, InjuryStatus):
            return obj.name
        if isinstance(obj, PracticeParticipation):
            return obj.name
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        # Add other custom conversions as needed
        return super().default(obj)

    @staticmethod
    def normalize_seasonal_json_database_to_excel_format(json_file):
        # Load the JSON data
        with open(json_file) as f:
            data = json.load(f)

        # Initialize lists to hold the normalized data
        players_data = []
        scrimmage_stats_data = []
        defense_stats_data = []
        passing_stats_data = []

        # Flatten the JSON structure
        for entry in data:
            owner_id = entry['owner_id']
            display_name = entry['display_name']
            team_name = entry['team_name']
            for player in entry['players_data']:
                for player_name, player_details in player.items():
                    player_info = player_details[0]
                    player_info.update({
                        'owner_id': owner_id,
                        'display_name': display_name,
                        'team_name': team_name,
                        'player_name': player_name
                    })
                    players_data.append(player_info)

                    # Extract and flatten scrimmage_stats
                    for scrimmage_stat in player_details[1].get('scrimmage_stats', []):
                        scrimmage_stat.update({
                            'owner_id': owner_id,
                            'display_name': display_name,
                            'team_name': team_name,
                            'player_name': player_name
                        })
                        scrimmage_stats_data.append(scrimmage_stat)

                    # Extract and flatten defense_stats
                    for defense_stat in player_details[1].get('defense_stats', []):
                        defense_stat.update({
                            'owner_id': owner_id,
                            'display_name': display_name,
                            'team_name': team_name,
                            'player_name': player_name
                        })
                        defense_stats_data.append(defense_stat)

                    # Extract and flatten passing_stats
                    for passing_stat in player_details[1].get('passing_stats', []):
                        passing_stat.update({
                            'owner_id': owner_id,
                            'display_name': display_name,
                            'team_name': team_name,
                            'player_name': player_name
                        })
                        passing_stats_data.append(passing_stat)

        # Create DataFrames for each part
        players_df = pd.DataFrame(players_data)
        scrimmage_stats_df = pd.DataFrame(scrimmage_stats_data)
        defense_stats_df = pd.DataFrame(defense_stats_data)
        passing_stats_df = pd.DataFrame(passing_stats_data)

        # Merge the DataFrames back on common keys
        final_df = players_df

        if not scrimmage_stats_df.empty:
            final_df = final_df.merge(scrimmage_stats_df, on=['owner_id', 'display_name', 'team_name', 'player_name'],
                                      how='left', suffixes=('', '_scrimmage'))

        if not defense_stats_df.empty:
            final_df = final_df.merge(defense_stats_df, on=['owner_id', 'display_name', 'team_name', 'player_name'],
                                      how='left', suffixes=('', '_defense'))

        if not passing_stats_df.empty:
            final_df = final_df.merge(passing_stats_df, on=['owner_id', 'display_name', 'team_name', 'player_name'],
                                      how='left', suffixes=('', '_passing'))

        final_df.to_excel(f'../data/{json_file}_as_excel.xlsx', index=False)

    @staticmethod
    def normalize_gamelog_json_database_to_csv_format(json_file):
        with open(json_file) as f:
            database = json.load(f)

        all_data = []

        for entry in database:
            # owner_id = entry['owner_id']
            display_name = entry['display_name']
            team_name = entry['team_name']
            for player in entry['players_data']:
                for player_name, player_details in player.items():
                    data = {'player_name': player_name,
                            'display_name': display_name,
                            'team_name': team_name,
                            'position': ' '.join(player_details[0]['fantasy_positions']),
                            'sleeper_player_id': player_details[0]['player_id'],
                            'height': player_details[0]['height'],
                            'weight': player_details[0]['weight']}
                    player_stats = player_details[1]
                    for category, stats in player_stats.items():
                        for stat_name, values in stats.items():
                            for idx, value in values.items():
                                col_name = stat_name
                                if col_name not in data:
                                    data[col_name] = []
                                data[col_name].append(value)
                    player_df = pd.DataFrame(data)
                    all_data.append(player_df)
                    logging.debug(f"{player_df=}")

        combined_df = pd.concat(all_data, ignore_index=True)
        columns = ['player_name', 'display_name', 'team_name', 'position', 'sleeper_player_id', 'height', 'weight'] + \
                  [col for col in combined_df.columns
                   if col not in [
                       'player_name',
                       'display_name',
                       'team_name',
                       'position',
                       'sleeper_player_id',
                       'height',
                       'weight']]
        combined_df = combined_df[columns]
        combined_df.to_csv(f'../data/{json_file}_as_csv.csv', index=False)


if __name__ == '__main__':
    CustomJSONEncoder.normalize_gamelog_json_database_to_csv_format('../data/test_new_scoring.json')
    # CustomJSONEncoder.normalize_gamelog_json_database_to_excel_format('data/test.json')
