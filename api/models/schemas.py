from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date

class GamePrediction(BaseModel):
    """Game prediction model"""
    home_team: str
    away_team: str
    home_confidence: Optional[float] = None
    away_confidence: Optional[float] = None
    ou_pick: str
    ou_value: str
    ou_confidence: Optional[float] = None
    home_team_odds: Optional[str] = None
    away_team_odds: Optional[str] = None
    home_team_ev: Optional[str] = None
    away_team_ev: Optional[str] = None

class BetCreate(BaseModel):
    """Model for creating a new bet"""
    date: str
    home_team: str
    away_team: str
    bet_type: str
    bet_pick: str
    odds: int
    amount: float
    confidence: Optional[float] = 0
    sportsbook: str

class BetUpdate(BaseModel):
    """Model for updating a bet result"""
    status: str
    score_home: Optional[int] = None
    score_away: Optional[int] = None

class Bet(BaseModel):
    """Complete bet model"""
    id: int
    date: str
    home_team: str
    away_team: str
    bet_type: str
    bet_pick: str
    odds: int
    amount: float
    confidence: Optional[float] = 0
    sportsbook: str
    date_placed: str
    status: str
    profit_loss: float
    score_home: Optional[int] = None
    score_away: Optional[int] = None

class BankrollHistory(BaseModel):
    """Bankroll history entry"""
    date: str
    balance: float
    change: float

class BettingStats(BaseModel):
    """Betting statistics"""
    total_bets: int
    wins: int
    losses: int
    pushes: int
    profit_loss: float
    roi: float

class Player(BaseModel):
    """Player model"""
    name: str
    shortName: Optional[str] = None
    headshot: Optional[str] = None
    injury: str = "Healthy"
    position: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    college: Optional[str] = None
    experience: Optional[str] = None
    jerseyNum: Optional[str] = None
    playerId: Optional[str] = None
    birthDate: Optional[str] = None

class TeamData(BaseModel):
    """Team data model"""
    success: bool
    players: Optional[List[Player]] = None
    error: Optional[str] = None

class PlayerGameStats(BaseModel):
    """Player game stats model"""
    gameID: str
    gameDate: str
    opponent: str
    result: str
    minutes: Optional[str] = None
    points: Optional[int] = None
    rebounds: Optional[int] = None
    assists: Optional[int] = None
    steals: Optional[int] = None
    blocks: Optional[int] = None
    turnovers: Optional[int] = None
    fieldGoals: Optional[str] = None
    threePointers: Optional[str] = None
    freeThrows: Optional[str] = None

class PlayerInfo(BaseModel):
    """Player info model"""
    name: str
    position: Optional[str] = None
    number: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    team: Optional[str] = None
    college: Optional[str] = None
    experience: Optional[str] = None
    headshot: Optional[str] = None
    injury: str = "Healthy"

class PlayerStats(BaseModel):
    """Player stats response model"""
    success: bool
    games: Optional[List[PlayerGameStats]] = None
    player: Optional[PlayerInfo] = None
    error: Optional[str] = None 