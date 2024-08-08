import json
import pandas as pd
from flask import render_template
from app import app


def load_database():
    with open('json/leagueid_1075600889420845056.json') as file:
        database_data = json.load(file)
    return database_data


def reformat_player_data(player_dataframe):
    # handle whitespace
    player_dataframe = player_dataframe.fillna('')
    player_dataframe = player_dataframe.replace('null', '')

    # Cast some columns to appropriate types
    if 'G#' in player_dataframe.columns:
        player_dataframe['G#'] = player_dataframe['G#'].apply(lambda x: int(float(x)) if x != '' else x)
    if 'Week' in player_dataframe.columns:
        player_dataframe['Week'] = player_dataframe['Week'].apply(lambda x: int(float(x)) if x != '' else x)
    player_dataframe.columns = player_dataframe.columns.astype(str)

    # resolve column names
    player_dataframe.columns = player_dataframe.columns.str.replace('Rk', 'Index') \
        .str.replace('G#', 'Game') \
        .str.replace('Tm', 'Team') \
        .str.replace('1', '') \
        .str.replace('Opp', 'Opponent') \
        .str.replace('GS', 'Starter') \
        .str.replace('Off. Snaps_Num', '# Offensive Snaps') \
        .str.replace('Off. Snaps_Pct', '% Offensive Snaps') \
        .str.replace('Def. Snaps_Pct', '% Defensive Snaps') \
        .str.replace('Def. Snaps_Num', '# Defensive Snaps') \
        .str.replace('ST Snaps_Num', '# Special Teams Snaps') \
        .str.replace('ST Snaps_Pct', '% Special Teams Snaps') \
        .str.replace('Receiving_Tgt', 'Receiving Targets') \
        .str.replace('Receiving_Yds', 'Receiving Yards') \
        .str.replace('Receiving_Y/R', 'Receiving Yards/Reception') \
        .str.replace('Receiving_TD', 'Receiving TD') \
        .str.replace('Receiving_Ctch%', 'Receiving Catch %') \
        .str.replace('Receiving_Y/Tgt', 'Receiving Yards/Target') \
        .str.replace('Kick Returns_Rt', 'Kick Return Tries') \
        .str.replace('Kick Returns_Yds', 'Kick Return Yards') \
        .str.replace('Kick Returns_Y/R', 'Kick Return Yards/Return') \
        .str.replace('Kick Returns_TD', 'Kick Return TD') \
        .str.replace('Scoring_2PM', '2pt Conversion') \
        .str.replace('Scoring_TD', 'Scoring TD (any)') \
        .str.replace('Scoring_Pts', 'Points Scored') \
        .str.replace('Fumbles_Fmb', 'Fumbles') \
        .str.replace('Fumbles_FL', 'Fumbles Lost') \
        .str.replace('Fumbles_FF', 'Fumbles Forced') \
        .str.replace('Fumbles_FR', 'Fumbles Recovered') \
        .str.replace('Fumbles_Yds', 'Fumble Yards Returned') \
        .str.replace('Fumbles_TD', 'Fumble Return TD') \
        .str.replace('fantasy_points', 'Fantasy Points') \
        .str.replace('Sk', 'Sacks') \
        .str.replace('Tackles_Solo', 'Solo Tackles') \
        .str.replace('Tackles_Ast', 'Assisted Tackles') \
        .str.replace('Tackles_Comb', 'Combined Tackles') \
        .str.replace('Tackles_TFL', 'Tackles for Loss') \
        .str.replace('Tackles_QBHits', 'QB Hits') \
        .str.replace('Def Interceptions_Int', 'Def. Interceptions') \
        .str.replace('Def Interceptions_Yds', 'Def. Interception Yards') \
        .str.replace('Def Interceptions_TD', 'Def. Interception TD') \
        .str.replace('Def Interceptions_PD', 'Passes Defended') \
        .str.replace('Rushing_Att', 'Rush Attempts') \
        .str.replace('Rushing_Yds', 'Rush Yards') \
        .str.replace('Rushing_Y/A', 'Rush Yards/Attempt') \
        .str.replace('Rushing_TD', 'Rush TD') \
        .str.replace('Passing_Cmp', 'Pass Completions') \
        .str.replace('Passing_Att', 'Pass Attempts') \
        .str.replace('Passing_Cmp%', 'Pass Completion %') \
        .str.replace('Passing_Yds', 'Passing Yards') \
        .str.replace('Passing_TD', 'Passing TD') \
        .str.replace('Passing_Int', 'Passing INT') \
        .str.replace('Passing_Rate', 'Pass Rate') \
        .str.replace('Passing_Sk', 'Sacked') \
        .str.replace('Passing_Yds.1', 'Yards Lost to Sacks') \
        .str.replace('Passing_Y/A', 'Pass Yards/Attempt') \
        .str.replace('Passing_AY/A', 'Adjusted Pass Yards/Attempt*') \
        .str.replace('Punt Returns_Ret', 'Punt Return Tries') \
        .str.replace('Punt Returns_Yds', 'Punt Return Yards') \
        .str.replace('Punt Returns_Y/R', 'Punt Return Yards/Return') \
        .str.replace('Punt Returns_TD', 'Punt Return TD') \
        .str.replace('Scoring_Sfty', 'Safety')
    # Passing_AY/A = Pass yds + 20 * Passing TD - 45 * Interceptions / Passes Attempted
    # Remove the index column
    player_dataframe = player_dataframe.iloc[:, 1:]
    return player_dataframe


