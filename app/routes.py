import json
import pandas as pd
from flask import render_template
from app import app


def load_database():
    with open('data/2023_gamelogs_leagueid_1075600889420845056.json') as file:
        database_data = json.load(file)
    return database_data


def get_player_info(player_id):
    database_data = load_database()
    player_query = {}
    player_tables = {}

    for roster in database_data:
        for player_data in roster['players_data']:
            for player_name, player_details in player_data.items():
                if player_details[0]['player_id'] == player_id:
                    player_query.update({'owner': roster['team_name']})
                    player_query.update({
                        'player_name': player_name,
                        'details': player_details[0],
                        'stats': player_details[1].keys()
                    })
                    player_stats = player_details[1]
                    for year, stats in player_stats.items():
                        player_df = pd.DataFrame(stats)
                        player_tables[year] = player_df.to_html(classes='table table-striped', index=True)
    return player_query, player_tables


@app.route('/')
@app.route('/index')
def index():
    # load in json/2023_gamelogs_leagueid_1075600889420845056.json and extract display_name and team_name
    # extract player_name
    # for each player_name, display_name, team_name, create a dictionary and append to a list
    # pass the list to the html

    database_data = load_database()
    league = []
    for roster in database_data:
        team_name = roster['team_name']
        owner_id = roster['owner_id']
        team = {'team_name': team_name, 'owner_id': owner_id}
        league.append(team)

    return render_template('index.html', title='Home', league_info=league)


@app.route('/team/<int:owner_id>')
def team_info(owner_id):
    owner_id = str(owner_id)
    database_data = load_database()
    selected_team = None
    roster = []
    for team in database_data:
        if team['owner_id'] == owner_id:
            selected_team = team
            roster.clear()
            for player_data in selected_team['players_data']:
                for player_name, player_details in player_data.items():
                    roster.append({
                        'player_name': player_name,
                        'position': player_details[0]['position'],
                        'player_id': player_details[0]['player_id']
                    })
    if selected_team:
        return render_template('team_info.html', team=selected_team, roster=roster)
    else:
        return "Team not found", 404


@app.route('/player/<int:player_id>')
def player_info(player_id):
    player_id = str(player_id)
    player_data, player_stat_tables = get_player_info(player_id)
    if player_data:
        print(f"Player data: {player_data}")
        print(f"Player stat table: {player_stat_tables}")
        return render_template('player_info.html', player=player_data, player_stat_tables=player_stat_tables)
    else:
        return "Player not found", 404
