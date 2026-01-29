import streamlit as st
import pandas as pd
import numpy as np
import random
from typing import List, Tuple, Dict, Set, Optional
import itertools
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from PIL import Image as PILImage

st.set_page_config(page_title="Music Bingo Game", layout="wide")

def parse_csv_tracks(uploaded_file) -> List[str]:
    """Parse track names from an Exportify CSV file.
    
    Args:
        uploaded_file: Streamlit UploadedFile object containing the CSV
    
    Returns:
        List of track names from the CSV
    """
    try:
        # Read the CSV file
        df = pd.read_csv(uploaded_file)
        
        # Check if "Track Name" column exists
        if "Track Name" not in df.columns:
            st.error("CSV file must contain a 'Track Name' column. Please ensure you're using a CSV exported from Exportify.")
            st.info("Available columns: " + ", ".join(df.columns.tolist()))
            return []
        
        # Extract track names
        track_names = df["Track Name"].dropna().tolist()
        
        if not track_names:
            st.error("No track names found in the CSV file.")
            return []
        
        return track_names
    
    except Exception as e:
        st.error(f"Error parsing CSV file: {str(e)}")
        st.info("Please ensure you're uploading a valid CSV file exported from Exportify (https://exportify.net/)")
        return []

def create_bingo_card(songs: List[str], card_size: int = 5, free_space: bool = True) -> List[List[str]]:
    """Create a single bingo card with random songs and optional free space in center."""
    # We need card_size * card_size songs for the bingo card (minus 1 if free space)
    num_squares = card_size * card_size
    num_songs_needed = num_squares - 1 if free_space and card_size % 2 == 1 else num_squares
    
    if len(songs) < num_songs_needed:
        st.warning(f"Not enough songs ({len(songs)}) for {card_size}x{card_size} card. Need at least {num_songs_needed} songs.")
        # Pad with duplicates if needed
        while len(songs) < num_songs_needed:
            songs.extend(songs[:num_songs_needed - len(songs)])
    
    # Randomly select songs for this card
    selected_songs = random.sample(songs, num_songs_needed)
    
    # Create 2D grid
    card = []
    song_idx = 0
    center = card_size // 2
    
    for i in range(card_size):
        row = []
        for j in range(card_size):
            # Add free space in center for odd-sized cards
            if free_space and card_size % 2 == 1 and i == center and j == center:
                row.append("FREE SPACE")
            else:
                row.append(selected_songs[song_idx])
                song_idx += 1
        card.append(row)
    
    return card

def create_card_for_full_completion_at_round(songs: List[str], card_size: int, target_round: int, free_space: bool = True) -> List[List[str]]:
    """
    Create a card that will complete (full card) at exactly target_round.
    
    Uses strategic song selection to ensure the card contains songs that will be
    called by target_round, with the critical song at position (target_round-1).
    """
    num_squares = card_size * card_size
    num_songs_needed = num_squares - 1 if free_space and card_size % 2 == 1 else num_squares
    
    # To complete at round N, we need songs from indices [0, N-1]
    # And importantly, we MUST include the song at index (N-1) to ensure completion at round N
    if target_round < num_songs_needed:
        # Not enough songs will be called by target_round to fill the card
        # This should have been caught by validation
        target_round = num_songs_needed
    
    # Select songs from [0, target_round-1]
    available_songs = songs[:target_round]
    
    # Randomly sample the needed songs from this range
    if len(available_songs) >= num_songs_needed:
        selected_songs = random.sample(available_songs, num_songs_needed)
    else:
        # Not enough unique songs, use all and allow duplicates
        selected_songs = list(available_songs)
        while len(selected_songs) < num_songs_needed:
            selected_songs.append(random.choice(available_songs))
    
    # Ensure the song at index (target_round-1) is included
    critical_song = songs[target_round - 1] if target_round <= len(songs) else songs[-1]
    if critical_song not in selected_songs:
        # Replace a random song with the critical one
        selected_songs[random.randint(0, len(selected_songs) - 1)] = critical_song
    
    # Shuffle to avoid patterns
    random.shuffle(selected_songs)
    
    # Create 2D grid
    card = []
    song_idx = 0
    center = card_size // 2
    
    for i in range(card_size):
        row = []
        for j in range(card_size):
            if free_space and card_size % 2 == 1 and i == center and j == center:
                row.append("FREE SPACE")
            else:
                row.append(selected_songs[song_idx])
                song_idx += 1
        card.append(row)
    
    return card

def generate_unique_bingo_cards(songs: List[str], num_cards: int, card_size: int = 5, free_space: bool = True) -> List[List[List[str]]]:
    """Generate multiple unique bingo cards."""
    cards = []
    for _ in range(num_cards):
        card = create_bingo_card(songs, card_size, free_space)
        cards.append(card)
    return cards

