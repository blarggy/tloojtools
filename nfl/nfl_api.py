import json

import nfl_data_py as nfl
import pandas as pd
from nfl.constants import GLOBAL_NFL_PLAYER_ID_FILE


def create_player_id_table():
    ids = nfl.import_ids()
    file_name = GLOBAL_NFL_PLAYER_ID_FILE
    ids.to_csv(file_name, index=False)
    return ids

class NFLData:
    pass


# nfl_data = nfl.import_seasonal_data(years=[2023], s_type='REG')
# df = pd.DataFrame(nfl_data)
# df.to_json('json/nfl_data.json', orient='records', indent=4)

# with open('json/nfl_data.json', 'r') as file:
#     nfl_data = json.load(file)
#
#
# player_ids = []
# for player in nfl_data:
#     player_ids.append(player['player_id'])

# player_names = nfl.import_ids()
# player_names.to_csv('test.csv', index=False)
# sleeper_id_to_find = 10216
# gsis_id_to_find = '00-0023459'
# info = player_names.loc[player_names['sleeper_id'] == sleeper_id_to_find, 'name'].values[0]
# print(info)

# name = player_names.loc[player_names['sleeper_id'] == sleeper_id_to_find, 'name'].values[0]
# id = player_names.loc[player_names['sleeper_id'] == sleeper_id_to_find, 'gsis_id'].values[0]

# print(name, id)


# nfl_weekly_data = nfl.import_weekly_data(years=[2023])
# df = pd.DataFrame(nfl_weekly_data)
# df.to_json('json/nfl_weekly_data.json', orient='records', indent=4)