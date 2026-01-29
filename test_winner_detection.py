#!/usr/bin/env python3
"""Test winner detection fix"""
import random
import sys
sys.path.insert(0, '/home/runner/work/music-trivia/music-trivia')

from app import generate_cards_for_targets, simulate_bingo_game

random.seed(42)

songs = [f"Song_{i:03d}" for i in range(1, 64)]
cards = generate_cards_for_targets(songs, 57, 5, 10, 20, 30, free_space=True)

results = simulate_bingo_game(cards, songs, 10, 20, 30)

print("=" * 100)
print("WINNER DETECTION TEST RESULTS")
print("=" * 100)
print(results.to_string(index=False))
print()

# Verify no duplicates
for place in [1, 2, 3]:
    winners = results[results['Won Place'] == place]
    assert len(winners) <= 1, f"Multiple winners for place {place}!"
    if len(winners) == 1:
        card_idx = int(winners['Card Index'].values[0])
        print(f"✓ {['1st', '2nd', '3rd'][place-1]} place: Card #{card_idx}")

# Check 2nd place achieves at round 20 or later
second_winner = results[results['Won Place'] == 2]
if not second_winner.empty:
    round_num = int(second_winner['2 Lines Round'].values[0])
    assert round_num >= 20, f"2nd place won at round {round_num}, should be >= 20"
    print(f"✓ 2nd place achieved 2 lines at round {round_num} (>= 20)")