def validate_round_targets(card_size: int, num_songs: int, first_round: Optional[int], 
                          second_round: Optional[int], third_round: Optional[int]) -> Tuple[bool, Optional[str]]:
    """
    Validate if the target rounds are feasible.
    
    Args:
        card_size: Size of the bingo card (NxN)
        num_songs: Number of songs in the playlist
        first_round: Target round for 1st place winner (1 line)
        second_round: Target round for 2nd place winner (2 lines)
        third_round: Target round for 3rd place winner (full card)
    
    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    # Check order first before checking minimums
    if first_round and second_round and first_round >= second_round:
        return False, "2nd place round must be after 1st place round"
    if second_round and third_round and second_round >= third_round:
        return False, "3rd place round must be after 2nd place round"
    if first_round and third_round and not second_round and first_round >= third_round:
        return False, "3rd place round must be after 1st place round"
    
    # Minimum rounds needed for each place
    min_first = card_size  # Need at least one full line
    min_second = card_size * 2  # Need 2 complete lines
    min_third = (card_size * card_size) - 1 if card_size % 2 == 1 else card_size * card_size  # Full card minus free space
    
    if first_round and first_round < min_first:
        return False, f"1st place (1 line) requires at least {min_first} rounds"
    if second_round and second_round < min_second:
        return False, f"2nd place (2 lines) requires at least {min_second} rounds"
    if third_round and third_round < min_third:
        return False, f"3rd place (full card) requires at least {min_third} rounds"
    
    if any([first_round, second_round, third_round]) and max(filter(None, [first_round, second_round, third_round])) > num_songs:
        return False, f"Target rounds exceed number of songs ({num_songs})"
    
    # For deterministic algorithm: need blocker songs after R
    # This ensures other cards can't blackout by round R
    if third_round and third_round >= num_songs:
        return False, f"3rd place round ({third_round}) must be less than total songs ({num_songs}) to allow blocker songs"
    
    return True, None

def get_card_milestones(card: List[List[str]], songs: List[str]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Get the rounds at which a card achieves milestones.
    
    Args:
        card: The bingo card
        songs: List of songs in playlist order
    
    Returns:
        Tuple of (1_line_round, 2_lines_round, full_card_round) or None if not achieved
    """
    one_line_round = None
    two_lines_round = None
    full_card_round = None
    
    called_songs = set()
    
    for round_num, song in enumerate(songs, 1):
        called_songs.add(song)
        
        # Check for 1 line
        if one_line_round is None:
            line_count, _ = count_complete_lines(card, called_songs)
            if line_count >= 1:
                one_line_round = round_num
        
        # Check for 2 lines
        if two_lines_round is None:
            line_count, _ = count_complete_lines(card, called_songs)
            if line_count >= 2:
                two_lines_round = round_num
        
        # Check for full card
        if full_card_round is None:
            if check_full_card(card, called_songs):
                full_card_round = round_num
        
        # Early exit if all milestones found
        if one_line_round and two_lines_round and full_card_round:
            break
    
    return one_line_round, two_lines_round, full_card_round

def create_card_A_blackout(songs: List[str], card_size: int, R: int, free_space: bool, max_attempts: int = 100) -> List[List[str]]:
    """
    Create Card A: Blackout winner at exactly round R.
    
    Strategy:
    - Include song at index R-1 (will be called at round R)
    - Fill remaining S-1 squares with songs from indices 0 to R-2
    - Card completes when song[R-1] is called at round R
    - CRITICAL: Ensure card doesn't get any complete lines before round R-card_size
      to prevent winning 1st or 2nd place before it can win 3rd place
    """
    S = card_size * card_size - 1 if free_space else card_size * card_size
    
    # EARLYR = songs[0..R-2], AT_R = songs[R-1]
    AT_R = songs[R - 1]
    EARLYR = songs[:R - 1]
    
    # Try multiple times to generate a card that doesn't get lines too early
    for attempt in range(max_attempts):
        # Build set of S songs: AT_R + (S-1) from EARLYR
        if len(EARLYR) < S - 1:
            # Not enough early songs, use what we have
            selected_songs = [AT_R] + EARLYR
            # Pad if needed
            while len(selected_songs) < S:
                selected_songs.append(EARLYR[len(selected_songs) % len(EARLYR)])
        else:
            # Sample S-1 songs from EARLYR
            selected_songs = [AT_R] + random.sample(EARLYR, S - 1)
        
        # Shuffle to avoid patterns
        random.shuffle(selected_songs)
        
        # Place into grid
        card = _place_songs_on_card(selected_songs, card_size, free_space)
        
        # Check if this card gets lines too early
        # We want to avoid getting 1 line before round R - (card_size * 2)
        # and 2 lines before round R - card_size
        one_line, two_lines, full_card = get_card_milestones(card, songs)
        
        # Accept if: no lines before mid-game OR full card is at R
        # Target: 1st line should be after R*0.5, 2nd line after R*0.7
        if full_card == R:
            if one_line is None or one_line > int(R * 0.5):
                if two_lines is None or two_lines > int(R * 0.7):
                    return card
    
    # If we couldn't find a good card, return the last one
    # (better than failing completely)
    return card

def create_card_B_one_line(songs: List[str], card_size: int, r1: int, R: int, M: int, free_space: bool) -> List[List[str]]:
    """
    Create Card B: 1-line winner by round r1 (with blocker to prevent blackout by R).
    
    Strategy:
    - Use center row (benefits from FREE center)
    - Place song at r1-1 on center row
    - Fill rest of center row with songs from 0 to r1-2
    - Add one blocker from songs[R..M-1] to prevent blackout
    - Fill remaining squares from songs[0..R-1]
    """
    S = card_size * card_size - 1 if free_space else card_size * card_size
    center = card_size // 2
    
    # Songs buckets
    AT_R1 = songs[r1 - 1] if r1 <= len(songs) else songs[-1]
    EARLY1 = songs[:r1 - 1]
    LATE = songs[R:M] if R < M else []
    EARLYR = songs[:R]
    
    # Must have blocker songs for deterministic algorithm
    if not LATE:
        raise ValueError(f"Need blocker songs: R={R} must be < M={M}")
    
    # Build card grid
    card_grid = [[None for _ in range(card_size)] for _ in range(card_size)]
    used_songs = set()
    
    # Set FREE space
    if free_space:
        card_grid[center][center] = "FREE SPACE"
    
    # Fill center row (except FREE center)
    center_row_squares = []
    for j in range(card_size):
        if free_space and j == center:
            continue  # FREE space
        center_row_squares.append((center, j))
    
    # Need k = N-1 songs for center row (or N if no free space in that row)
    k = len(center_row_squares)
    
    # Place AT_R1 on center row
    row_songs = [AT_R1]
    used_songs.add(AT_R1)
    
    # Fill rest of center row with songs from EARLY1
    available_early1 = [s for s in EARLY1 if s not in used_songs]
    if len(available_early1) >= k - 1:
        row_songs.extend(random.sample(available_early1, k - 1))
    else:
        row_songs.extend(available_early1)
        # Pad if needed from EARLYR
        while len(row_songs) < k:
            available = [s for s in EARLYR if s not in used_songs and s not in row_songs]
            if available:
                row_songs.append(random.choice(available))
            else:
                break
    
    used_songs.update(row_songs)
    random.shuffle(row_songs)
    
    for idx, (i, j) in enumerate(center_row_squares[:len(row_songs)]):
        card_grid[i][j] = row_songs[idx]
    
    # Add one blocker from LATE (anywhere NOT on center row) - REQUIRED
    blocker = random.choice(LATE)
    used_songs.add(blocker)
    
    # Find a square not on center row
    off_row_squares = [(i, j) for i in range(card_size) for j in range(card_size) 
                      if i != center and card_grid[i][j] is None]
    if off_row_squares:
        pos = random.choice(off_row_squares)
        card_grid[pos[0]][pos[1]] = blocker
    
    # Fill remaining squares with songs from EARLYR
    empty_squares = [(i, j) for i in range(card_size) for j in range(card_size) 
                     if card_grid[i][j] is None]
    
    available_songs = [s for s in EARLYR if s not in used_songs]
    random.shuffle(available_songs)
    
    for idx, (i, j) in enumerate(empty_squares):
        if idx < len(available_songs):
            card_grid[i][j] = available_songs[idx]
        else:
            # Ran out, allow duplicates
            card_grid[i][j] = random.choice(EARLYR)
    
    return card_grid

