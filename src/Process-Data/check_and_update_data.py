import os
import sys
import sqlite3
import datetime
import toml
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(1, os.path.join(sys.path[0], '../..'))
from src.Utils.tools import get_json_data, to_data_frame
from sbrscrape import Scoreboard
import pandas as pd
import random
import time

def get_config():
    """Load configuration from config.toml"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.toml")
    return toml.load(config_path)

def check_team_data_freshness():
    """Check the most recent date in TeamData.sqlite"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Data/TeamData.sqlite")
    
    if not os.path.exists(db_path):
        print("TeamData.sqlite not found. No data exists yet.")
        return None, None
    
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    
    # Get the most recent table (date)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC LIMIT 1;")
    result = cursor.fetchone()
    
    if not result:
        print("No tables found in TeamData.sqlite")
        con.close()
        return None, None
    
    latest_date = result[0]
    latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d").date()
    
    # Get current season from config
    config = get_config()
    current_season = None
    for key, value in config['get-data'].items():
        end_date = datetime.strptime(value['end_date'], "%Y-%m-%d").date()
        if end_date > datetime.now().date():
            current_season = key
            break
    
    if not current_season:
        current_season = list(config['get-data'].keys())[-1]
    
    con.close()
    
    return latest_date_obj, current_season

def check_odds_data_freshness():
    """Check the most recent date in OddsData.sqlite"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Data/OddsData.sqlite")
    
    if not os.path.exists(db_path):
        print("OddsData.sqlite not found. No data exists yet.")
        return None, None
    
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    
    # Get the most recent season table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC LIMIT 1;")
    result = cursor.fetchone()
    
    if not result:
        print("No tables found in OddsData.sqlite")
        con.close()
        return None, None
    
    latest_table = result[0]
    
    # Get the most recent date in that table
    try:
        cursor.execute(f"SELECT Date FROM '{latest_table}' ORDER BY Date DESC LIMIT 1;")
        result = cursor.fetchone()
        
        if not result:
            print(f"No data found in table {latest_table}")
            con.close()
            return None, latest_table
        
        latest_date = result[0]
        latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d").date()
        
        con.close()
        return latest_date_obj, latest_table
    except sqlite3.OperationalError:
        print(f"Error querying table {latest_table}")
        con.close()
        return None, latest_table

def update_team_data(start_date, end_date, season):
    """Update team data from start_date to end_date"""
    print(f"Updating team data from {start_date} to {end_date} for season {season}")
    
    config = get_config()
    url = config['data_url']
    season_config = config['get-data'][season]
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Data/TeamData.sqlite")
    con = sqlite3.connect(db_path)
    
    date_pointer = start_date
    while date_pointer <= end_date:
        print(f"Getting team data for: {date_pointer}")
        
        try:
            raw_data = get_json_data(
                url.format(date_pointer.month, date_pointer.day, season_config['start_year'], date_pointer.year, season))
            df = to_data_frame(raw_data)
            
            df['Date'] = str(date_pointer)
            df.to_sql(date_pointer.strftime("%Y-%m-%d"), con, if_exists="replace")
            
            # Sleep to avoid rate limiting
            time.sleep(random.randint(1, 3))
        except Exception as e:
            print(f"Error getting data for {date_pointer}: {e}")
        
        date_pointer = date_pointer + timedelta(days=1)
    
    con.close()
    print("Team data update completed")

def update_odds_data(start_date, end_date, season_key):
    """Update odds data from start_date to end_date"""
    print(f"Updating odds data from {start_date} to {end_date} for {season_key}")
    
    config = get_config()
    sportsbook = 'fanduel'
    df_data = []
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Data/OddsData.sqlite")
    con = sqlite3.connect(db_path)
    
    # Get existing data to track teams' last played dates
    teams_last_played = {}
    try:
        cursor = con.cursor()
        table_name = f"odds_{season_key}_new"
        cursor.execute(f"SELECT * FROM '{table_name}' ORDER BY Date DESC LIMIT 1000;")
        existing_data = cursor.fetchall()
        
        # Extract team names and dates from existing data
        for row in existing_data:
            home_team = row[2]  # Adjust index based on your schema
            away_team = row[3]  # Adjust index based on your schema
            game_date = datetime.strptime(row[1], "%Y-%m-%d").date()  # Adjust index based on your schema
            
            if home_team not in teams_last_played or teams_last_played[home_team] < game_date:
                teams_last_played[home_team] = game_date
            
            if away_team not in teams_last_played or teams_last_played[away_team] < game_date:
                teams_last_played[away_team] = game_date
    except (sqlite3.OperationalError, IndexError) as e:
        print(f"Could not load existing data: {e}")
    
    date_pointer = start_date
    while date_pointer <= end_date:
        print(f"Getting odds data for: {date_pointer}")
        
        try:
            sb = Scoreboard(date=date_pointer)
            
            if not hasattr(sb, "games"):
                date_pointer = date_pointer + timedelta(days=1)
                continue
            
            for game in sb.games:
                if game['home_team'] not in teams_last_played:
                    teams_last_played[game['home_team']] = date_pointer
                    home_games_rested = timedelta(days=7)  # start of season, big number
                else:
                    current_date = date_pointer
                    home_games_rested = current_date - teams_last_played[game['home_team']]
                    teams_last_played[game['home_team']] = current_date
                
                if game['away_team'] not in teams_last_played:
                    teams_last_played[game['away_team']] = date_pointer
                    away_games_rested = timedelta(days=7)  # start of season, big number
                else:
                    current_date = date_pointer
                    away_games_rested = current_date - teams_last_played[game['away_team']]
                    teams_last_played[game['away_team']] = current_date
                
                try:
                    df_data.append({
                        'Date': date_pointer,
                        'Home': game['home_team'],
                        'Away': game['away_team'],
                        'OU': game['total'][sportsbook],
                        'Spread': game['away_spread'][sportsbook],
                        'ML_Home': game['home_ml'][sportsbook],
                        'ML_Away': game['away_ml'][sportsbook],
                        'Points': game['away_score'] + game['home_score'],
                        'Win_Margin': game['home_score'] - game['away_score'],
                        'Days_Rest_Home': home_games_rested.days,
                        'Days_Rest_Away': away_games_rested.days
                    })
                except KeyError:
                    print(f"No {sportsbook} odds data found for game: {game}")
        except Exception as e:
            print(f"Error getting odds data for {date_pointer}: {e}")
        
        date_pointer = date_pointer + timedelta(days=1)
        time.sleep(random.randint(1, 3))
    
    if df_data:
        df = pd.DataFrame(df_data)
        table_name = f"odds_{season_key}_new"
        df.to_sql(table_name, con, if_exists="append")
    
    con.close()
    print("Odds data update completed")

def main():
    """Main function to check and update data if needed"""
    print("Checking data freshness...")
    
    # Get current date (yesterday to ensure games are completed)
    yesterday = datetime.now().date() - timedelta(days=1)
    
    # Check team data freshness
    team_latest_date, current_season = check_team_data_freshness()
    if team_latest_date:
        days_since_update = (yesterday - team_latest_date).days
        print(f"Team data last updated: {team_latest_date} ({days_since_update} days ago)")
        
        # Update if data is not current
        if days_since_update > 0:
            start_date = team_latest_date + timedelta(days=1)
            update_team_data(start_date, yesterday, current_season)
        else:
            print("Team data is up to date")
    else:
        print("No team data found. Please run Get_Data.py first to initialize the database.")
    
    # Check odds data freshness
    odds_latest_date, latest_table = check_odds_data_freshness()
    if odds_latest_date:
        days_since_update = (yesterday - odds_latest_date).days
        print(f"Odds data last updated: {odds_latest_date} ({days_since_update} days ago)")
        
        # Update if data is not current
        if days_since_update > 0:
            start_date = odds_latest_date + timedelta(days=1)
            # Extract season key from table name (e.g., "odds_2023-24_new" -> "2023-24")
            season_key = latest_table.split("_")[1] if "_" in latest_table else None
            if season_key:
                update_odds_data(start_date, yesterday, season_key)
            else:
                print(f"Could not determine season from table name: {latest_table}")
        else:
            print("Odds data is up to date")
    else:
        print("No odds data found. Please run Get_Odds_Data.py first to initialize the database.")
    
    print("Data check and update completed")

if __name__ == "__main__":
    main() 