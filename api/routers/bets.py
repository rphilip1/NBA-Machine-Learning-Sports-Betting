from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from datetime import date

from src.Utils.BetTracker import BetTracker
from api.models.schemas import Bet, BetCreate, BetUpdate, BankrollUpdate, BettingStats, BankrollHistory

router = APIRouter(
    prefix="/bets",
    tags=["bets"],
    responses={404: {"description": "Not found"}},
)

templates = Jinja2Templates(directory="api/templates")

def get_bet_tracker():
    """Dependency to get the BetTracker instance"""
    return BetTracker()

@router.get("/", response_class=HTMLResponse)
async def get_bets_page(request: Request, tracker: BetTracker = Depends(get_bet_tracker)):
    """Get the bets tracking page"""
    all_bets = tracker.get_all_bets()
    stats = tracker.get_stats()
    bankroll = tracker.get_current_bankroll()
    bankroll_history = tracker.get_bankroll_history()
    
    return templates.TemplateResponse(
        "bets.html", 
        {
            "request": request, 
            "today": date.today(),
            "bets": all_bets,
            "stats": stats,
            "bankroll": bankroll,
            "bankroll_history": bankroll_history
        }
    )

@router.post("/add")
async def add_bet(bet: BetCreate, tracker: BetTracker = Depends(get_bet_tracker)):
    """Add a new bet"""
    bet_id = tracker.add_bet(bet.dict())
    return {"success": True, "bet_id": bet_id}

@router.post("/update/{bet_id}")
async def update_bet(
    bet_id: int, 
    bet_update: BetUpdate,
    tracker: BetTracker = Depends(get_bet_tracker)
):
    """Update a bet's result"""
    success = tracker.update_bet_result(
        bet_id, 
        bet_update.status, 
        bet_update.score_home, 
        bet_update.score_away
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Bet with ID {bet_id} not found")
    
    return {"success": True}

@router.post("/set-bankroll")
async def set_bankroll(
    bankroll_update: BankrollUpdate,
    tracker: BetTracker = Depends(get_bet_tracker)
):
    """Set initial bankroll"""
    success = tracker.set_initial_bankroll(bankroll_update.amount)
    return {"success": success}

# API endpoints for frontend

@router.get("/api/all", response_model=List[Bet])
async def get_all_bets(tracker: BetTracker = Depends(get_bet_tracker)):
    """Get all bets"""
    return tracker.get_all_bets()

@router.get("/api/pending", response_model=List[Bet])
async def get_pending_bets(tracker: BetTracker = Depends(get_bet_tracker)):
    """Get pending bets"""
    return tracker.get_pending_bets()

@router.get("/api/stats", response_model=BettingStats)
async def get_betting_stats(tracker: BetTracker = Depends(get_bet_tracker)):
    """Get betting statistics"""
    return tracker.get_stats()

@router.get("/api/bankroll")
async def get_bankroll(tracker: BetTracker = Depends(get_bet_tracker)):
    """Get current bankroll"""
    return {"bankroll": tracker.get_current_bankroll()}

@router.get("/api/bankroll-history", response_model=List[BankrollHistory])
async def get_bankroll_history(tracker: BetTracker = Depends(get_bet_tracker)):
    """Get bankroll history"""
    return tracker.get_bankroll_history()

# Form submission handlers for HTML forms

@router.post("/form/add", response_class=RedirectResponse)
async def add_bet_form(
    date: str = Form(...),
    home_team: str = Form(...),
    away_team: str = Form(...),
    bet_type: str = Form(...),
    bet_pick: str = Form(...),
    odds: int = Form(...),
    amount: float = Form(...),
    confidence: Optional[float] = Form(0),
    sportsbook: str = Form(...),
    tracker: BetTracker = Depends(get_bet_tracker)
):
    """Add a new bet from form submission"""
    bet_data = {
        "date": date,
        "home_team": home_team,
        "away_team": away_team,
        "bet_type": bet_type,
        "bet_pick": bet_pick,
        "odds": odds,
        "amount": amount,
        "confidence": confidence,
        "sportsbook": sportsbook
    }
    
    tracker.add_bet(bet_data)
    return RedirectResponse(url="/bets/", status_code=303)

@router.post("/form/update/{bet_id}", response_class=RedirectResponse)
async def update_bet_form(
    bet_id: int,
    status: str = Form(...),
    score_home: Optional[str] = Form(None),
    score_away: Optional[str] = Form(None),
    tracker: BetTracker = Depends(get_bet_tracker)
):
    """Update a bet's result from form submission"""
    score_home_int = int(score_home) if score_home else None
    score_away_int = int(score_away) if score_away else None
    
    tracker.update_bet_result(bet_id, status, score_home_int, score_away_int)
    return RedirectResponse(url="/bets/", status_code=303)

@router.post("/form/set-bankroll", response_class=RedirectResponse)
async def set_bankroll_form(
    amount: float = Form(...),
    tracker: BetTracker = Depends(get_bet_tracker)
):
    """Set initial bankroll from form submission"""
    tracker.set_initial_bankroll(amount)
    return RedirectResponse(url="/bets/", status_code=303) 