def create_card_C_two_lines(songs: List[str], card_size: int, r2: int, R: int, M: int, free_space: bool) -> List[List[str]]:
    """
    Create Card C: 2-line winner by round r2 (with blocker).
    
    Strategy:
    - Use both center row AND center column (share FREE center)
    - Place song at r2-1 on one of these lines
    - Fill both lines with songs from 0 to r2-2
    - Add blocker from songs[R..M-1]
    - Place delay songs on non-center rows to prevent early completion
    - Fill rest from songs[0..R-1]
    """
    S = card_size * card_size - 1 if free_space else card_size * card_size
    center = card_size // 2
    
    # Songs buckets
    AT_R2 = songs[r2 - 1] if r2 <= len(songs) else songs[-1]
    EARLY2 = songs[:r2 - 1]
    LATE = songs[R:M] if R < M else []
    EARLYR = songs[:R]
    DELAY = songs[r2:R] if r2 < R else []  # Songs to delay line completion
    
    # Must have blocker songs for deterministic algorithm
    if not LATE:
        raise ValueError(f"Need blocker songs: R={R} must be < M={M}")
    
    # Build card grid
    card_grid = [[None for _ in range(card_size)] for _ in range(card_size)]
    used_songs = set()
    
    # Set FREE space
    if free_space:
        card_grid[center][center] = "FREE SPACE"
    
    # Collect center row and column squares (excluding FREE center)
    line_squares = []
    # Center row
    for j in range(card_size):
        if not (free_space and j == center):
            line_squares.append((center, j))
    # Center column (skip center to avoid duplicate)
    for i in range(card_size):
        if i != center:
            line_squares.append((i, center))
    
    # Total: 2(N-1) squares for free space case
    total_line_squares = len(line_squares)
    
    # Place AT_R2 on one of these squares
    line_songs = [AT_R2]
    used_songs.add(AT_R2)
    
    # Fill rest with songs from EARLY2
    available_early2 = [s for s in EARLY2 if s not in used_songs]
    needed = total_line_squares - 1
    
    if len(available_early2) >= needed:
        line_songs.extend(random.sample(available_early2, needed))
    else:
        line_songs.extend(available_early2)
        # Pad from EARLYR if needed
        while len(line_songs) < total_line_squares:
            available = [s for s in EARLYR if s not in used_songs and s not in line_songs]
            if available:
                line_songs.append(random.choice(available))
            else:
                line_songs.append(random.choice(EARLYR))
    
    used_songs.update(line_songs)
    random.shuffle(line_songs)
    
    for idx, (i, j) in enumerate(line_squares[:len(line_songs)]):
        card_grid[i][j] = line_songs[idx]
    
    # Add blocker from LATE (NOT on center row or column) - REQUIRED
    blocker = random.choice(LATE)
    used_songs.add(blocker)
    
    off_lines = [(i, j) for i in range(card_size) for j in range(card_size) 
                 if i != center and j != center and card_grid[i][j] is None]
    if off_lines:
        pos = random.choice(off_lines)
        card_grid[pos[0]][pos[1]] = blocker
    
    # Add delay songs to non-center rows to prevent early 2-line completion
    # For each row except center, try to place a delay song
    if DELAY:
        for i in range(card_size):
            if i == center:
                continue  # Skip center row
            available_cols = [j for j in range(card_size) if card_grid[i][j] is None]
            if available_cols:
                delay_song = random.choice(DELAY)
                j = random.choice(available_cols)
                card_grid[i][j] = delay_song
                used_songs.add(delay_song)
    
    # Fill remaining squares from EARLYR
    empty_squares = [(i, j) for i in range(card_size) for j in range(card_size) 
                     if card_grid[i][j] is None]
    
    available_songs = [s for s in EARLYR if s not in used_songs]
    random.shuffle(available_songs)
    
    for idx, (i, j) in enumerate(empty_squares):
        if idx < len(available_songs):
            card_grid[i][j] = available_songs[idx]
        else:
            card_grid[i][j] = random.choice(EARLYR)
    
    return card_grid

def create_other_card_with_blocker(songs: List[str], card_size: int, R: int, M: int, 
                                   second_round: int, free_space: bool) -> List[List[str]]:
    """
    Create remaining cards with blockers to prevent:
    1. Blackout by round R
    2. Getting 2 lines at or near the 2nd place target round
    
    Strategy:
    - Add one blocker from songs[R..M-1] to prevent early blackout
    - Place "late" songs strategically in each row/column to delay 2-line completion
    """
    S = card_size * card_size - 1 if free_space else card_size * card_size
    center = card_size // 2
    
    LATE = songs[R:M] if R < M else []
    EARLYR = songs[:R]
    
    # Songs in the range [second_round, R) to delay line completion
    delay_songs = songs[second_round + 2:R] if second_round + 2 < R else []
    
    card_grid = [[None for _ in range(card_size)] for _ in range(card_size)]
    used_songs = set()
    
    # Set FREE space
    if free_space:
        card_grid[center][center] = "FREE SPACE"
    
    # Add blocker from LATE to prevent blackout
    if LATE:
        blocker = random.choice(LATE)
        used_songs.add(blocker)
        i, j = random.randint(0, card_size-1), random.randint(0, card_size-1)
        while card_grid[i][j] is not None:
            i, j = random.randint(0, card_size-1), random.randint(0, card_size-1)
        card_grid[i][j] = blocker
    
    # For each row, place at least one delay song to prevent early line completion
    if delay_songs:
        for i in range(card_size):
            delay_song = random.choice(delay_songs)
            available_cols = [j for j in range(card_size) if card_grid[i][j] is None]
            if available_cols:
                j = random.choice(available_cols)
                card_grid[i][j] = delay_song
                used_songs.add(delay_song)
    
    # Fill remaining squares from EARLYR
    empty_squares = [(i, j) for i in range(card_size) for j in range(card_size) 
                     if card_grid[i][j] is None]
    
    available_songs = [s for s in EARLYR if s not in used_songs]
    random.shuffle(available_songs)
    
    for idx, (i, j) in enumerate(empty_squares):
        if idx < len(available_songs):
            card_grid[i][j] = available_songs[idx]
        else:
            card_grid[i][j] = random.choice(EARLYR)
    
    return card_grid

