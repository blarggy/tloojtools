import json

from flask import render_template

from app import app

@app.route('/')
@app.route('/index')
def index():
    # load in json/2023_gamelogs_leagueid_1075600889420845056.json and extract display_name and team_name
    # extract player_name
    # for each player_name, display_name, team_name, create a dictionary and append to a list
    # pass the list to the html
    league = []
    with open('data/2023_gamelogs_leagueid_1075600889420845056.json') as file:
        database_data = json.load(file)
        for roster in database_data:
            display_name = roster['display_name']
            team_name = roster['team_name']
            team = {'username': display_name, 'team_name': team_name, 'players': []}
            for player_data in roster['players_data']:
                for player_name, player_details in player_data.items():
                    team['players'].append({
                        'player_name': player_name,
                        'position': player_details[0]['position'],
                        'sleeper_player_id': player_details[0]['player_id'],
                        'height': player_details[0]['height'],
                        'weight': player_details[0]['weight'],
                        'stats': player_details[1]
                    })
            league.append(team)
    return render_template('index.html', title='Home', league_info=league)