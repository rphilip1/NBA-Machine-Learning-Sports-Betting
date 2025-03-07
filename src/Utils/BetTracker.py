import json
import os
import datetime
from pathlib import Path

class BetTracker:
    def __init__(self, bets_file_path='Data/bet_history.json'):
        self.bets_file_path = bets_file_path
        self.bets = self._load_bets()
        
    def _load_bets(self):
        """Load bets from the JSON file or create an empty structure if it doesn't exist"""
        if os.path.exists(self.bets_file_path):
            with open(self.bets_file_path, 'r') as f:
                return json.load(f)
        else:
            # Create directory if it doesn't exist
            Path(os.path.dirname(self.bets_file_path)).mkdir(parents=True, exist_ok=True)
            return {
                "bets": [],
                "bankroll_history": [],
                "stats": {
                    "total_bets": 0,
                    "wins": 0,
                    "losses": 0,
                    "pushes": 0,
                    "profit_loss": 0.0,
                    "roi": 0.0
                }
            }
    
    def _save_bets(self):
        """Save bets to the JSON file"""
        with open(self.bets_file_path, 'w') as f:
            json.dump(self.bets, f, indent=4)
    
    def add_bet(self, bet_data):
        """
        Add a new bet to the tracker
        
        bet_data should be a dictionary with the following keys:
        - date: date of the game (string in YYYY-MM-DD format)
        - home_team: name of the home team
        - away_team: name of the away team
        - bet_type: 'moneyline', 'spread', or 'over_under'
        - bet_pick: team name for moneyline/spread, 'over' or 'under' for over_under
        - odds: American odds for the bet
        - amount: amount wagered
        - confidence: model confidence percentage
        - sportsbook: name of the sportsbook
        """
        bet_id = len(self.bets["bets"]) + 1
        bet_data["id"] = bet_id
        bet_data["date_placed"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bet_data["status"] = "pending"  # pending, won, lost, push
        bet_data["profit_loss"] = 0.0
        
        self.bets["bets"].append(bet_data)
        self.bets["stats"]["total_bets"] += 1
        self._save_bets()
        return bet_id
    
    def update_bet_result(self, bet_id, status, score_home=None, score_away=None):
        """
        Update a bet with its result
        
        Parameters:
        - bet_id: ID of the bet to update
        - status: 'won', 'lost', or 'push'
        - score_home: final score of the home team (optional)
        - score_away: final score of the away team (optional)
        """
        for bet in self.bets["bets"]:
            if bet["id"] == bet_id:
                bet["status"] = status
                if score_home is not None and score_away is not None:
                    bet["score_home"] = score_home
                    bet["score_away"] = score_away
                
                # Calculate profit/loss
                if status == "won":
                    if bet["odds"] > 0:
                        profit = bet["amount"] * (bet["odds"] / 100)
                    else:
                        profit = bet["amount"] * (100 / abs(bet["odds"]))
                    bet["profit_loss"] = profit
                    self.bets["stats"]["wins"] += 1
                    self.bets["stats"]["profit_loss"] += profit
                elif status == "lost":
                    bet["profit_loss"] = -bet["amount"]
                    self.bets["stats"]["losses"] += 1
                    self.bets["stats"]["profit_loss"] -= bet["amount"]
                elif status == "push":
                    bet["profit_loss"] = 0
                    self.bets["stats"]["pushes"] += 1
                
                # Update ROI
                total_wagered = sum(b["amount"] for b in self.bets["bets"])
                if total_wagered > 0:
                    self.bets["stats"]["roi"] = (self.bets["stats"]["profit_loss"] / total_wagered) * 100
                
                # Update bankroll history
                self.bets["bankroll_history"].append({
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "balance": self.get_current_bankroll(),
                    "change": bet["profit_loss"]
                })
                
                self._save_bets()
                return True
        return False
    
    def get_bet(self, bet_id):
        """Get a specific bet by ID"""
        for bet in self.bets["bets"]:
            if bet["id"] == bet_id:
                return bet
        return None
    
    def get_all_bets(self):
        """Get all bets"""
        return self.bets["bets"]
    
    def get_pending_bets(self):
        """Get all pending bets"""
        return [bet for bet in self.bets["bets"] if bet["status"] == "pending"]
    
    def get_stats(self):
        """Get betting statistics"""
        return self.bets["stats"]
    
    def get_current_bankroll(self):
        """Calculate current bankroll based on initial bankroll and profit/loss"""
        initial_bankroll = 1000.0  # Default initial bankroll
        if "initial_bankroll" in self.bets:
            initial_bankroll = self.bets["initial_bankroll"]
        return initial_bankroll + self.bets["stats"]["profit_loss"]
    
    def set_initial_bankroll(self, amount):
        """Set the initial bankroll amount"""
        self.bets["initial_bankroll"] = amount
        
        # Initialize bankroll history if empty
        if not self.bets["bankroll_history"]:
            self.bets["bankroll_history"].append({
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "balance": amount,
                "change": 0
            })
        
        self._save_bets()
        return True
    
    def get_bankroll_history(self):
        """Get bankroll history"""
        return self.bets["bankroll_history"] 