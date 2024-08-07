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

    #TODO: Update this to support multiple years worth of stats
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
