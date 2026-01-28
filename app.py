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

def generate_unique_bingo_cards(songs: List[str], num_cards: int, card_size: int = 5, free_space: bool = True) -> List[List[List[str]]]:
    """Generate multiple unique bingo cards."""
    cards = []
    for _ in range(num_cards):
        card = create_bingo_card(songs, card_size, free_space)
        cards.append(card)
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
    Simulate the bingo game and determine when each card wins based on new rules:
    - 1st place: One complete line (row or column, no diagonals)
    - 2nd place: Two complete lines
    - 3rd place: Full card
    
    Args:
        cards: List of bingo cards
        songs: List of all songs in the playlist
        first_winner_round: Target round for 1st place winner (optional)
        second_winner_round: Target round for 2nd place winner (optional)
        third_winner_round: Target round for 3rd place winner (optional)
    
    Returns a DataFrame with card index, win round, and win type.
    """
    # Shuffle the song order for calling
    call_order = songs.copy()
    random.shuffle(call_order)
    
    results = []
    place_winners = {1: None, 2: None, 3: None}  # Track which card won each place
    called_songs = set()
    
    for round_num, song in enumerate(call_order, 1):
        called_songs.add(song)
        
        # Check for each place in order (1st, 2nd, 3rd)
        for place in [1, 2, 3]:
            # Skip if this place already has a winner
            if place_winners[place] is not None:
                continue
            
            # Skip if we're not at the target round for this place yet
            if place == 1 and first_winner_round and round_num < first_winner_round:
                continue
            if place == 2 and second_winner_round and round_num < second_winner_round:
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
                    results.append({
                        'Card Index': card_idx + 1,
                        'Win Round': round_num,
                        'Win Type': win_type,
                        'Place': place,
                        'Song Called': song
                    })
                    break  # Only one winner per round per place
        
        # Stop if all three places have winners
        if all(place_winners[p] is not None for p in [1, 2, 3]):
            break
    
    # Add cards that never won
    winning_card_indices = set(place_winners[p] for p in [1, 2, 3] if place_winners[p] is not None)
    for card_idx in range(len(cards)):
        if card_idx not in winning_card_indices:
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
            "Third place winner: Fill sheet"
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
