# discord-analytics

## Overview
Discord Analytics is a Python project scaffold for building a Discord bot and a Streamlit dashboard for server insights and reporting.

## Features
- Discord bot foundation using `discord.py`
- Analytics and persistence layers prepared for SQLAlchemy-based models
- Streamlit dashboard scaffold for visual reporting
- Test-ready project structure with `pytest`

## Tech Stack
- Python
- discord.py
- SQLAlchemy
- pandas
- Streamlit
- Plotly
- Alembic
- SQLite / aiosqlite
- pytest / pytest-asyncio

## Prerequisites
- Python 3.11 or newer
- `pip`
- A Discord bot token

## Installation
1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration
Create a `.env` file in the project root with your environment variables, for example:

```env
DISCORD_TOKEN=your-token-here
```

## Running the Bot
Run the bot entry point:

```bash
python run_bot.py
```

## Running the Dashboard
Run the Streamlit dashboard:

```bash
streamlit run run_dashboard.py
```

## Project Structure
- `bot/` - Discord bot package and event handlers
- `bot/events/` - Bot event modules
- `db/` - Database models, sessions, and migrations support
- `analytics/` - Analytics logic and data processing
- `dashboard/` - Streamlit dashboard application package
- `dashboard/pages/` - Dashboard page modules
- `dashboard/components/` - Shared dashboard components
- `utils/` - Shared utility helpers
- `tests/` - Automated tests
# Analytics-Naya
