#!/usr/bin/env python3
"""
Test script for the Spotify Bingo app core functionality
"""

import sys
sys.path.insert(0, '/home/runner/work/music-trivia/music-trivia')

from app import (
    extract_playlist_id,
    create_bingo_card,
    generate_unique_bingo_cards,
    check_bingo_win,
    simulate_bingo_game
)

def test_extract_playlist_id():
    """Test playlist ID extraction"""
    print("Testing playlist ID extraction...")
    
    test_cases = [
        ("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M", "37i9dQZF1DXcBWIGoYBM5M"),
        ("spotify:playlist:37i9dQZF1DXcBWIGoYBM5M", "37i9dQZF1DXcBWIGoYBM5M"),
        ("37i9dQZF1DXcBWIGoYBM5M", "37i9dQZF1DXcBWIGoYBM5M")
    ]
    
    for url, expected in test_cases:
        result = extract_playlist_id(url)
        assert result == expected, f"Failed for {url}: got {result}, expected {expected}"
    
    print("✓ Playlist ID extraction working correctly")

def test_bingo_card_generation():
    """Test bingo card creation"""
    print("\nTesting bingo card generation...")
    
    # Create test songs
    songs = [f"Song {i}" for i in range(1, 51)]
    
    # Test 5x5 card
    card = create_bingo_card(songs, 5)
    assert len(card) == 5, f"Card should have 5 rows, got {len(card)}"
    assert all(len(row) == 5 for row in card), "All rows should have 5 columns"
    
    # Check all songs are from the original list
    all_card_songs = [song for row in card for song in row]
    assert all(song in songs for song in all_card_songs), "Card contains invalid songs"
    
    print("✓ Bingo card generation working correctly")

def test_unique_cards():
    """Test that multiple cards are generated"""
    print("\nTesting unique card generation...")
    
    songs = [f"Song {i}" for i in range(1, 51)]
    cards = generate_unique_bingo_cards(songs, 5, 5)
    
    assert len(cards) == 5, f"Should generate 5 cards, got {len(cards)}"
    assert all(len(card) == 5 for card in cards), "All cards should be 5x5"
    
    print("✓ Multiple card generation working correctly")

def test_bingo_win_detection():
    """Test bingo win detection"""
    print("\nTesting bingo win detection...")
    
    # Create a simple 3x3 card for easier testing
    card = [
        ["Song1", "Song2", "Song3"],
        ["Song4", "Song5", "Song6"],
        ["Song7", "Song8", "Song9"]
    ]
    
    # Test row win
    called_songs = {"Song1", "Song2", "Song3"}
    has_won, win_type = check_bingo_win(card, called_songs)
    assert has_won, "Should detect row win"
    assert "Row" in win_type, f"Should be a row win, got {win_type}"
    
    # Test column win
    called_songs = {"Song1", "Song4", "Song7"}
    has_won, win_type = check_bingo_win(card, called_songs)
    assert has_won, "Should detect column win"
    assert "Column" in win_type, f"Should be a column win, got {win_type}"
    
    # Test diagonal win (TL-BR)
    called_songs = {"Song1", "Song5", "Song9"}
    has_won, win_type = check_bingo_win(card, called_songs)
    assert has_won, "Should detect diagonal win"
    assert "Diagonal" in win_type, f"Should be a diagonal win, got {win_type}"
    
    # Test no win
    called_songs = {"Song1", "Song2"}
    has_won, win_type = check_bingo_win(card, called_songs)
    assert not has_won, "Should not detect win with insufficient songs"
    
    print("✓ Bingo win detection working correctly")

def test_game_simulation():
    """Test game simulation"""
    print("\nTesting game simulation...")
    
    songs = [f"Song {i}" for i in range(1, 26)]
    cards = generate_unique_bingo_cards(songs, 5, 3)
    
    results_df = simulate_bingo_game(cards, songs)
    
    assert len(results_df) == 5, f"Should have results for 5 cards, got {len(results_df)}"
    assert 'Card Index' in results_df.columns, "Results should have Card Index column"
    assert 'Win Round' in results_df.columns, "Results should have Win Round column"
    assert 'Place' in results_df.columns, "Results should have Place column"
    
    # Check that we have 1st, 2nd, 3rd place winners
    places = results_df['Place'].dropna().tolist()
    assert 1 in places, "Should have a 1st place winner"
    
    print("✓ Game simulation working correctly")

if __name__ == "__main__":
    print("Running Spotify Bingo App Tests\n" + "=" * 50)
    
    try:
        test_extract_playlist_id()
        test_bingo_card_generation()
        test_unique_cards()
        test_bingo_win_detection()
        test_game_simulation()
        
        print("\n" + "=" * 50)
        print("✓ All tests passed!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
