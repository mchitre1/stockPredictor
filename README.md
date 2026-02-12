# Stock Predictor

A daily stock picker that uses **historical price data** and **optional news** to suggest one stock from your watchlist each day. It runs at **9:00 AM EST** (before market open) and tracks **accuracy** over time.

## Features

- **Watchlist** — Add and remove stock symbols (saved in SQLite).
- **Daily prediction** — Scores each symbol using short-term momentum (1d, 5d, 20d) and optional news sentiment (Finnhub).
- **Today’s pick** — Shown on the dashboard; you can also run a prediction manually.
- **Scheduler toggle** — Turn the 9 AM / 5 PM schedule on or off from the UI (e.g. for testing outside market hours).
- **Accuracy tracking** — Compares each pick to the next trading day’s return; “correct” = next-day return > 0%. Updated daily at 5 PM EST.
- **Web UI** — Dashboard with saved stocks, today’s pick, accuracy stats, and history.

## Prerequisites

- **Python 3.9+**
- (Optional) [Finnhub](https://finnhub.io) free API key for news-based scoring

## Quick start

### 1. Clone and enter the repo

```bash
git clone https://github.com/YOUR_USERNAME/stockPredictor.git
cd stockPredictor
```

### 2. Create a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Optional: enable news-based scoring

Copy the example env file and add your Finnhub API key (free at [finnhub.io](https://finnhub.io)):

```bash
cp .env.example .env
```

Edit `.env` and set:

```
FINNHUB_API_KEY=your_key_here
```

Without this, predictions use only price momentum (no API key required).

### 5. Run the app

```bash
python run.py
```

Open **http://localhost:5000** in your browser.

## How to use

### Dashboard

- **Scheduler** — Shows whether the daily schedule is **On** or **Off**. Use **Turn on** / **Turn off** to enable or pause the 9 AM prediction and 5 PM accuracy jobs (handy for testing outside market hours).
- **Today’s pick** — The current recommended symbol and a short reason. Click **Run prediction now** to generate a new pick anytime.
- **Accuracy** — Correct/total count and percentage; table of recent dates, pick, actual return, and result (Correct/Wrong).
- **Saved stocks (watchlist)** — Add symbols (e.g. `AAPL`, `MSFT`, `GOOGL`) and optional names. Remove with the **×** next to each row.
- **Recent predictions** — Last 14 predictions with date, symbol, score, and reason.

### Scheduler

- **On** — Prediction runs at **9:00 AM EST**, accuracy update at **5:00 PM EST**.
- **Off** — No automatic runs; you can still use **Run prediction now** and add/remove stocks.

To start the app with the scheduler **paused** (e.g. for development), set:

```bash
# Windows PowerShell
$env:DISABLE_SCHEDULER="1"; python run.py

# macOS / Linux
DISABLE_SCHEDULER=1 python run.py
```

Then use **Turn on** in the UI when you want the schedule active.

### Data and storage

- Stock data comes from **Yahoo Finance** via `yfinance` (no API key).
- Predictions and accuracy are stored in **SQLite** in the `data/` folder (created on first run).
- The `data/` folder is gitignored; back it up if you want to keep history.

## Project structure

```
stockPredictor/
├── app/
│   ├── __init__.py      # Flask app factory
│   ├── database.py      # SQLite setup
│   ├── models.py        # Watchlist, predictions, accuracy
│   ├── stock_data.py    # yfinance price fetch
│   ├── news_data.py     # Finnhub news (optional)
│   ├── predictor.py     # Scoring and daily pick
│   ├── accuracy.py      # Next-day return and correctness
│   ├── scheduler.py     # 9 AM / 5 PM jobs, on/off toggle
│   ├── routes.py        # Web and API routes
│   ├── static/          # CSS
│   └── templates/       # HTML
├── config.py            # Paths, API keys, schedule time
├── run.py               # Entry point
├── requirements.txt
├── .env.example         # Copy to .env and set FINNHUB_API_KEY
└── README.md
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `FINNHUB_API_KEY` | (Optional) Finnhub API key for news sentiment in scoring. |
| `DISABLE_SCHEDULER` | Set to `1` to start with scheduler paused; turn on in UI. |
| `SECRET_KEY` | Flask secret; set in production. |
| `FLASK_ENV` | e.g. `development` or `production`. |

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This tool is for **educational and personal use only**. It is not financial advice. Past accuracy does not guarantee future results. Always do your own research before investing.
