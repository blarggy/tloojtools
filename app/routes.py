from flask import render_template

from app import app

@app.route('/')
@app.route('/index')
def index():
    league = [
        {
            'team': {'username': 'blarggy'},
            'player_name': 'Kenny McIntosh'
        },
        {
            'team': {'username': 'joe'},
            'player_name': 'Trent McDuffie'
        },
    ]
    return render_template('index.html', title='Home', league_info=league)