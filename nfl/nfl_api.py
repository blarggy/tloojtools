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