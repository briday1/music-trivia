# 🎵 Spotify Bingo Game Generator

A Streamlit web application that generates unique bingo cards from Spotify playlists. Perfect for music trivia nights, parties, or any event where you want to play bingo with your favorite songs!

## Features

- 🎧 **Spotify Integration**: Paste any public Spotify playlist URL to fetch all song titles
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

1. **Paste Spotify Playlist URL**: Copy the URL of any public Spotify playlist
   - Example: `https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M`

2. **Configure Settings** (in sidebar):
   - Number of Bingo Cards: 1-100 cards
   - Card Size: 3x3 to 7x7 grid
   - Win Analysis: Enable to see winning predictions

3. **Generate Cards**: Click "Generate Bingo Cards"

4. **View Results**:
   - Win analysis showing 1st, 2nd, and 3rd place winners
   - Operator table with round-by-round winning information
   - Preview of bingo cards

5. **Print**: Use your browser's print function (Ctrl+P / Cmd+P) to print cards

### Spotify Authentication

This app uses a **hybrid approach** for accessing Spotify playlists:

#### Option 1: No Credentials (Easiest)
The app will **automatically attempt** to fetch public playlists without requiring any credentials using SpotAPI. Just paste a playlist URL and go!

#### Option 2: With Credentials (More Reliable)
For better reliability, rate limits, and guaranteed access, you can provide Spotify API credentials:

**For App Owners (Recommended):**
Set environment variables so all users can access playlists:
```bash
export SPOTIPY_CLIENT_ID="your_client_id"
export SPOTIPY_CLIENT_SECRET="your_client_secret"
```

**For Individual Users:**
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app (or use an existing one)
3. Get your Client ID and Client Secret
4. Enter them in the app's sidebar under "Spotify API Credentials"

**Note:** The credential-free approach uses SpotAPI, which accesses Spotify's web API. While it works for most public playlists, the official Spotify API (with credentials) is more reliable and has higher rate limits.

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
The app simulates a bingo game by:
1. Shuffling the song order (simulating random calling)
2. Calling songs one by one
3. Checking each card for wins (rows, columns, diagonals)
4. Recording the round number when each card wins
5. Tracking 1st, 2nd, and 3rd place winners

### Operator Table
The operator table shows:
- Card Index: Unique identifier for each card
- Win Round: Which round the card will win
- Win Type: How the card wins (Row, Column, or Diagonal)
- Place: Winner ranking (1st, 2nd, 3rd)
- Song Called: The winning song

This table helps operators manage the game by knowing in advance which cards will win.

## Requirements

- Python 3.8+
- streamlit >= 1.28.0
- spotipy >= 2.23.0
- pandas >= 2.0.0
- numpy >= 1.24.0

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
- Spotify integration via [Spotipy](https://spotipy.readthedocs.io/)