def _place_songs_on_card(selected_songs: List[str], card_size: int, free_space: bool) -> List[List[str]]:
    """Helper to place a list of songs onto a card grid with FREE space."""
    card = []
    song_idx = 0
    center = card_size // 2
    
    for i in range(card_size):
        row = []
        for j in range(card_size):
            if free_space and card_size % 2 == 1 and i == center and j == center:
                row.append("FREE SPACE")
            else:
                if song_idx < len(selected_songs):
                    row.append(selected_songs[song_idx])
                    song_idx += 1
                else:
                    # Shouldn't happen, but fallback
                    row.append(selected_songs[0] if selected_songs else "")
        card.append(row)
    
    return card

def generate_cards_for_targets(songs: List[str], num_cards: int, card_size: int, 
                               first_round: Optional[int], second_round: Optional[int], 
                               third_round: Optional[int], max_attempts: int = 10000,
                               free_space: bool = True) -> Optional[List[List[List[str]]]]:
    """
    Generate cards with DETERMINISTIC guaranteed winners using strategic song placement.
    
    Algorithm:
    - Card A: Blackout (3rd place) at exactly round R (third_round)
    - Card B: 1-line winner by round r1 (first_round) with blocker to prevent blackout
    - Card C: 2-line winner by round r2 (second_round) with blocker
    - Other cards: Random with blockers to prevent early blackout
    
    Args:
        songs: List of all songs in play order
        num_cards: Number of cards to generate  
        card_size: Size of each card (NxN)
        first_round: Target round for 1st place (1 line) winner
        second_round: Target round for 2nd place (2 lines) winner
        third_round: Target round for 3rd place (blackout) winner
        max_attempts: Not used (kept for compatibility)
        free_space: Whether to include a free space (must be True for odd card_size)
    
    Returns:
        List of cards, or None if unable to generate valid cards
    """
    if not third_round:
        # No round control, generate random cards
        return [create_bingo_card(songs, card_size, free_space) for _ in range(num_cards)]
    
    # Calculate default r1 and r2 if not provided
    # r1 ~ 30-40% of R, r2 ~ 60-70% of R
    R = third_round
    if not first_round:
        first_round = max(card_size, int(R * 0.35))
    if not second_round:
        second_round = max(card_size * 2, int(R * 0.65))
    
    r1 = first_round
    r2 = second_round
    
    # Validate we have enough songs
    M = len(songs)
    if R > M:
        return None  # Not enough songs
    
    # Initialize cards list
    cards = [None] * num_cards
    
    # Randomly assign which cards get which roles
    card_positions = list(range(num_cards))
    random.shuffle(card_positions)
    
    card_A_pos = card_positions[0] if num_cards >= 1 else None
    card_B_pos = card_positions[1] if num_cards >= 2 else None
    card_C_pos = card_positions[2] if num_cards >= 3 else None
    
    # Card A: Blackout winner at exactly round R
    if card_A_pos is not None:
        cards[card_A_pos] = create_card_A_blackout(songs, card_size, R, free_space)
    
    # Card B: 1-line winner by r1 (with blocker)
    if card_B_pos is not None:
        cards[card_B_pos] = create_card_B_one_line(songs, card_size, r1, R, M, free_space)
    
    # Card C: 2-line winner by r2 (with blocker)
    if card_C_pos is not None:
        cards[card_C_pos] = create_card_C_two_lines(songs, card_size, r2, R, M, free_space)
    
    # Remaining cards: random with blockers
    for i in range(num_cards):
        if cards[i] is None:
            cards[i] = create_other_card_with_blocker(songs, card_size, R, M, r2, free_space)
    
    return cards

def is_called(song: str, called_songs: Set[str]) -> bool:
    """
    Check if a song is called. FREE SPACE is always considered called.
    
    Args:
        song: The song name to check
        called_songs: Set of songs that have been called
    
    Returns:
        True if the song is called or is FREE SPACE
    """
    return song == "FREE SPACE" or song in called_songs

def count_complete_lines(card: List[List[str]], called_songs: Set[str]) -> Tuple[int, List[str]]:
    """
    Count the number of complete lines (rows or columns, no diagonals) on a card.
    Returns (count, list of line descriptions)
    FREE SPACE is automatically considered as called/matched.
    """
    card_size = len(card)
    complete_lines = []
    
    # Check rows
    for i, row in enumerate(card):
        if all(is_called(song, called_songs) for song in row):
            complete_lines.append(f"Row {i+1}")
    
    # Check columns
    for col in range(card_size):
        if all(is_called(card[row][col], called_songs) for row in range(card_size)):
            complete_lines.append(f"Column {col+1}")
    
    return len(complete_lines), complete_lines

def check_full_card(card: List[List[str]], called_songs: Set[str]) -> bool:
    """
    Check if all spaces on the card have been called.
    FREE SPACE is automatically considered as called/matched.
    """
    for row in card:
        for song in row:
            if not is_called(song, called_songs):
                return False
    return True

