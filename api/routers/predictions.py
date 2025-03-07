from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, List, Optional
import subprocess
import re
import json
import time
from functools import lru_cache
from datetime import date

from api.models.schemas import GamePrediction

router = APIRouter(
    prefix="/predictions",
    tags=["predictions"],
    responses={404: {"description": "Not found"}},
)

templates = Jinja2Templates(directory="api/templates")

# Team abbreviations dictionary
team_abbreviations = {
    'Orlando Magic': 'ORL',
    'Minnesota Timberwolves': 'MIN',
    'Miami Heat': 'MIA',
    'Boston Celtics': 'BOS',
    'LA Clippers': 'LAC',
    'Denver Nuggets': 'DEN',
    'Detroit Pistons': 'DET',
    'Atlanta Hawks': 'ATL',
    'Cleveland Cavaliers': 'CLE',
    'Toronto Raptors': 'TOR',
    'Washington Wizards': 'WAS',
    'Phoenix Suns': 'PHO',
    'San Antonio Spurs': 'SA',
    'Chicago Bulls': 'CHI',
    'Charlotte Hornets': 'CHA',
    'Philadelphia 76ers': 'PHI',
    'New Orleans Pelicans': 'NO',
    'Sacramento Kings': 'SAC',
    'Dallas Mavericks': 'DAL',
    'Houston Rockets': 'HOU',
    'Brooklyn Nets': 'BKN',
    'New York Knicks': 'NY',
    'Utah Jazz': 'UTA',
    'Oklahoma City Thunder': 'OKC',
    'Portland Trail Blazers': 'POR',
    'Indiana Pacers': 'IND',
    'Milwaukee Bucks': 'MIL',
    'Golden State Warriors': 'GS',
    'Memphis Grizzlies': 'MEM',
    'Los Angeles Lakers': 'LAL'
}

def get_ttl_hash(seconds=600):
    """Return the same value within `seconds` time period"""
    return round(time.time() / seconds)

@lru_cache()
def fetch_game_data(sportsbook: str = "fanduel", ttl_hash=None):
    """Fetch game data from the prediction model"""
    # Delete ttl_hash to avoid it being used in the function
    if ttl_hash is not None:
        del ttl_hash
        
    cmd = ["python", "main.py", "-xgb", f"-odds={sportsbook}"]
    try:
        stdout = subprocess.check_output(cmd).decode()
        
        # Regular expressions to extract data
        data_re = re.compile(r'\n(?P<home_team>[\w ]+)(\((?P<home_confidence>[\d+\.]+)%\))? vs (?P<away_team>[\w ]+)(\((?P<away_confidence>[\d+\.]+)%\))?: (?P<ou_pick>OVER|UNDER) (?P<ou_value>[\d+\.]+) (\((?P<ou_confidence>[\d+\.]+)%\))?', re.MULTILINE)
        ev_re = re.compile(r'(?P<team>[\w ]+) EV: (?P<ev>[-\d+\.]+)', re.MULTILINE)
        odds_re = re.compile(r'(?P<away_team>[\w ]+) \((?P<away_team_odds>-?\d+)\) @ (?P<home_team>[\w ]+) \((?P<home_team_odds>-?\d+)\)', re.MULTILINE)
        
        games = {}
        for match in data_re.finditer(stdout):
            game_dict = {
                'away_team': match.group('away_team').strip(),
                'home_team': match.group('home_team').strip(),
                'away_confidence': match.group('away_confidence'),
                'home_confidence': match.group('home_confidence'),
                'ou_pick': match.group('ou_pick'),
                'ou_value': match.group('ou_value'),
                'ou_confidence': match.group('ou_confidence')
            }
            
            for ev_match in ev_re.finditer(stdout):
                if ev_match.group('team') == game_dict['away_team']:
                    game_dict['away_team_ev'] = ev_match.group('ev')
                if ev_match.group('team') == game_dict['home_team']:
                    game_dict['home_team_ev'] = ev_match.group('ev')
                    
            for odds_match in odds_re.finditer(stdout):
                if odds_match.group('away_team') == game_dict['away_team']:
                    game_dict['away_team_odds'] = odds_match.group('away_team_odds')
                if odds_match.group('home_team') == game_dict['home_team']:
                    game_dict['home_team_odds'] = odds_match.group('home_team_odds')
            
            games[f"{game_dict['away_team']}:{game_dict['home_team']}"] = game_dict
            
        return games
    except subprocess.CalledProcessError as e:
        print(f"Error running prediction: {e}")
        return {}

@router.get("/", response_class=HTMLResponse)
async def get_predictions_page(request: Request):
    """Get the predictions page"""
    # Get predictions from different sportsbooks
    fanduel = fetch_game_data(sportsbook="fanduel", ttl_hash=get_ttl_hash())
    draftkings = fetch_game_data(sportsbook="draftkings", ttl_hash=get_ttl_hash())
    betmgm = fetch_game_data(sportsbook="betmgm", ttl_hash=get_ttl_hash())
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "today": date.today(),
            "data": {
                "fanduel": fanduel,
                "draftkings": draftkings,
                "betmgm": betmgm
            }
        }
    )

@router.get("/api/sportsbooks/{sportsbook}", response_model=Dict[str, GamePrediction])
async def get_predictions(sportsbook: str):
    """Get predictions for a specific sportsbook"""
    if sportsbook not in ["fanduel", "draftkings", "betmgm"]:
        raise HTTPException(status_code=400, detail="Invalid sportsbook. Choose from: fanduel, draftkings, betmgm")
    
    predictions = fetch_game_data(sportsbook=sportsbook, ttl_hash=get_ttl_hash())
    return predictions

@router.get("/api/games", response_model=List[GamePrediction])
async def get_games():
    """Get all games for the bet form"""
    fanduel = fetch_game_data(sportsbook="fanduel", ttl_hash=get_ttl_hash())
    games_data = []
    
    for game_key in fanduel:
        teams = game_key.split(':')
        game_data = fanduel[game_key]
        games_data.append({
            "home_team": teams[1],
            "away_team": teams[0],
            "home_team_odds": game_data.get("home_team_odds"),
            "away_team_odds": game_data.get("away_team_odds"),
            "ou_value": game_data.get("ou_value"),
            "home_confidence": game_data.get("home_confidence"),
            "away_confidence": game_data.get("away_confidence"),
            "ou_confidence": game_data.get("ou_confidence"),
            "ou_pick": game_data.get("ou_pick")
        })
    
    return games_data 