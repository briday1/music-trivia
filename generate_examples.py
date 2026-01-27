#!/usr/bin/env python3
"""
Generate example bingo cards and operator table for screenshots
"""

from app import (
    generate_unique_bingo_cards,
    simulate_bingo_game,
    format_bingo_card_html
)
import pandas as pd

# Sample playlist of popular songs
SAMPLE_SONGS = [
    "Bohemian Rhapsody - Queen",
    "Stairway to Heaven - Led Zeppelin", 
    "Hotel California - Eagles",
    "Imagine - John Lennon",
    "Smells Like Teen Spirit - Nirvana",
    "Billie Jean - Michael Jackson",
    "Sweet Child O' Mine - Guns N' Roses",
    "Hey Jude - The Beatles",
    "Like a Rolling Stone - Bob Dylan",
    "Purple Haze - Jimi Hendrix",
    "What's Going On - Marvin Gaye",
    "Respect - Aretha Franklin",
    "Good Vibrations - The Beach Boys",
    "Johnny B. Goode - Chuck Berry",
    "I Want to Hold Your Hand - The Beatles",
    "God Only Knows - The Beach Boys",
    "A Day in the Life - The Beatles",
    "Layla - Derek and the Dominos",
    "Born to Run - Bruce Springsteen",
    "London Calling - The Clash",
    "One - U2",
    "Bittersweet Symphony - The Verve",
    "Wonderwall - Oasis",
    "Champagne Supernova - Oasis",
    "Creep - Radiohead",
    "Basket Case - Green Day",
    "Mr. Brightside - The Killers",
    "Boulevard of Broken Dreams - Green Day",
    "Lose Yourself - Eminem",
    "In Da Club - 50 Cent"
]

def generate_sample_cards():
    """Generate sample bingo cards and operator table"""
    
    print("Generating 10 sample bingo cards...")
    cards = generate_unique_bingo_cards(SAMPLE_SONGS, 10, 5)
    
    print("Simulating game to generate operator table...")
    results_df = simulate_bingo_game(cards, SAMPLE_SONGS)
    
    # Sort by win round for operator table
    results_df = results_df.sort_values('Win Round', na_position='last')
    
    return cards, results_df

def save_card_html(card, card_index, filename):
    """Save a bingo card as HTML file"""
    html = format_bingo_card_html(card, card_index)
    
    # Add full HTML structure
    full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Bingo Card #{card_index + 1}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    {html}
</body>
</html>
"""
    
    with open(filename, 'w') as f:
        f.write(full_html)
    
    print(f"Saved card to {filename}")

def save_operator_table_html(results_df, filename):
    """Save operator table as HTML file"""
    
    # Format the table nicely
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Operator Reference Sheet</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .info {
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th {
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .place-1 { background-color: #fff9c4; }
        .place-2 { background-color: #ffe0b2; }
        .place-3 { background-color: #ffccbc; }
        .medal {
            font-size: 20px;
        }
    </style>
</head>
<body>
    <h1>🎮 Bingo Game - Operator Reference Sheet</h1>
    
    <div class="info">
        <strong>📋 Instructions for Operator:</strong><br>
        This table shows the order in which bingo cards will win as you call songs from the playlist.
        Use this to prepare prizes and anticipate winners during the game.
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Card Index</th>
                <th>Win Round</th>
                <th>Win Type</th>
                <th>Place</th>
                <th>Song Called</th>
            </tr>
        </thead>
        <tbody>
"""
    
    for _, row in results_df.iterrows():
        place = row['Place']
        place_class = ""
        medal = ""
        
        if pd.notna(place):
            if place == 1:
                place_class = "place-1"
                medal = "🥇"
            elif place == 2:
                place_class = "place-2"
                medal = "🥈"
            elif place == 3:
                place_class = "place-3"
                medal = "🥉"
            
            place_text = f"{medal} {int(place)}"
        else:
            place_text = "-"
        
        win_round = f"Round {int(row['Win Round'])}" if pd.notna(row['Win Round']) else "No Win"
        win_type = row['Win Type'] if pd.notna(row['Win Type']) else "-"
        song = row['Song Called'] if pd.notna(row['Song Called']) else "-"
        
        html += f"""
            <tr class="{place_class}">
                <td><strong>Card #{int(row['Card Index'])}</strong></td>
                <td>{win_round}</td>
                <td>{win_type}</td>
                <td class="medal">{place_text}</td>
                <td>{song}</td>
            </tr>
"""
    
    html += """
        </tbody>
    </table>
</body>
</html>
"""
    
    with open(filename, 'w') as f:
        f.write(html)
    
    print(f"Saved operator table to {filename}")

if __name__ == "__main__":
    import os
    
    # Create output directory
    output_dir = "/tmp/bingo_examples"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate cards and results
    cards, results_df = generate_sample_cards()
    
    # Save first card as HTML
    save_card_html(cards[0], 0, f"{output_dir}/bingo_card_example.html")
    
    # Save operator table as HTML
    save_operator_table_html(results_df, f"{output_dir}/operator_table.html")
    
    print("\n✅ Examples generated successfully!")
    print(f"Files saved in: {output_dir}")
    print("\nTo view:")
    print(f"  Card: {output_dir}/bingo_card_example.html")
    print(f"  Operator Table: {output_dir}/operator_table.html")