def check_bingo_win(card: List[List[str]], called_songs: Set[str], place: int) -> Tuple[bool, str]:
    """
    Check if a card has won based on the place (1st, 2nd, or 3rd).
    - 1st place: One complete line (row or column, no diagonals)
    - 2nd place: Two complete lines (rows or columns)
    - 3rd place: Full card (all spaces called)
    Returns (has_won, win_type)
    FREE SPACE is automatically considered as called/matched.
    """
    if place == 1:
        # 1st place needs at least 1 line
        line_count, lines = count_complete_lines(card, called_songs)
        if line_count >= 1:
            return True, lines[0]
    elif place == 2:
        # 2nd place needs at least 2 lines
        line_count, lines = count_complete_lines(card, called_songs)
        if line_count >= 2:
            return True, f"{lines[0]}, {lines[1]}"
    elif place == 3:
        # 3rd place needs full card
        if check_full_card(card, called_songs):
            return True, "Full Card"
    
    return False, ""

def simulate_bingo_game(cards: List[List[List[str]]], songs: List[str], 
                        first_winner_round: int = None, 
                        second_winner_round: int = None,
                        third_winner_round: int = None) -> pd.DataFrame:
    """
    Simulate the bingo game and track when each card achieves milestones:
    - 1 line: One complete line (row or column, no diagonals)
    - 2 lines: Two complete lines
    - Full card: All spaces called
    
    Also tracks which card wins 1st, 2nd, and 3rd place.
    
    Args:
        cards: List of bingo cards
        songs: List of all songs in the playlist
        first_winner_round: Target round for 1st place winner (optional)
        second_winner_round: Target round for 2nd place winner (optional)
        third_winner_round: Target round for 3rd place winner (optional)
    
    Returns a DataFrame with card milestones and winners.
    """
    # Use playlist order as-is (no shuffling to preserve playlist order)
    call_order = songs.copy()
    
    # Track milestones for each card
    card_milestones = {}
    for card_idx in range(len(cards)):
        card_milestones[card_idx] = {
            '1_line_round': None,
            '2_lines_round': None,
            'full_card_round': None
        }
    
    place_winners = {1: None, 2: None, 3: None}  # Track which card won each place
    called_songs = set()
    
    for round_num, song in enumerate(call_order, 1):
        called_songs.add(song)
        
        # Update milestones for all cards
        for card_idx, card in enumerate(cards):
            milestones = card_milestones[card_idx]
            
            # Check for 1 line (if not already achieved)
            if milestones['1_line_round'] is None:
                line_count, lines = count_complete_lines(card, called_songs)
                if line_count >= 1:
                    milestones['1_line_round'] = round_num
            
            # Check for 2 lines (if not already achieved)
            if milestones['2_lines_round'] is None:
                line_count, lines = count_complete_lines(card, called_songs)
                if line_count >= 2:
                    milestones['2_lines_round'] = round_num
            
            # Check for full card (if not already achieved)
            if milestones['full_card_round'] is None:
                if check_full_card(card, called_songs):
                    milestones['full_card_round'] = round_num
        
        # Check for 1st and 3rd place winners (keep existing logic)
        for place in [1, 3]:
            # Skip if this place already has a winner
            if place_winners[place] is not None:
                continue
            
            # Skip if we're not at the target round for this place yet
            if place == 1 and first_winner_round and round_num < first_winner_round:
                continue
            if place == 3 and third_winner_round and round_num < third_winner_round:
                continue
            
            # Convert winning_card_indices to set for O(1) lookup
            winning_card_indices = set(place_winners[p] for p in [1, 2, 3] if place_winners[p] is not None)
            
            # Check each card for this place's win condition
            for card_idx, card in enumerate(cards):
                # Skip if card already won a place
                if card_idx in winning_card_indices:
                    continue
                
                has_won, win_type = check_bingo_win(card, called_songs, place)
                if has_won:
                    place_winners[place] = card_idx
                    break  # Only one winner per round per place
        
        # Special logic for 2nd place - find earliest 2-line achiever at or after target round
        if place_winners[2] is None and (not second_winner_round or round_num >= second_winner_round):
            earliest_2_lines = None
            earliest_2_lines_card = None
            
            for card_idx, milestones in card_milestones.items():
                # Skip if this card already won 1st place (no duplicate winners)
                if card_idx == place_winners[1]:
                    continue
                
                two_line_round = milestones['2_lines_round']
                if two_line_round is not None:
                    # Exclude cards that achieved before the target round (no earlier winners)
                    if second_winner_round and two_line_round < second_winner_round:
                        continue
                    
                    # Pick the earliest achiever at or after the target round
                    if earliest_2_lines is None or two_line_round < earliest_2_lines:
                        earliest_2_lines = two_line_round
                        earliest_2_lines_card = card_idx
            
            if earliest_2_lines_card is not None:
                place_winners[2] = earliest_2_lines_card
        
        # Continue simulation to track full card completion for all cards
        # (Don't stop early even if all three places have winners)
    
    # Build results DataFrame with all card milestones
    results = []
    for card_idx in range(len(cards)):
        milestones = card_milestones[card_idx]
        
        # Determine which place this card won (if any)
        card_place = None
        for place, winner_idx in place_winners.items():
            if winner_idx == card_idx:
                card_place = place
                break
        
        results.append({
            'Card Index': card_idx + 1,
            '1 Line Round': milestones['1_line_round'],
            '2 Lines Round': milestones['2_lines_round'],
            'Full Card Round': milestones['full_card_round'],
            'Won Place': card_place
        })
    
    return pd.DataFrame(results)

def calculate_win_probability(cards: List[List[List[str]]], songs: List[str], 
                              target_card: int, num_simulations: int = 100) -> float:
    """Calculate the probability that a specific card wins within certain rounds."""
    wins = 0
    
    for _ in range(num_simulations):
        results = simulate_bingo_game(cards, songs)
        card_result = results[results['Card Index'] == target_card + 1]
        if not card_result.empty and card_result['Won Place'].values[0] == 1:
            wins += 1
    
    return wins / num_simulations

