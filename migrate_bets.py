#!/usr/bin/env python3
from src.Utils.BetTracker import BetTracker
import os

def migrate_bets():
    """Migrate bet data from JSON to SQLite"""
    json_path = 'Data/bet_history.json.bak'
    db_path = 'Data/betting.sqlite'
    
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        return False
    
    # Create a new BetTracker instance
    tracker = BetTracker(db_path)
    
    # Migrate data
    success = tracker.migrate_from_json(json_path)
    
    if success:
        print(f"Successfully migrated bet data from {json_path} to {db_path}")
        return True
    else:
        print(f"Error: Failed to migrate bet data")
        return False

if __name__ == "__main__":
    migrate_bets() 