def get_player_info(player_id):
    database_data = load_database()
    player_query = {}
    player_tables = {}

    for roster in database_data:
        for player_data in roster['players_data']:
            for player_name, player_details in player_data.items():
                if player_details[0]['player_id'] == player_id:
                    player_query.update({'owner': roster['team_name']})
                    player_query.update({'owner_id': roster['owner_id']})
                    player_query.update({
                        'player_name': player_name,
                        'details': player_details[0],
                        'stats': [detail.keys() for detail in player_details[1:]]
                    })
                    for year, stats in player_details[1].items():
                        player_df = pd.DataFrame(stats)
                        player_df = reformat_player_data(player_df)
                        player_tables[year] = player_df.to_html(classes='table table-striped', index=False)
                    for detail in player_details[2:]:
                        for year, stats in detail.items():
                            player_df = pd.DataFrame(stats)
                            player_df = reformat_player_data(player_df)
                            player_tables[year] = player_df.to_html(classes='table table-striped', index=False)
    return player_query, player_tables


@app.route('/')
@app.route('/index')
def index():
    database_data = load_database()
    league = []
    for roster in database_data:
        team_name = roster['team_name']
        owner_id = roster['owner_id']
        team = {'team_name': team_name, 'owner_id': owner_id}
        league.append(team)

    return render_template('index.html', title='Home', league_info=league)


def generate_breadcrumbs(current_page, crumbs=None):
    breadcrumbs = [{'name': 'Home', 'url': '/index'}]
    if current_page == 'team':
        breadcrumbs.append({'name': crumbs['team_name'], 'url': f'/team/{crumbs["owner_id"]}'})
    elif current_page == 'player':
        breadcrumbs.append({'name': crumbs['team_name'], 'url': f'/team/{crumbs["owner_id"]}'})
        breadcrumbs.append({'name': crumbs['player_name'], 'url': f'/player/{crumbs["player_id"]}'})
    return breadcrumbs


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
        crumbs = {"team_name": selected_team['team_name'], "owner_id": selected_team['owner_id']}
        breadcrumbs = generate_breadcrumbs('team', crumbs=crumbs)
        return render_template('team_info.html', team=selected_team, roster=roster, breadcrumbs=breadcrumbs)
    else:
        return "Team not found", 404


@app.route('/player/<int:player_id>')
def player_info(player_id):
    player_id = str(player_id)
    player_data, player_stat_tables = get_player_info(player_id)
    if player_data:
        print(f"Player data: {player_data}")
        print(f"Player stat table: {player_stat_tables}")
        crumbs = {"team_name": player_data['owner'], "owner_id": player_data['owner_id'], "player_name": player_data['player_name'], "player_id": player_id}
        breadcrumbs = generate_breadcrumbs('player', crumbs=crumbs)
        return render_template('player_info.html', player=player_data, player_stat_tables=player_stat_tables, breadcrumbs=breadcrumbs)
    else:
        return "Player not found", 404
