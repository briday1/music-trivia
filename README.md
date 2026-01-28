# 🎵 Music Bingo Game Generator

A Streamlit web application that generates unique bingo cards from Spotify playlists exported via Exportify. Perfect for music trivia nights, parties, or any event where you want to play bingo with your favorite songs!

## Features

- 🎧 **CSV Import**: Upload playlists exported from Exportify (https://exportify.net/)
- 🎲 **Unique Bingo Cards**: Generate multiple unique bingo cards (up to 100)
- 📊 **Win Analysis**: Automatically analyze which cards will win in which rounds
- 🏆 **Multiple Winners**: Track 1st, 2nd, and 3rd place winners
- 📋 **Operator Table**: Get a detailed table showing which round each card wins
- 🖨️ **Print Ready**: Cards are formatted for easy printing with unique indexes
- ⚙️ **Customizable**: Adjust card size (3x3 to 7x7) and number of cards

## Installation

1. Clone this repository:
```bash
git clone https://github.com/briday1/music-trivia.git
cd music-trivia
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the App

Start the Streamlit app:
```bash
streamlit run app.py
```

The app will open in your default web browser at `http://localhost:8501`

### Using the App

1. **Export Your Playlist**: 
   - Visit [Exportify](https://exportify.net/)
   - Click "Get Started" and authorize with your Spotify account
   - Click "Export" next to the playlist you want to use
   - Download the CSV file

2. **Upload CSV File**: Upload the downloaded CSV file in the app

3. **Configure Settings** (in sidebar):
   - Number of Bingo Cards: 1-100 cards
   - Card Size: 3x3 to 7x7 grid
   - Win Analysis: Enable to see winning predictions

4. **Generate Cards**: Click "Generate Bingo Cards"

5. **View Results**:
   - Win analysis showing 1st, 2nd, and 3rd place winners
   - Operator table with round-by-round winning information
   - Preview of bingo cards

6. **Print**: Use your browser's print function (Ctrl+P / Cmd+P) to print cards

## Examples

See [EXAMPLES.md](docs/EXAMPLES.md) for visual examples of:
- 📋 Sample bingo card with classic rock songs
- 📊 Operator reference sheet showing win progression
- 🎮 Complete game flow walkthrough

## How It Works

### Bingo Card Generation
- Each card is randomly generated from the playlist songs
- Cards are unique with different song arrangements
- Each card is assigned a unique index number

### Win Analysis
The app simulates a bingo game with the following winning rules:

**1st Place Winner:**
- Requires **one complete line** (horizontal or vertical)
- No diagonals allowed
- First card to achieve one line wins 1st place

**2nd Place Winner:**
- Requires **two complete lines** (horizontal or vertical)
- Must be a different card from the 1st place winner
- Only one winner per round

**3rd Place Winner:**
- Requires **full card** (all spaces called)
- Must be a different card from 1st and 2nd place winners

The simulation process:
1. Shuffles the song order (simulating random calling)
2. Calls songs one by one
3. Checks each card for wins based on place requirements
4. Records the round number when each card wins
5. Ensures only one winner per round

**Optional Round Control:**
You can optionally set target rounds for each winner using sliders in the sidebar. This allows you to control when winners are determined during the game.

### Operator Table
The operator table shows:
- Card Index: Unique identifier for each card
- Win Round: Which round the card will win
- Win Type: How the card wins (e.g., "Row 1", "Row 2, Column 3", "Full Card")
- Place: Winner ranking (1st, 2nd, 3rd)
- Song Called: The winning song

This table helps operators manage the game by knowing in advance which cards will win.

## Requirements

- Python 3.8+
- streamlit >= 1.28.0
- pandas >= 2.0.0
- numpy >= 1.24.0
- reportlab >= 4.0.0
- Pillow >= 10.0.0

## Example Use Cases

- **Music Trivia Nights**: Create bingo cards for themed music events
- **Parties**: Use popular playlists for party games
- **Education**: Music appreciation classes or workshops
- **Fundraisers**: Bingo games with custom music themes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Playlist export via [Exportify](https://exportify.net/)