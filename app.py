import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
import numpy as np
import random
import re
from typing import List, Tuple, Dict, Set
import itertools

st.set_page_config(page_title="Spotify Bingo Game", layout="wide")

def extract_playlist_id(url: str) -> str:
    """Extract playlist ID from Spotify URL."""
    # Pattern for Spotify playlist URLs
    patterns = [
        r'playlist/([a-zA-Z0-9]+)',
        r'playlist:([a-zA-Z0-9]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no pattern matches, assume the input is already a playlist ID
    return url.strip()

def get_playlist_tracks(playlist_url: str, client_id: str = None, client_secret: str = None) -> List[str]:
    """Fetch track names from a Spotify playlist."""
    try:
        playlist_id = extract_playlist_id(playlist_url)
        
        if client_id and client_secret:
            # Use credentials if provided
            auth_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
        else:
            # Use without authentication (limited functionality)
            sp = spotipy.Spotify()
        
        # Get playlist tracks
        results = sp.playlist_tracks(playlist_id)
        tracks = results['items']
        
        # Handle pagination if playlist has more than 100 songs
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        
        # Extract track names
        track_names = []
        for item in tracks:
            if item['track'] and item['track']['name']:
                track_names.append(item['track']['name'])
        
        return track_names
    
    except Exception as e:
        st.error(f"Error fetching playlist: {str(e)}")
        return []

def create_bingo_card(songs: List[str], card_size: int = 5) -> List[List[str]]:
    """Create a single bingo card with random songs."""
    # We need card_size * card_size songs for the bingo card
    num_squares = card_size * card_size
    
    if len(songs) < num_squares:
        st.warning(f"Not enough songs ({len(songs)}) for {card_size}x{card_size} card. Need at least {num_squares} songs.")
        # Pad with duplicates if needed
        while len(songs) < num_squares:
            songs.extend(songs[:num_squares - len(songs)])
    
    # Randomly select songs for this card
    selected_songs = random.sample(songs, num_squares)
    
    # Create 2D grid
    card = []
    for i in range(card_size):
        row = selected_songs[i * card_size:(i + 1) * card_size]
        card.append(row)
    
    return card

def generate_unique_bingo_cards(songs: List[str], num_cards: int, card_size: int = 5) -> List[List[List[str]]]:
    """Generate multiple unique bingo cards."""
    cards = []
    for _ in range(num_cards):
        card = create_bingo_card(songs, card_size)
        cards.append(card)
    return cards

def check_bingo_win(card: List[List[str]], called_songs: Set[str]) -> Tuple[bool, str]:
    """
    Check if a card has a bingo (row, column, or diagonal).
    Returns (has_won, win_type)
    """
    card_size = len(card)
    
    # Check rows
    for i, row in enumerate(card):
        if all(song in called_songs for song in row):
            return True, f"Row {i+1}"
    
    # Check columns
    for col in range(card_size):
        if all(card[row][col] in called_songs for row in range(card_size)):
            return True, f"Column {col+1}"
    
    # Check diagonal (top-left to bottom-right)
    if all(card[i][i] in called_songs for i in range(card_size)):
        return True, "Diagonal (TL-BR)"
    
    # Check diagonal (top-right to bottom-left)
    if all(card[i][card_size - 1 - i] in called_songs for i in range(card_size)):
        return True, "Diagonal (TR-BL)"
    
    return False, ""

def simulate_bingo_game(cards: List[List[List[str]]], songs: List[str]) -> pd.DataFrame:
    """
    Simulate the bingo game and determine when each card wins.
    Returns a DataFrame with card index, win round, and win type.
    """
    # Shuffle the song order for calling
    call_order = songs.copy()
    random.shuffle(call_order)
    
    results = []
    winners = []
    called_songs = set()
    
    for round_num, song in enumerate(call_order, 1):
        called_songs.add(song)
        
        # Check each card that hasn't won yet
        for card_idx, card in enumerate(cards):
            # Skip if card already won
            if card_idx in winners:
                continue
            
            has_won, win_type = check_bingo_win(card, called_songs)
            if has_won:
                winners.append(card_idx)
                place = len(winners)
                results.append({
                    'Card Index': card_idx + 1,
                    'Win Round': round_num,
                    'Win Type': win_type,
                    'Place': place,
                    'Song Called': song
                })
    
    # Add cards that never won
    for card_idx in range(len(cards)):
        if card_idx not in winners:
            results.append({
                'Card Index': card_idx + 1,
                'Win Round': None,
                'Win Type': 'No Win',
                'Place': None,
                'Song Called': None
            })
    
    return pd.DataFrame(results)

def calculate_win_probability(cards: List[List[List[str]]], songs: List[str], 
                              target_card: int, num_simulations: int = 100) -> float:
    """Calculate the probability that a specific card wins within certain rounds."""
    wins = 0
    
    for _ in range(num_simulations):
        results = simulate_bingo_game(cards, songs)
        card_result = results[results['Card Index'] == target_card + 1]
        if not card_result.empty and card_result['Place'].values[0] == 1:
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

def main():
    st.title("🎵 Spotify Playlist Bingo Game Generator")
    st.write("Create unique bingo cards from your favorite Spotify playlist!")
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    
    # Spotify credentials (optional)
    with st.sidebar.expander("Spotify API Credentials (Optional)", expanded=False):
        st.info("You can provide Spotify API credentials for better reliability. Get them at https://developer.spotify.com/")
        client_id = st.text_input("Client ID", type="password")
        client_secret = st.text_input("Client Secret", type="password")
    
    # Main input
    playlist_url = st.text_input(
        "Spotify Playlist URL or ID",
        placeholder="https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    )
    
    # Bingo game settings
    st.sidebar.subheader("Bingo Settings")
    num_cards = st.sidebar.slider("Number of Bingo Cards", min_value=1, max_value=100, value=10)
    card_size = st.sidebar.slider("Card Size (NxN)", min_value=3, max_value=7, value=5)
    
    # Win guarantee settings
    st.sidebar.subheader("Win Analysis")
    analyze_wins = st.sidebar.checkbox("Analyze Win Probabilities", value=True)
    
    if playlist_url:
        if st.button("Generate Bingo Cards", type="primary"):
            with st.spinner("Fetching playlist tracks..."):
                songs = get_playlist_tracks(
                    playlist_url,
                    client_id if client_id else None,
                    client_secret if client_secret else None
                )
            
            if songs:
                st.success(f"Found {len(songs)} songs in the playlist!")
                
                # Display song list
                with st.expander(f"View all {len(songs)} songs"):
                    st.write(", ".join(songs))
                
                # Generate bingo cards
                with st.spinner(f"Generating {num_cards} unique bingo cards..."):
                    cards = generate_unique_bingo_cards(songs, num_cards, card_size)
                
                st.success(f"Generated {len(cards)} bingo cards!")
                
                # Analyze wins
                if analyze_wins:
                    with st.spinner("Analyzing win probabilities..."):
                        results_df = simulate_bingo_game(cards, songs)
                    
                    st.header("📊 Win Analysis")
                    
                    # Show summary statistics
                    col1, col2, col3 = st.columns(3)
                    
                    first_place = results_df[results_df['Place'] == 1]
                    second_place = results_df[results_df['Place'] == 2]
                    third_place = results_df[results_df['Place'] == 3]
                    
                    with col1:
                        if not first_place.empty:
                            st.metric("🥇 1st Place", f"Card #{first_place['Card Index'].values[0]}", 
                                     f"Round {first_place['Win Round'].values[0]}")
                    
                    with col2:
                        if not second_place.empty:
                            st.metric("🥈 2nd Place", f"Card #{second_place['Card Index'].values[0]}", 
                                     f"Round {second_place['Win Round'].values[0]}")
                    
                    with col3:
                        if not third_place.empty:
                            st.metric("🥉 3rd Place", f"Card #{third_place['Card Index'].values[0]}", 
                                     f"Round {third_place['Win Round'].values[0]}")
                    
                    # Operator table
                    st.subheader("Operator Control Table")
                    st.info("This table shows which round each bingo card will win. Use this to call songs in order.")
                    
                    # Sort by win round
                    display_df = results_df.copy()
                    display_df = display_df.sort_values('Win Round', na_position='last')
                    
                    # Format the table
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Download option for operator table
                    csv = display_df.to_csv(index=False)
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
                st.error("Could not fetch songs from the playlist. Please check the URL and try again.")
    
    # Instructions
    with st.expander("ℹ️ How to Use"):
        st.markdown("""
        ### Getting Started
        1. **Get a Spotify Playlist URL**: Copy the link to any public Spotify playlist
        2. **Paste the URL**: Enter it in the text box above
        3. **Configure Settings**: Use the sidebar to adjust the number of cards and card size
        4. **Generate**: Click the "Generate Bingo Cards" button
        5. **Analyze**: Review the win analysis table to see which cards will win in which rounds
        6. **Print**: Use your browser's print function to print the bingo cards
        
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
        """)

if __name__ == "__main__":
    main()
