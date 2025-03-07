#!/usr/bin/env python3
import sqlite3
from tabulate import tabulate

def view_sqlite_bets():
    """View bets from the SQLite database"""
    db_path = 'Data/betting.sqlite'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get betting stats
        cursor.execute('SELECT COUNT(*) FROM bets')
        total_bets = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bets WHERE status = "won"')
        wins = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bets WHERE status = "lost"')
        losses = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bets WHERE status = "push"')
        pushes = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(profit_loss) FROM bets')
        profit_loss = cursor.fetchone()[0] or 0.0
        
        cursor.execute('SELECT SUM(amount) FROM bets')
        total_wagered = cursor.fetchone()[0] or 0.0
        
        roi = 0.0
        if total_wagered > 0:
            roi = (profit_loss / total_wagered) * 100
        
        # Fixed initial bankroll
        initial_bankroll = 1000.0
        
        # Get current bankroll from bankroll history
        cursor.execute('SELECT SUM(change) FROM bankroll_history')
        total_change = cursor.fetchone()[0] or 0.0
        current_bankroll = initial_bankroll + total_change
        
        # Print summary
        print("\n===== BETTING SUMMARY =====")
        print(f"Total Bets: {total_bets}")
        print(f"Record: {wins}-{losses}-{pushes}")
        print(f"Profit/Loss: ${profit_loss:.2f}")
        print(f"ROI: {roi:.2f}%")
        print(f"Current Bankroll: ${current_bankroll:.2f}")
        
        # Get all bets
        cursor.execute('''
        SELECT id, date, home_team, away_team, bet_type, bet_pick, odds, 
               amount, status, profit_loss
        FROM bets
        ORDER BY date_placed DESC
        ''')
        bets = cursor.fetchall()
        
        if bets:
            print("\n===== BET HISTORY =====")
            headers = ["ID", "Date", "Game", "Bet", "Odds", "Amount", "Status", "P/L"]
            table_data = []
            
            for bet in bets:
                bet_id, date, home_team, away_team, bet_type, bet_pick, odds, amount, status, profit_loss = bet
                
                # Format bet type
                if bet_type == 'moneyline':
                    bet_display = f"ML: {bet_pick}"
                elif bet_type == 'spread':
                    bet_display = f"Spread: {bet_pick}"
                else:
                    bet_display = f"{bet_pick.upper()}"
                
                # Format odds
                odds_display = f"+{odds}" if odds > 0 else f"{odds}"
                
                # Format profit/loss
                pl_display = f"+${profit_loss:.2f}" if profit_loss > 0 else f"${profit_loss:.2f}"
                
                table_data.append([
                    bet_id,
                    date,
                    f"{away_team} @ {home_team}",
                    bet_display,
                    odds_display,
                    f"${amount:.2f}",
                    status.upper(),
                    pl_display
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            print("\nNo bets found in database.")
            
        # Get bankroll history
        cursor.execute('''
        SELECT date, balance, change
        FROM bankroll_history
        ORDER BY date
        ''')
        history = cursor.fetchall()
        
        if history:
            print("\n===== BANKROLL HISTORY =====")
            headers = ["Date", "Balance", "Change"]
            table_data = []
            
            for entry in history:
                date, balance, change = entry
                
                # Format change
                change_display = f"+${change:.2f}" if change > 0 else f"${change:.2f}"
                
                table_data.append([
                    date,
                    f"${balance:.2f}",
                    change_display
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            print("\nNo bankroll history found.")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    view_sqlite_bets() 