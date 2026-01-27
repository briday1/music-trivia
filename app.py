import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
import numpy as np
import random
import re
import os
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
    """Fetch track names from a Spotify playlist.
    
    This function uses a hybrid approach:
    1. First tries SpotAPI (no credentials needed) for public playlists
    2. Falls back to Spotipy with Client Credentials if SpotAPI fails or credentials are provided
    
    Args:
        playlist_url: Spotify playlist URL or ID
        client_id: Optional client ID (overrides environment variable)
        client_secret: Optional client secret (overrides environment variable)
    
    Returns:
        List of track names from the playlist
    """
    try:
        playlist_id = extract_playlist_id(playlist_url)
        
        # Try to get credentials from parameters first, then fall back to environment variables
        final_client_id = client_id or os.environ.get('SPOTIPY_CLIENT_ID')
        final_client_secret = client_secret or os.environ.get('SPOTIPY_CLIENT_SECRET')
        
        # Try SpotAPI first (no credentials needed) if credentials are not provided
        if not final_client_id or not final_client_secret:
            try:
                from spotapi import PublicPlaylist
                
                st.info("Attempting to fetch playlist without credentials using SpotAPI...")
                playlist = PublicPlaylist(playlist_id)
                result = playlist.get_playlist_info()
                
                # Extract track names from SpotAPI response
                track_names = []
                tracks = result.get('tracks', {}).get('items', [])
                for item in tracks:
                    track = item.get('track', {})
                    if track and track.get('name'):
                        track_names.append(track['name'])
                
                # Handle pagination if needed
                total_tracks = result.get('tracks', {}).get('total', len(track_names))
                if len(track_names) < total_tracks:
                    # Use pagination to get remaining tracks
                    for page_data in playlist.paginate_playlist():
                        for item in page_data.get('items', []):
                            track = item.get('track', {})
                            if track and track.get('name'):
                                track_names.append(track['name'])
                
                if track_names:
                    st.success(f"Successfully fetched {len(track_names)} tracks without credentials!")
                    return track_names
                    
            except Exception as spotapi_error:
                st.warning(f"SpotAPI failed: {str(spotapi_error)}. Trying with Spotify API credentials...")
        
        # Fall back to Spotipy with credentials
        if not final_client_id or not final_client_secret:
            st.error("Spotify API credentials are required to access this playlist.")
            st.info("""
            **Option 1 (Recommended for app owners):** Set environment variables:
            - `SPOTIPY_CLIENT_ID`
            - `SPOTIPY_CLIENT_SECRET`
            
            **Option 2:** Provide credentials in the sidebar below.
            
            Get free credentials at: https://developer.spotify.com/dashboard
            """)
            return []
        
        # Use Spotipy with credentials
        auth_manager = SpotifyClientCredentials(
            client_id=final_client_id,
            client_secret=final_client_secret
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
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

def generate_unique_bingo_cards(songs: List[str], num_cards: int, card_size: int = 5, free_space: bool = True) -> List[List[List[str]]]:
    """Generate multiple unique bingo cards."""
    cards = []
    for _ in range(num_cards):
        card = create_bingo_card(songs, card_size, free_space)
        cards.append(card)
    return cards

def check_bingo_win(card: List[List[str]], called_songs: Set[str]) -> Tuple[bool, str]:
    """
    Check if a card has a bingo (row, column, or diagonal).
    Returns (has_won, win_type)
    FREE SPACE is automatically considered as called/matched.
    """
    card_size = len(card)
    
    # Helper function to check if a song is called (FREE SPACE is always considered called)
    def is_called(song: str) -> bool:
        return song == "FREE SPACE" or song in called_songs
    
    # Check rows
    for i, row in enumerate(card):
        if all(is_called(song) for song in row):
            return True, f"Row {i+1}"
    
    # Check columns
    for col in range(card_size):
        if all(is_called(card[row][col]) for row in range(card_size)):
            return True, f"Column {col+1}"
    
    # Check diagonal (top-left to bottom-right)
    if all(is_called(card[i][i]) for i in range(card_size)):
        return True, "Diagonal (TL-BR)"
    
    # Check diagonal (top-right to bottom-left)
    if all(is_called(card[i][card_size - 1 - i]) for i in range(card_size)):
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
        elements.append(Spacer(1, 0.2*inch))
        
        # Add card index in bottom corner
        elements.append(Paragraph(f"Card #{card_idx + 1}", index_style))
        
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
        "<b>Instructions:</b> This table shows the order in which bingo cards will win as you call songs from the playlist.",
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.3*inch))
    
    # Create operator table
    op_data = [['Card', 'Win Round', 'Win Type', 'Place', 'Song Called']]
    
    for _, row in results_df.iterrows():
        card_idx = f"Card #{int(row['Card Index'])}"
        win_round = f"Round {int(row['Win Round'])}" if pd.notna(row['Win Round']) else "No Win"
        win_type = row['Win Type'] if pd.notna(row['Win Type']) else "-"
        
        if pd.notna(row['Place']):
            place = int(row['Place'])
            if place == 1:
                place_text = "🥇 1st"
            elif place == 2:
                place_text = "🥈 2nd"
            elif place == 3:
                place_text = "🥉 3rd"
            else:
                place_text = str(place)
        else:
            place_text = "-"
        
        song = row['Song Called'] if pd.notna(row['Song Called']) else "-"
        
        op_data.append([card_idx, win_round, win_type, place_text, song])
    
    op_table = Table(op_data, colWidths=[0.8*inch, 1.2*inch, 1.5*inch, 1*inch, 3*inch])
    op_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fff9c4')),  # 1st place
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#ffe0b2')),  # 2nd place
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#ffccbc')),  # 3rd place
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(op_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer

def main():
    st.title("🎵 Spotify Playlist Bingo Game Generator")
    st.write("Create unique bingo cards from your favorite Spotify playlist!")
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    
    # Spotify credentials (optional but recommended)
    with st.sidebar.expander("Spotify API Credentials (Optional)", expanded=False):
        st.info("""
        **No credentials?** The app will try to fetch playlists without them first.
        
        **Have credentials?** Provide them for more reliable access and higher rate limits.
        
        Get free credentials at: https://developer.spotify.com/dashboard
        """)
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
    
    # PDF Customization
    st.sidebar.subheader("PDF Customization")
    card_title = st.sidebar.text_input("Card Title (optional)", placeholder="e.g., Music Bingo Night")
    
    # Logo upload
    logo_file = st.sidebar.file_uploader("Upload Logo for Free Space (optional)", type=['png', 'jpg', 'jpeg'])
    logo_zoom = 1.0
    if logo_file:
        logo_zoom = st.sidebar.slider("Logo Zoom", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
    
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
                
                # Generate PDF
                results_df = None
                if analyze_wins:
                    with st.spinner("Analyzing win probabilities..."):
                        results_df = simulate_bingo_game(cards, songs)
                else:
                    # Create empty results dataframe if not analyzing
                    results_df = pd.DataFrame({
                        'Card Index': range(1, len(cards) + 1),
                        'Win Round': [None] * len(cards),
                        'Win Type': [None] * len(cards),
                        'Place': [None] * len(cards),
                        'Song Called': [None] * len(cards)
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
