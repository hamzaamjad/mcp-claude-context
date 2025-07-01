#!/usr/bin/env python3
"""
Helper script to migrate existing data to v0.5.0
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from deployment.scripts.migrate_data import main

if __name__ == "__main__":
    print("Starting migration to v0.5.0...")
    print("This will convert your JSON files to SQLite database.")
    print()
    
    response = input("Continue? (y/n): ")
    if response.lower() == 'y':
        main()
    else:
        print("Migration cancelled.")
