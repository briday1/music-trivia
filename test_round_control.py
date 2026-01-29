#!/usr/bin/env python3
"""
Test script for round control feature fixes
"""

import sys
sys.path.insert(0, '/home/runner/work/music-trivia/music-trivia')

from app import (
    validate_round_targets,
    generate_cards_for_targets,
    simulate_bingo_game,
    generate_unique_bingo_cards
)

def test_validate_round_targets():
    """Test round target validation"""
    print("\nTesting round target validation...")
    
    # Valid configuration
    is_valid, msg = validate_round_targets(5, 50, 10, 20, 30)
    assert is_valid, f"Valid config should pass: {msg}"
    assert msg is None
    
    # 1st place too early (need at least card_size rounds)
    is_valid, msg = validate_round_targets(5, 50, 3, 20, 30)
    assert not is_valid, "Should reject 1st place round < card_size"
    assert "1st place" in msg and "at least 5" in msg
    
    # 2nd place too early
    is_valid, msg = validate_round_targets(5, 50, 10, 5, 30)
    assert not is_valid, "Should reject 2nd place round < card_size + 1"
    assert "2nd place" in msg
    
    # 3rd place too early
    is_valid, msg = validate_round_targets(5, 50, 10, 20, 15)
    assert not is_valid, "Should reject 3rd place round < full card requirement"
    assert "3rd place" in msg
    
    # Wrong order: 2nd before 1st
    is_valid, msg = validate_round_targets(5, 50, 20, 10, 30)
    assert not is_valid, "Should reject 2nd place before 1st place"
    assert "2nd place round must be after 1st place round" in msg
    
    # Wrong order: 3rd before 2nd
    is_valid, msg = validate_round_targets(5, 50, 10, 25, 20)
    assert not is_valid, "Should reject 3rd place before 2nd place"
    assert "3rd place round must be after 2nd place round" in msg
    
    # Exceeds number of songs
    is_valid, msg = validate_round_targets(5, 30, 10, 20, 50)
    assert not is_valid, "Should reject rounds beyond song count"
    assert "exceed number of songs" in msg
    
    print("✓ Round target validation working correctly")

def test_playlist_order_preserved():
    """Test that playlist order is NOT shuffled"""
    print("\nTesting playlist order preservation...")
    
    # Create a specific song order
    songs = [f"Song_{i:03d}" for i in range(1, 51)]
    
    # Generate cards and simulate multiple times
    cards = generate_unique_bingo_cards(songs, 5, 3)
    
    # Run simulation multiple times - results should be identical
    results1 = simulate_bingo_game(cards, songs)
    results2 = simulate_bingo_game(cards, songs)
    
    # The milestone rounds should be the same every time (deterministic)
    for idx in range(len(results1)):
        r1 = results1.iloc[idx]
        r2 = results2.iloc[idx]
        
        # Check 1 line round
        assert r1['1 Line Round'] == r2['1 Line Round'] or (pd.isna(r1['1 Line Round']) and pd.isna(r2['1 Line Round'])), \
            f"Results should be deterministic. Card {idx+1} 1 Line: {r1['1 Line Round']} vs {r2['1 Line Round']}"
        
        # Check 2 lines round  
        assert r1['2 Lines Round'] == r2['2 Lines Round'] or (pd.isna(r1['2 Lines Round']) and pd.isna(r2['2 Lines Round'])), \
            f"Results should be deterministic. Card {idx+1} 2 Lines: {r1['2 Lines Round']} vs {r2['2 Lines Round']}"
    
    print("✓ Playlist order is preserved (not shuffled)")

