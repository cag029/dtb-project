from flask import Flask, render_template, request, redirect, url_for
import supabase
import requests

app = Flask(__name__)

# Init supabase client
supabase_url = 'https://tiektbwpfezprueyljzt.supabase.co'
supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRpZWt0YndwZmV6cHJ1ZXlsanp0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTM5MzU3MzEsImV4cCI6MjAyOTUxMTczMX0.BlyWTAYM6R-STVArXF61aGFrylK6k9HZNn4PyCiIF-I'  # Replace with your Supabase API key
client = supabase.create_client(supabase_url, supabase_key)

# Map primary key column names to each table for ease of access
primary_keys = {
    'Player': 'player_ID',
    'Game': 'game_ID',
    'Team': 'team_ID'
}


# Insert data into a supabase table
def insert_data_into_table(table_name, data):
    client.table(table_name).insert(data).execute()


# Delete data from a supabase table
def delete_data_from_table(table_name, ID):
    key_name = primary_keys[table_name]
    client.table(table_name).delete().eq(key_name, ID).execute()


# Route to display the index page with buttons to add or remove data
@app.route('/')
def index():
    return render_template('index.html')


# Route to handle adding data
@app.route('/add', methods=['POST'])
def add_data():
    table_name = request.form['table']
    data = {}

    # Construct data dictionary based on the selected table
    if table_name == 'Player':
        data = {
            'player_ID': request.form.get('player_ID'),
            'team_ID': request.form.get('team_ID'),
            'player_name': request.form.get('player_name'),
            'player_position': request.form.get('player_position')
        }
    elif table_name == 'Game':
        data = {
            'game_ID': request.form.get('game_ID'),
            'team_one_ID': request.form.get('team_one_ID'),
            'team_two_ID': request.form.get('team_two_ID'),
            'team_one_score': request.form.get('team_one_score'),
            'team_two_score': request.form.get('team_two_score'),
            'date': request.form.get('date')
        }
    elif table_name == 'Team':
        data = {
            'team_ID': request.form.get('team_ID_input'),
            'location': request.form.get('location'),
            'nickname': request.form.get('nickname'),
            'conference': request.form.get('conference'),
            'division': request.form.get('division')
        }

    # Check for missing fields
    required_fields = {
        'Player': ['player_ID', 'team_ID', 'player_name', 'player_position'],
        'Game': ['game_ID', 'team_one_ID', 'team_two_ID', 'team_one_score', 'team_two_score', 'date'],
        'Team': ['team_ID', 'location', 'nickname', 'conference', 'division']
    }

    missing_fields = [field for field in required_fields[table_name] if not data.get(field)]
    if missing_fields:
        error_message = f"Please fill out all required fields: {', '.join(missing_fields)}"
        return redirect(url_for('index', error=error_message))

    # Insert data into the table
    insert_data_into_table(table_name, [data])
    return redirect(url_for('index'))


# Route to handle deleting a player
@app.route('/delete_player', methods=['POST'])
def delete_player():
    player_id = request.form['playerID']
    delete_data_from_table('Player', player_id)
    return redirect(url_for('index'))


# Route to handle deleting a game
@app.route('/delete_game', methods=['POST'])
def delete_game():
    game_id = request.form['gameID']
    delete_data_from_table('Game', game_id)
    return redirect(url_for('index'))


# Route to handle deleting a team
@app.route('/delete_team', methods=['POST'])
def delete_team():
    team_id = request.form['teamID']
    delete_data_from_table('Team', team_id)
    return redirect(url_for('index'))


# Route to handle displaying all members of a specified team
@app.route('/team_members', methods=['GET', 'POST'])
def team_members():
    if request.method == 'POST':
        team_id = request.form.get('team_ID')
        print("Received team ID:", team_id)

        # Query the database for team members based on team ID
        try:
            response = client.table('Player').select('*').eq('team_ID', team_id).execute()
            print("Supabase response:", response)

            if hasattr(response, 'data') and response.data:
                team_members = response.data
                return render_template('team_members.html', team_members=team_members)
            else:
                error_message = "No players found for the specified team."
                return render_template('team_members.html', error_message=error_message)
        except Exception as e:
            error_message = f"Failed to retrieve team members. Error: {str(e)}"
            return render_template('team_members.html', error_message=error_message)

    return render_template('team_members.html', team_members=None)


# Route to handle displaying all players of a specified position
@app.route('/position_members', methods=['GET', 'POST'])
def position_members():
    if request.method == 'POST':
        position = request.form.get('position')
        print("Received position:", position)

        # Query the database for players based on position
        try:
            response = client.table('Player').select('*').eq('player_position', position).execute()
            print("Supabase response:", response)

            if hasattr(response, 'data') and response.data:
                position_members = response.data

                # Fetch team name for each player
                for member in position_members:
                    team_response = client.table('Team').select('nickname').eq('team_ID', member['team_ID']).execute()
                    if hasattr(team_response, 'data') and team_response.data:
                        team_name = team_response.data[0]['nickname']
                        member['team_name'] = team_name
                    else:
                        member['team_name'] = "Unknown"

                return render_template('position_members.html', position_members=position_members)
            else:
                error_message = "No players found for the specified position."
                return render_template('position_members.html', error_message=error_message)
        except Exception as e:
            error_message = f"Failed to retrieve players by position. Error: {str(e)}"
            return render_template('position_members.html', error_message=error_message)

    return render_template('position_members.html', position_members=None)


