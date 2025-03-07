import sys
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import date

# Add parent directory to path to import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import routers
from api.routers import predictions, bets, teams, players
from api.routers.predictions import fetch_game_data, get_ttl_hash

# Create FastAPI app
app = FastAPI(
    title="NBA Machine Learning Sports Betting",
    description="API for NBA betting predictions and bet tracking",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="api/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="api/templates")

# Include routers
app.include_router(predictions.router)
app.include_router(bets.router)
app.include_router(teams.router)
app.include_router(players.router)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main index page"""
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

# Redirect /predictions to root for convenience
@app.get("/predictions", response_class=RedirectResponse)
async def redirect_to_index():
    """Redirect /predictions to root"""
    return RedirectResponse(url="/")

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI app on http://127.0.0.1:8000")
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True) 