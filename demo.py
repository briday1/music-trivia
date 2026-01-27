#!/usr/bin/env python3
"""
Demo script showing the Spotify Bingo app functionality without Spotify API
This demonstrates the core features with sample data.
"""

from app import (
    create_bingo_card,
    generate_unique_bingo_cards,
    simulate_bingo_game,
    format_bingo_card_html
)
import pandas as pd

def demo_bingo_game():
    """Demonstrate the bingo game with sample songs"""
    
    print("🎵 Spotify Bingo Game Demo")
    print("=" * 70)
    
    # Sample songs (simulating a Spotify playlist)
    sample_songs = [
        "Bohemian Rhapsody", "Stairway to Heaven", "Hotel California",
        "Imagine", "Smells Like Teen Spirit", "Billie Jean",
        "Sweet Child O' Mine", "Hey Jude", "Like a Rolling Stone",
        "Purple Haze", "What's Going On", "Respect",
        "Good Vibrations", "Johnny B. Goode", "I Want to Hold Your Hand",
        "God Only Knows", "A Day in the Life", "Layla",
        "Born to Run", "London Calling", "One", "Bittersweet Symphony",
        "Wonderwall", "Champagne Supernova", "Creep"
    ]
    
    print(f"\n📀 Playlist: Classic Rock Hits")
    print(f"Total Songs: {len(sample_songs)}")
    print(f"Sample Songs: {', '.join(sample_songs[:5])}...\n")
    
    # Generate bingo cards
    num_cards = 10
    card_size = 5
    
    print(f"🎲 Generating {num_cards} unique {card_size}x{card_size} bingo cards...\n")
    cards = generate_unique_bingo_cards(sample_songs, num_cards, card_size)
    
    # Show first card
    print("📋 Sample Bingo Card #1:")
    print("=" * 70)
    print("     B            I            N            G            O")
    print("-" * 70)
    for row in cards[0]:
        # Truncate long names for display
        row_display = [f"{song[:12]:<12}" for song in row]
        print(" | ".join(row_display))
    print("=" * 70)
    
    # Simulate game
    print("\n🎮 Simulating Bingo Game...\n")
    results_df = simulate_bingo_game(cards, sample_songs)
    
    # Show winners
    print("🏆 Winners:")
    print("-" * 70)
    
    for place in [1, 2, 3]:
        winner = results_df[results_df['Place'] == place]
        if not winner.empty:
            card_idx = winner['Card Index'].values[0]
            round_num = winner['Win Round'].values[0]
            win_type = winner['Win Type'].values[0]
            song = winner['Song Called'].values[0]
            
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            ordinals = {1: "1st", 2: "2nd", 3: "3rd"}
            print(f"{medals[place]} {ordinals[place]} Place: Card #{card_idx}")
            print(f"   - Won in Round: {round_num}")
            print(f"   - Win Type: {win_type}")
            print(f"   - Winning Song: {song}")
            print()
    
    # Show operator table
    print("📊 Operator Control Table (First 10 Results):")
    print("=" * 70)
    display_df = results_df.sort_values('Win Round', na_position='last').head(10)
    print(display_df.to_string(index=False))
    print("=" * 70)
    
    # Statistics
    print("\n📈 Statistics:")
    print(f"   - Total Cards: {len(cards)}")
    print(f"   - Cards that won: {results_df['Place'].notna().sum()}")
    print(f"   - Average win round: {results_df['Win Round'].mean():.1f}")
    print(f"   - Earliest win: Round {results_df['Win Round'].min():.0f}")
    print(f"   - Latest win: Round {results_df['Win Round'].dropna().max():.0f}")
    
    print("\n✅ Demo completed successfully!")
    print("\nTo use with real Spotify playlists:")
    print("   streamlit run app.py")

if __name__ == "__main__":
    demo_bingo_game()