# Route to handle displaying all teams arranged by conference sorted by wins
@app.route('/teams_by_conference')
def teams_by_conference():
    # Query all teams from the database
    teams_response = client.table('Team').select('*').execute()
    teams = teams_response.data

    # Query all games from the database
    games_response = client.table('Game').select('*').execute()
    games = games_response.data

    # Calculate number of wins for each team
    team_wins = {}
    for game in games:
        if game['team_one_score'] > game['team_two_score']:
            team_wins[game['team_one_ID']] = team_wins.get(game['team_one_ID'], 0) + 1
        elif game['team_one_score'] < game['team_two_score']:
            team_wins[game['team_two_ID']] = team_wins.get(game['team_two_ID'], 0) + 1

    # Add number of wins to each team in the teams list
    for team in teams:
        team['wins'] = team_wins.get(team['team_ID'], 0)

    # Separate teams by conference and sort them by wins
    afc_teams = sorted([team for team in teams if team['conference'] == 'AFC'], key=lambda x: x['wins'], reverse=True)
    nfc_teams = sorted([team for team in teams if team['conference'] == 'NFC'], key=lambda x: x['wins'], reverse=True)

    return render_template('teams_by_conference.html', afc_teams=afc_teams, nfc_teams=nfc_teams)


# not working
# Route to display all games for a team
@app.route('/games_for_team', methods=['POST'])
def games_for_team():
    # Extract team ID from the form submission
    team_ID = request.form.get('team_ID')
    print("Submitted team ID:", team_ID)  # Debug

    try:
        # Query games where the submitted team_ID matches team_one_ID or team_two_ID
        games_response = client.table('Game').select('*').execute()
        all_games = games_response.data

        # Filter games where the submitted team_ID matches team_one_ID or team_two_ID
        team_games = [game for game in all_games if str(game['team_one_ID']) == str(team_ID) or str(game['team_two_ID']) == str(team_ID)]
        print("Filtered games:")
        for game in team_games:
            print(game)  # Debug

        # If games are found render the template with the filtered games data
        if team_games:
            return render_template('games_for_team.html', games=team_games, team_ID=team_ID)
        # If no games are found for the specified team render the template with an indicator
        else:
            return render_template('games_for_team.html', games=None, team_ID=team_ID, message="No games found for the specified team.")
    except Exception as e:
        # If an error occurs during the process render the template with an error
        return render_template('games_for_team.html', games=None, team_ID=team_ID, error_message=str(e))


# Route to handle changing a players team
@app.route('/change_player_team', methods=['POST'])
def change_player_team():
    player_id = request.form['playerID']
    new_team_id = request.form['newTeamID']

    # Update players team in the database
    try:
        client.table('Player').update({'team_ID': new_team_id}).eq('player_ID', player_id).execute()
        return redirect(url_for('index'))
    except Exception as e:
        error_message = f"Failed to change player's team. Error: {str(e)}"
        return redirect(url_for('index', error=error_message))


# Route to handle viewing results on a given date
@app.route('/games_by_date', methods=['POST'])
def view_results():
    date = request.form['date']

    try:
        # Query games for the specified date
        games_response = client.table('Game').select('*').eq('date', date).execute()
        games = games_response.data

        if games:
            for game in games:
                # Fetch team information for team one
                team_one_response = client.table('Team').select('nickname', 'location').eq('team_ID', game['team_one_ID']).execute()
                team_one_data = team_one_response.data[0] if team_one_response.data else None
                team_one_nickname = team_one_data['nickname'] if team_one_data else ''
                team_one_location = team_one_data['location'] if team_one_data else ''

                # Fetch team information for team two
                team_two_response = client.table('Team').select('nickname', 'location').eq('team_ID', game['team_two_ID']).execute()
                team_two_data = team_two_response.data[0] if team_two_response.data else None
                team_two_nickname = team_two_data['nickname'] if team_two_data else ''
                team_two_location = team_two_data['location'] if team_two_data else ''

                # Determine the winner
                if game['team_one_score'] > game['team_two_score']:
                    game['winner'] = team_one_nickname
                elif game['team_one_score'] < game['team_two_score']:
                    game['winner'] = team_two_nickname
                else:
                    game['winner'] = 'Tie'

                game['team_one_nickname'] = team_one_nickname
                game['team_two_nickname'] = team_two_nickname
                game['team_one_location'] = team_one_location
                game['team_two_location'] = team_two_location

            return render_template('games_by_date.html', games=games)
        else:
            return render_template('games_by_date.html', games=None, message="No results found for the specified date.")
    except Exception as e:
        return render_template('games_by_date.html', games=None, error_message=str(e))


if __name__ == '__main__':
    app.run(debug=True)