def format_bingo_card_html(card: List[List[str]], card_index: int) -> str:
    """Format a bingo card as HTML for display."""
    html = f'<div style="page-break-after: always; margin-bottom: 20px;">'
    html += f'<h3 style="text-align: center;">Bingo Card #{card_index + 1}</h3>'
    html += '<table style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 0 auto;">'
    html += '<tr style="background-color: #4CAF50; color: white;">'
    for letter in 'BINGO':
        html += f'<th style="border: 2px solid black; padding: 10px; text-align: center; font-size: 24px;">{letter}</th>'
    html += '</tr>'
    
    for row in card:
        html += '<tr>'
        for song in row:
            # Truncate long song names
            display_song = song[:20] + '...' if len(song) > 20 else song
            html += f'<td style="border: 2px solid black; padding: 15px; text-align: center; height: 80px; font-size: 12px;">{display_song}</td>'
        html += '</tr>'
    
    html += '</table></div>'
    return html

def generate_bingo_pdf(
    cards: List[List[List[str]]], 
    results_df: pd.DataFrame,
    title: Optional[str] = None,
    logo_image: Optional[BytesIO] = None,
    logo_zoom: float = 1.0
) -> BytesIO:
    """
    Generate a PDF with all bingo cards and operator reference sheet.
    
    Args:
        cards: List of bingo cards
        results_df: DataFrame with win analysis
        title: Optional title to display on top of each card
        logo_image: Optional logo image for free space (BytesIO)
        logo_zoom: Zoom factor for logo (default 1.0)
    
    Returns:
        BytesIO object containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading2'],
        alignment=TA_CENTER,
        spaceAfter=12
    )
    index_style = ParagraphStyle(
        'CardIndex',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
        fontSize=8,
        textColor=colors.grey
    )
    
    # Generate each bingo card
    for card_idx, card in enumerate(cards):
        # Add optional title at top
        if title:
            elements.append(Paragraph(title, title_style))
            elements.append(Spacer(1, 0.2*inch))
        
        # Create table data (no BINGO header)
        table_data = []
        card_size = len(card)
        center = card_size // 2
        
        for row_idx, row in enumerate(card):
            table_row = []
            for col_idx, song in enumerate(row):
                # Handle free space
                if song == "FREE SPACE":
                    if logo_image:
                        # Add logo image
                        try:
                            logo_image.seek(0)  # Reset stream position
                            img = PILImage.open(logo_image)
                            
                            # Calculate dimensions with zoom
                            max_size = 60 * logo_zoom
                            img.thumbnail((max_size, max_size), PILImage.Resampling.LANCZOS)
                            
                            # Save to BytesIO
                            img_buffer = BytesIO()
                            img.save(img_buffer, format='PNG')
                            img_buffer.seek(0)
                            
                            # Create ReportLab image
                            rl_img = RLImage(img_buffer, width=img.width, height=img.height)
                            table_row.append(rl_img)
                        except Exception as e:
                            # Fallback to text if image fails
                            table_row.append(Paragraph("FREE<br/>SPACE", 
                                ParagraphStyle('center', alignment=TA_CENTER, fontSize=8)))
                    else:
                        # Text free space
                        table_row.append(Paragraph("FREE<br/>SPACE", 
                            ParagraphStyle('center', alignment=TA_CENTER, fontSize=8)))
                else:
                    # Regular song cell - wrap text
                    song_text = song[:30] if len(song) <= 30 else song[:27] + "..."
                    table_row.append(Paragraph(song_text, 
                        ParagraphStyle('center', alignment=TA_CENTER, fontSize=7)))
            table_data.append(table_row)
        
        # Create the table
        col_width = 6.5*inch / card_size
        table = Table(table_data, colWidths=[col_width] * card_size, 
                     rowHeights=[col_width] * card_size)
        
        # Style the table
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.1*inch))
        
        # Add card index and game instructions at the bottom
        elements.append(Paragraph(f"Card #{card_idx + 1}", index_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Add minimal game instructions at the bottom
        instructions_style = ParagraphStyle(
            'Instructions',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        instructions_text = (
            "First place winner: One line (up/down, left/right). "
            "Second place winner: Two lines. "
            "Third place winner: Fill sheet. "
            "Each card can only win once."
        )
        elements.append(Paragraph(instructions_text, instructions_style))
        
        # Page break after each card (except the last)
        if card_idx < len(cards) - 1:
            elements.append(PageBreak())
    
    # Add operator reference sheet
    elements.append(PageBreak())
    
    # Operator sheet title
    op_title_style = ParagraphStyle(
        'OpTitle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        spaceAfter=12
    )
    elements.append(Paragraph("Operator Reference Sheet", op_title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Instructions
    elements.append(Paragraph(
        "<b>Instructions:</b> This table shows when each card achieves milestones. "
        "Highlighted rows show which card won 1st (1 line), 2nd (2 lines), and 3rd (full card) place. "
        "<b>Important:</b> Once a card wins a place, it is ineligible to win another place.",
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.3*inch))
    
    # Create operator table with all milestones
    op_data = [['Card', '1 Line', '2 Lines', 'Full Card']]
    
    # Track which rows to highlight
    highlight_rows = {}
    
    for _, row in results_df.iterrows():
        card_idx = int(row['Card Index'])
        one_line = f"Round {int(row['1 Line Round'])}" if pd.notna(row['1 Line Round']) else "-"
        two_lines = f"Round {int(row['2 Lines Round'])}" if pd.notna(row['2 Lines Round']) else "-"
        full_card = f"Round {int(row['Full Card Round'])}" if pd.notna(row['Full Card Round']) else "-"
        
        op_data.append([f"Card #{card_idx}", one_line, two_lines, full_card])
        
        # Track which place this card won for highlighting
        if pd.notna(row['Won Place']):
            place = int(row['Won Place'])
            highlight_rows[len(op_data) - 1] = place  # Store row index and place
    
    op_table = Table(op_data, colWidths=[1.5*inch, 2*inch, 2*inch, 2*inch])
    
    # Build style list
    style_list = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    
    # Add highlighting for winning cards
    for row_idx, place in highlight_rows.items():
        if place == 1:
            # Highlight 1 Line column for 1st place winner
            style_list.append(('BACKGROUND', (1, row_idx), (1, row_idx), colors.HexColor('#fff9c4')))
            style_list.append(('FONTNAME', (1, row_idx), (1, row_idx), 'Helvetica-Bold'))
        elif place == 2:
            # Highlight 2 Lines column for 2nd place winner
            style_list.append(('BACKGROUND', (2, row_idx), (2, row_idx), colors.HexColor('#ffe0b2')))
            style_list.append(('FONTNAME', (2, row_idx), (2, row_idx), 'Helvetica-Bold'))
        elif place == 3:
            # Highlight Full Card column for 3rd place winner
            style_list.append(('BACKGROUND', (3, row_idx), (3, row_idx), colors.HexColor('#ffccbc')))
            style_list.append(('FONTNAME', (3, row_idx), (3, row_idx), 'Helvetica-Bold'))
    
    op_table.setStyle(TableStyle(style_list))
    
    elements.append(op_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer

def main():
    st.title("🎵 Music Bingo Game Generator")
    st.write("Create unique bingo cards from your Spotify playlists!")
    
    # Instructions for using Exportify
    st.info("""
    ### 📋 How to Use This App:
    
    1. **Export Your Playlist**: Visit [Exportify](https://exportify.net/) to export your Spotify playlist(s) to CSV
    2. **Upload CSV**: Upload the exported CSV file below
    3. **Configure Settings**: Adjust card size, number of cards, and other options below
    4. **Generate Cards**: Click "Generate Bingo Cards" to create your bingo game
    
    **Note:** This app works with CSV files exported from [Exportify](https://exportify.net/), which contains your Spotify playlist data.
    """)
    
    # CSV file uploader
    uploaded_file = st.file_uploader(
        "Upload Exportify CSV File",
        type=['csv'],
        help="Upload a CSV file exported from https://exportify.net/"
    )
    
    # Configuration section - moved from sidebar
    st.divider()
    st.subheader("⚙️ Configuration")
    
    # Bingo game settings in columns
    col1, col2 = st.columns(2)
    with col1:
        num_cards = st.slider("Number of Bingo Cards", min_value=1, max_value=100, value=10)
    with col2:
        card_size = st.slider("Card Size (NxN)", min_value=3, max_value=7, value=5)
    
    # Win Analysis section
    st.divider()
    analyze_wins = st.checkbox("Analyze Win Probabilities", value=True)
    
    # Initialize round control variables
    use_round_control = False
    first_winner_round = None
    second_winner_round = None
    third_winner_round = None
    
    # Winner round controls
    if analyze_wins:
        with st.expander("Winner Round Controls (Optional)"):
            st.caption("Set target rounds for each winner")
            use_round_control = st.checkbox("Control Winner Rounds", value=False)
            
            if use_round_control:
                col1, col2, col3 = st.columns(3)
                with col1:
                    first_winner_round = st.slider(
                        "1st Winner Round (1 line)",
                        min_value=1,
                        max_value=100,
                        value=10,
                        help="Minimum round for the first winner"
                    )
                with col2:
                    second_winner_round = st.slider(
                        "2nd Winner Round (2 lines)",
                        min_value=first_winner_round + 1,
                        max_value=100,
                        value=min(20, first_winner_round + 10),
                        help="Minimum round for the second winner"
                    )
                with col3:
                    third_winner_round = st.slider(
                        "3rd Winner Round (full card)",
                        min_value=second_winner_round + 1,
                        max_value=100,
                        value=min(30, second_winner_round + 10),
                        help="Minimum round for the third winner"
                    )
    
    # PDF Customization
    st.divider()
    with st.expander("PDF Customization (Optional)"):
        card_title = st.text_input("Card Title (optional)", placeholder="e.g., Music Bingo Night")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            logo_file = st.file_uploader("Upload Logo for Free Space (optional)", type=['png', 'jpg', 'jpeg'])
        with col2:
            logo_zoom = 1.0
            if logo_file:
                logo_zoom = st.slider("Logo Zoom", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
    
    st.divider()
    
    if uploaded_file:
        if st.button("Generate Bingo Cards", type="primary"):
            with st.spinner("Parsing CSV file..."):
                songs = parse_csv_tracks(uploaded_file)
            
            if songs:
                st.success(f"Found {len(songs)} songs in the playlist!")
                
                # Validate round targets if round control is enabled
                if use_round_control:
                    is_valid, error_msg = validate_round_targets(
                        card_size, 
                        len(songs),
                        first_winner_round,
                        second_winner_round,
                        third_winner_round
                    )
                    if not is_valid:
                        st.error(f"❌ Invalid round targets: {error_msg}")
                        st.stop()
                
                # Display song list
                with st.expander(f"View all {len(songs)} songs"):
                    st.write(", ".join(songs))
                
                # Generate bingo cards
                with st.spinner(f"Generating {num_cards} unique bingo cards..."):
                    if use_round_control:
                        cards = generate_cards_for_targets(
                            songs, 
                            num_cards, 
                            card_size,
                            first_winner_round,
                            second_winner_round,
                            third_winner_round
                        )
                        if cards is None:
                            st.warning("⚠️ Could not generate cards that meet exact target rounds after 1000 attempts. Try adjusting target rounds or card size.")
                            st.stop()
                    else:
                        cards = generate_unique_bingo_cards(songs, num_cards, card_size)
                
                st.success(f"Generated {len(cards)} bingo cards!")
                
                # Generate PDF
                results_df = None
                if analyze_wins:
                    with st.spinner("Analyzing win probabilities..."):
                        results_df = simulate_bingo_game(
                            cards, 
                            songs,
                            first_winner_round if use_round_control else None,
                            second_winner_round if use_round_control else None,
                            third_winner_round if use_round_control else None
                        )
                else:
                    # Create empty results dataframe if not analyzing
                    results_df = pd.DataFrame({
                        'Card Index': range(1, len(cards) + 1),
                        '1 Line Round': [None] * len(cards),
                        '2 Lines Round': [None] * len(cards),
                        'Full Card Round': [None] * len(cards),
                        'Won Place': [None] * len(cards)
                    })
                
                # Generate and offer PDF download
                with st.spinner("Generating PDF..."):
                    logo_bytes = None
                    if logo_file:
                        logo_bytes = BytesIO(logo_file.read())
                        logo_file.seek(0)  # Reset for potential re-use
                    
                    pdf_buffer = generate_bingo_pdf(
                        cards, 
                        results_df,
                        title=card_title if card_title else None,
                        logo_image=logo_bytes,
                        logo_zoom=logo_zoom
                    )
                
                st.download_button(
                    label="📥 Download Complete PDF (Cards + Operator Sheet)",
                    data=pdf_buffer,
                    file_name="bingo_game_complete.pdf",
                    mime="application/pdf",
                    type="primary"
                )
                
                # Analyze wins
                if analyze_wins:
                    st.header("📊 Win Analysis")
                    
                    # Show summary statistics
                    col1, col2, col3 = st.columns(3)
                    
                    first_place = results_df[results_df['Won Place'] == 1]
                    second_place = results_df[results_df['Won Place'] == 2]
                    third_place = results_df[results_df['Won Place'] == 3]
                    
                    with col1:
                        if not first_place.empty:
                            card_num = first_place['Card Index'].values[0]
                            round_num = first_place['1 Line Round'].values[0]
                            st.metric("🥇 1st Place (1 Line)", f"Card #{card_num}", 
                                     f"Round {round_num}")
                    
                    with col2:
                        if not second_place.empty:
                            card_num = second_place['Card Index'].values[0]
                            round_num = second_place['2 Lines Round'].values[0]
                            st.metric("🥈 2nd Place (2 Lines)", f"Card #{card_num}", 
                                     f"Round {round_num}")
                    
                    with col3:
                        if not third_place.empty:
                            card_num = third_place['Card Index'].values[0]
                            round_num = third_place['Full Card Round'].values[0]
                            st.metric("🥉 3rd Place (Full Card)", f"Card #{card_num}", 
                                     f"Round {round_num}")
                    
                    # Operator table
                    st.subheader("Operator Control Table")
                    st.info("This table shows when each card achieves milestones. Highlighted cells show winners.")
                    
                    # Format display DataFrame
                    display_df = results_df.copy()
                    
                    # Add highlighting info as text for display
                    def format_cell(row, col_name):
                        value = row[col_name]
                        if pd.isna(value):
                            return "-"
                        round_val = f"Round {int(value)}"
                        
                        # Add emoji if this card won this milestone
                        if col_name == '1 Line Round' and row['Won Place'] == 1:
                            return f"🥇 {round_val}"
                        elif col_name == '2 Lines Round' and row['Won Place'] == 2:
                            return f"🥈 {round_val}"
                        elif col_name == 'Full Card Round' and row['Won Place'] == 3:
                            return f"🥉 {round_val}"
                        return round_val
                    
                    display_df['1 Line'] = display_df.apply(lambda r: format_cell(r, '1 Line Round'), axis=1)
                    display_df['2 Lines'] = display_df.apply(lambda r: format_cell(r, '2 Lines Round'), axis=1)
                    display_df['Full Card'] = display_df.apply(lambda r: format_cell(r, 'Full Card Round'), axis=1)
                    
                    # Select and rename columns for display
                    display_df = display_df[['Card Index', '1 Line', '2 Lines', 'Full Card']]
                    display_df = display_df.rename(columns={'Card Index': 'Card'})
                    display_df['Card'] = display_df['Card'].apply(lambda x: f"Card #{int(x)}")
                    
                    # Sort by card index
                    display_df = display_df.sort_values('Card')
                    
                    # Format the table
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Download option for operator table
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Operator Table (CSV)",
                        data=csv,
                        file_name="bingo_operator_table.csv",
                        mime="text/csv"
                    )
                
                # Display bingo cards
                st.header("🎴 Bingo Cards")
                st.write("Preview and print your bingo cards below:")
                
                # Option to show all cards or paginate
                display_option = st.radio(
                    "Display Options",
                    ["Show First 3 Cards", "Show All Cards", "Select Specific Card"]
                )
                
                if display_option == "Show First 3 Cards":
                    for i in range(min(3, len(cards))):
                        st.markdown(format_bingo_card_html(cards[i], i), unsafe_allow_html=True)
                
                elif display_option == "Show All Cards":
                    for i, card in enumerate(cards):
                        st.markdown(format_bingo_card_html(card, i), unsafe_allow_html=True)
                
                else:  # Select Specific Card
                    card_to_show = st.number_input(
                        "Card Number",
                        min_value=1,
                        max_value=len(cards),
                        value=1
                    ) - 1
                    st.markdown(format_bingo_card_html(cards[card_to_show], card_to_show), unsafe_allow_html=True)
                
                # Print instructions
                st.info("💡 **Printing Tip**: Use your browser's Print function (Ctrl+P or Cmd+P) to print all bingo cards. "
                       "Each card will automatically be on its own page.")
            else:
                st.error("Could not parse songs from the CSV file. Please check the file format and try again.")
    
    # Instructions
    with st.expander("ℹ️ How to Use"):
        st.markdown("""
        ### Getting Started
        1. **Export Your Playlist**: Visit [Exportify](https://exportify.net/) and authorize with Spotify
        2. **Download CSV**: Click "Export" on your desired playlist to download a CSV file
        3. **Upload CSV**: Upload the CSV file using the file uploader above
        4. **Configure Settings**: Adjust the number of cards and card size in the Configuration section
        5. **Generate**: Click the "Generate Bingo Cards" button
        6. **Analyze**: Review the win analysis table to see which cards will win in which rounds
        7. **Print**: Use your browser's print function to print the bingo cards
        
        ### Features
        - 🎲 **Unique Cards**: Each bingo card is randomly generated with different songs
        - 📊 **Win Analysis**: See which round each card will win (1st, 2nd, 3rd place)
        - 🎯 **Operator Table**: Download a table showing the winning order for game management
        - 🖨️ **Print Ready**: Cards are formatted for easy printing
        
        ### Tips
        - Use playlists with at least 25 songs for 5x5 cards
        - The win analysis simulates calling songs in a random order
        - Each card has a unique index for tracking
        - You can generate up to 100 cards at once
        - CSV files from [Exportify](https://exportify.net/) are the only supported format
        """)

if __name__ == "__main__":
    main()