def test_round_control_generation():
    """Test intelligent card generation with round control"""
    print("\nTesting round control card generation...")
    
    songs = [f"Song_{i:03d}" for i in range(1, 101)]
    
    # Test with more realistic target rounds based on expected win probabilities
    # With more cards, we have better chance of hitting targets
    first_round = 30
    second_round = 50
    third_round = 90
    
    cards = generate_cards_for_targets(
        songs, 
        num_cards=30,  # More cards gives better chance of meeting targets
        card_size=5,
        first_round=first_round,
        second_round=second_round,
        third_round=third_round,
        max_attempts=100
    )
    
    assert cards is not None, "Should be able to generate cards with reasonable targets"
    assert len(cards) == 30, f"Should generate 30 cards, got {len(cards)}"
    
    # Simulate and check results
    results = simulate_bingo_game(cards, songs, first_round, second_round, third_round)
    
    first_winner = results[results['Won Place'] == 1]
    second_winner = results[results['Won Place'] == 2]
    third_winner = results[results['Won Place'] == 3]
    
    assert not first_winner.empty, "Should have a 1st place winner"
    assert not second_winner.empty, "Should have a 2nd place winner"
    assert not third_winner.empty, "Should have a 3rd place winner"
    
    # Check wins are approximately at target rounds (within tolerance)
    tolerance = 5  # Reasonable tolerance for random generation
    first_actual = first_winner['1 Line Round'].values[0]
    second_actual = second_winner['2 Lines Round'].values[0]
    third_actual = third_winner['Full Card Round'].values[0]
    
    assert abs(first_actual - first_round) <= tolerance, \
        f"1st place should win near round {first_round}, won at {first_actual}"
    assert abs(second_actual - second_round) <= tolerance, \
        f"2nd place should win near round {second_round}, won at {second_actual}"
    assert abs(third_actual - third_round) <= tolerance, \
        f"3rd place should win near round {third_round}, won at {third_actual}"
    
    print(f"✓ Cards generated with targets: 1st={first_actual}, 2nd={second_actual}, 3rd={third_actual}")

def test_winning_cards_shuffled():
    """Test that winning card positions are randomized"""
    print("\nTesting winning cards are shuffled throughout deck...")
    
    songs = [f"Song_{i:03d}" for i in range(1, 101)]
    
    # Generate cards multiple times and track winning positions
    first_positions = []
    second_positions = []
    third_positions = []
    
    for _ in range(5):
        cards = generate_cards_for_targets(
            songs,
            num_cards=20,
            card_size=5,
            first_round=30,
            second_round=50,
            third_round=90,
            max_attempts=100
        )
        
        if cards is None:
            continue
            
        results = simulate_bingo_game(cards, songs, 30, 50, 90)
        
        first_winner = results[results['Won Place'] == 1]
        second_winner = results[results['Won Place'] == 2]
        third_winner = results[results['Won Place'] == 3]
        
        if not first_winner.empty:
            first_positions.append(first_winner['Card Index'].values[0])
        if not second_winner.empty:
            second_positions.append(second_winner['Card Index'].values[0])
        if not third_winner.empty:
            third_positions.append(third_winner['Card Index'].values[0])
    
    # Check that winning positions vary (not always the same cards)
    if len(first_positions) > 1:
        assert len(set(first_positions)) > 1, \
            f"1st place winners should be at different positions, got: {first_positions}"
    if len(second_positions) > 1:
        assert len(set(second_positions)) > 1, \
            f"2nd place winners should be at different positions, got: {second_positions}"
    if len(third_positions) > 1:
        assert len(set(third_positions)) > 1, \
            f"3rd place winners should be at different positions, got: {third_positions}"
    
    print(f"✓ Winning cards are shuffled: 1st places={set(first_positions)}, 2nd places={set(second_positions)}, 3rd places={set(third_positions)}")

def test_impossible_configuration():
    """Test that impossible configurations return None"""
    print("\nTesting impossible configuration handling...")
    
    songs = [f"Song_{i:03d}" for i in range(1, 26)]
    
    # Try to create targets that are impossible (very tight constraints)
    cards = generate_cards_for_targets(
        songs,
        num_cards=5,
        card_size=5,
        first_round=5,
        second_round=6,
        third_round=7,  # Impossible - need 24 rounds for full card
        max_attempts=10  # Low attempts to fail quickly
    )
    
    # Should return None when unable to meet targets
    assert cards is None, "Should return None for impossible configuration"
    
    print("✓ Impossible configurations return None correctly")

if __name__ == "__main__":
    import pandas as pd
    
    print("Running Round Control Feature Tests\n" + "=" * 50)
    
    try:
        test_validate_round_targets()
        test_playlist_order_preserved()
        test_round_control_generation()
        test_winning_cards_shuffled()
        test_impossible_configuration()
        
        print("\n" + "=" * 50)
        print("✓ All round control tests passed!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
