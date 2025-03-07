import os
import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

class BetTracker:
    def __init__(self, db_path='Data/betting.sqlite'):
        self.db_path = db_path
        self._ensure_db_exists()
        
    def _ensure_db_exists(self):
        """Create the database and tables if they don't exist"""
        # Create directory if it doesn't exist
        Path(os.path.dirname(self.db_path)).mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create bets table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            bet_type TEXT NOT NULL,
            bet_pick TEXT NOT NULL,
            odds INTEGER NOT NULL,
            amount REAL NOT NULL,
            confidence REAL DEFAULT 0,
            sportsbook TEXT NOT NULL,
            date_placed TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            profit_loss REAL DEFAULT 0,
            score_home INTEGER,
            score_away INTEGER
        )
        ''')
        
        # Create bankroll_history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bankroll_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            balance REAL NOT NULL,
            change REAL NOT NULL
        )
        ''')
        
        # Create settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        ''')
        
        # Insert default initial bankroll if not exists
        cursor.execute('SELECT value FROM settings WHERE key = "initial_bankroll"')
        if not cursor.fetchone():
            cursor.execute('INSERT INTO settings (key, value) VALUES (?, ?)', 
                          ('initial_bankroll', '1000.0'))
        
        # Check if bankroll history is empty
        cursor.execute('SELECT COUNT(*) FROM bankroll_history')
        if cursor.fetchone()[0] == 0:
            # Initialize with starting bankroll of $1000
            cursor.execute('''
            INSERT INTO bankroll_history (date, balance, change)
            VALUES (?, ?, ?)
            ''', (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                1000.0,  # Fixed initial bankroll
                0.0
            ))
        
        conn.commit()
        conn.close()
    
    def add_bet(self, bet_data: Dict[str, Any]) -> int:
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_placed = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
        INSERT INTO bets (
            date, home_team, away_team, bet_type, bet_pick, odds, 
            amount, confidence, sportsbook, date_placed, status, profit_loss
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bet_data["date"],
            bet_data["home_team"],
            bet_data["away_team"],
            bet_data["bet_type"],
            bet_data["bet_pick"],
            bet_data["odds"],
            bet_data["amount"],
            bet_data.get("confidence", 0),
            bet_data["sportsbook"],
            date_placed,
            "pending",
            0.0
        ))
        
        bet_id = cursor.lastrowid
        
        # Update stats
        self._update_stats(cursor)
        
        # Update bankroll history - subtract bet amount from bankroll
        current_bankroll = self.get_current_bankroll(cursor)
        bet_amount = bet_data["amount"]
        
        # Record the bankroll change when placing the bet
        cursor.execute('''
        INSERT INTO bankroll_history (date, balance, change)
        VALUES (?, ?, ?)
        ''', (
            date_placed,
            current_bankroll - bet_amount,  # New balance after placing bet
            -bet_amount  # Negative change (money leaving bankroll)
        ))
        
        conn.commit()
        conn.close()
        
        return bet_id
    
    def update_bet_result(self, bet_id: int, status: str, score_home: Optional[int] = None, 
                          score_away: Optional[int] = None) -> bool:
        """
        Update a bet with its result
        
        Parameters:
        - bet_id: ID of the bet to update
        - status: 'won', 'lost', or 'push'
        - score_home: final score of the home team (optional)
        - score_away: final score of the away team (optional)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get the bet
        cursor.execute('SELECT * FROM bets WHERE id = ?', (bet_id,))
        bet = cursor.fetchone()
        
        if not bet:
            conn.close()
            return False
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        bet_dict = dict(zip(column_names, bet))
        
        # Calculate profit/loss
        profit_loss = 0.0
        bankroll_change = 0.0
        
        if status == "won":
            if bet_dict["odds"] > 0:
                profit = bet_dict["amount"] * (bet_dict["odds"] / 100)
            else:
                profit = bet_dict["amount"] * (100 / abs(bet_dict["odds"]))
                
            profit_loss = profit
            # When you win, you get back your stake plus the profit
            bankroll_change = bet_dict["amount"] + profit
            
        elif status == "lost":
            profit_loss = -bet_dict["amount"]
            # No money returned on a loss (already subtracted when bet was placed)
            bankroll_change = 0
            
        elif status == "push":
            profit_loss = 0
            # On a push, you get your stake back
            bankroll_change = bet_dict["amount"]
        
        # Update the bet
        cursor.execute('''
        UPDATE bets 
        SET status = ?, profit_loss = ?, score_home = ?, score_away = ?
        WHERE id = ?
        ''', (status, profit_loss, score_home, score_away, bet_id))
        
        # Update stats
        self._update_stats(cursor)
        
        # Update bankroll history
        current_bankroll = self.get_current_bankroll(cursor)
        
        # Only add a bankroll history entry if there's money coming back
        if bankroll_change > 0:
            cursor.execute('''
            INSERT INTO bankroll_history (date, balance, change)
            VALUES (?, ?, ?)
            ''', (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                current_bankroll + bankroll_change,  # New balance after settling bet
                bankroll_change  # Positive change (money returning to bankroll)
            ))
        
        conn.commit()
        conn.close()
        
        return True
    
    def _update_stats(self, cursor):
        """Update betting statistics"""
        # Count total bets
        cursor.execute('SELECT COUNT(*) FROM bets')
        total_bets = cursor.fetchone()[0]
        
        # Count wins
        cursor.execute('SELECT COUNT(*) FROM bets WHERE status = "won"')
        wins = cursor.fetchone()[0]
        
        # Count losses
        cursor.execute('SELECT COUNT(*) FROM bets WHERE status = "lost"')
        losses = cursor.fetchone()[0]
        
        # Count pushes
        cursor.execute('SELECT COUNT(*) FROM bets WHERE status = "push"')
        pushes = cursor.fetchone()[0]
        
        # Calculate profit/loss
        cursor.execute('SELECT SUM(profit_loss) FROM bets')
        profit_loss = cursor.fetchone()[0] or 0.0
        
        # Calculate ROI
        cursor.execute('SELECT SUM(amount) FROM bets')
        total_wagered = cursor.fetchone()[0] or 0.0
        
        roi = 0.0
        if total_wagered > 0:
            roi = (profit_loss / total_wagered) * 100
    
    def get_bet(self, bet_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific bet by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM bets WHERE id = ?', (bet_id,))
        bet = cursor.fetchone()
        
        if not bet:
            conn.close()
            return None
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        bet_dict = dict(zip(column_names, bet))
        
        conn.close()
        return bet_dict
    
    def get_all_bets(self) -> List[Dict[str, Any]]:
        """Get all bets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM bets ORDER BY date_placed DESC')
        bets = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Convert to list of dictionaries
        bets_list = [dict(zip(column_names, bet)) for bet in bets]
        
        conn.close()
        return bets_list
    
    def get_pending_bets(self) -> List[Dict[str, Any]]:
        """Get all pending bets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM bets WHERE status = "pending" ORDER BY date_placed DESC')
        bets = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Convert to list of dictionaries
        bets_list = [dict(zip(column_names, bet)) for bet in bets]
        
        conn.close()
        return bets_list
    
    def get_stats(self) -> Dict[str, Any]:
        """Get betting statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count total bets
        cursor.execute('SELECT COUNT(*) FROM bets')
        total_bets = cursor.fetchone()[0]
        
        # Count wins
        cursor.execute('SELECT COUNT(*) FROM bets WHERE status = "won"')
        wins = cursor.fetchone()[0]
        
        # Count losses
        cursor.execute('SELECT COUNT(*) FROM bets WHERE status = "lost"')
        losses = cursor.fetchone()[0]
        
        # Count pushes
        cursor.execute('SELECT COUNT(*) FROM bets WHERE status = "push"')
        pushes = cursor.fetchone()[0]
        
        # Calculate profit/loss
        cursor.execute('SELECT SUM(profit_loss) FROM bets')
        profit_loss = cursor.fetchone()[0] or 0.0
        
        # Calculate ROI
        cursor.execute('SELECT SUM(amount) FROM bets')
        total_wagered = cursor.fetchone()[0] or 0.0
        
        roi = 0.0
        if total_wagered > 0:
            roi = (profit_loss / total_wagered) * 100
        
        conn.close()
        
        return {
            "total_bets": total_bets,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "profit_loss": profit_loss,
            "roi": roi
        }
    
    def get_current_bankroll(self, cursor=None) -> float:
        """Calculate current bankroll based on initial bankroll and bankroll history"""
        close_conn = False
        if cursor is None:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            close_conn = True
        
        # Fixed initial bankroll
        initial_bankroll = 1000.0
        
        # Get sum of all changes in bankroll history
        cursor.execute('SELECT SUM(change) FROM bankroll_history')
        total_change = cursor.fetchone()[0] or 0.0
        
        if close_conn:
            conn.close()
        
        return initial_bankroll + total_change
    
    def get_bankroll_history(self) -> List[Dict[str, Any]]:
        """Get bankroll history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT date, balance, change FROM bankroll_history ORDER BY date')
        history = cursor.fetchall()
        
        # Convert to list of dictionaries
        history_list = [
            {"date": item[0], "balance": item[1], "change": item[2]}
            for item in history
        ]
        
        conn.close()
        return history_list
    
    def migrate_from_json(self, json_path='Data/bet_history.json'):
        """Migrate data from JSON file to SQLite database"""
        import json
        
        if not os.path.exists(json_path):
            return False
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM bets')
            cursor.execute('DELETE FROM bankroll_history')
            
            # Set fixed initial bankroll
            initial_bankroll = 1000.0
            
            # Initialize bankroll history with initial bankroll
            cursor.execute('''
            INSERT INTO bankroll_history (date, balance, change)
            VALUES (?, ?, ?)
            ''', (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                initial_bankroll,
                0.0
            ))
            
            current_bankroll = initial_bankroll
            
            # Migrate bets
            for bet in data.get("bets", []):
                # Insert the bet
                cursor.execute('''
                INSERT INTO bets (
                    id, date, home_team, away_team, bet_type, bet_pick, odds, 
                    amount, confidence, sportsbook, date_placed, status, profit_loss,
                    score_home, score_away
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    bet.get("id"),
                    bet.get("date"),
                    bet.get("home_team"),
                    bet.get("away_team"),
                    bet.get("bet_type"),
                    bet.get("bet_pick"),
                    bet.get("odds"),
                    bet.get("amount"),
                    bet.get("confidence", 0),
                    bet.get("sportsbook"),
                    bet.get("date_placed"),
                    bet.get("status"),
                    bet.get("profit_loss", 0.0),
                    bet.get("score_home"),
                    bet.get("score_away")
                ))
                
                # Record bet placement (subtract amount from bankroll)
                bet_amount = bet.get("amount", 0.0)
                current_bankroll -= bet_amount
                
                cursor.execute('''
                INSERT INTO bankroll_history (date, balance, change)
                VALUES (?, ?, ?)
                ''', (
                    bet.get("date_placed"),
                    current_bankroll,
                    -bet_amount
                ))
                
                # If bet is settled, record the outcome
                if bet.get("status") != "pending":
                    bankroll_change = 0.0
                    
                    if bet.get("status") == "won":
                        # Calculate winnings
                        if bet.get("odds") > 0:
                            profit = bet_amount * (bet.get("odds") / 100)
                        else:
                            profit = bet_amount * (100 / abs(bet.get("odds")))
                        
                        # When you win, you get back your stake plus the profit
                        bankroll_change = bet_amount + profit
                        
                    elif bet.get("status") == "push":
                        # On a push, you get your stake back
                        bankroll_change = bet_amount
                    
                    # Only add a bankroll history entry if there's money coming back
                    if bankroll_change > 0:
                        current_bankroll += bankroll_change
                        
                        cursor.execute('''
                        INSERT INTO bankroll_history (date, balance, change)
                        VALUES (?, ?, ?)
                        ''', (
                            # Use date_placed + 1 day as a proxy for settlement date
                            datetime.datetime.strptime(bet.get("date_placed"), "%Y-%m-%d %H:%M:%S") + 
                            datetime.timedelta(days=1),
                            current_bankroll,
                            bankroll_change
                        ))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error migrating from JSON: {e}")
            return False 