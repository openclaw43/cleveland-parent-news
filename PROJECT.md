# Cleveland Parent News Data Collection

This project aggregates local news and events for Cleveland-area parents.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m src.collector
```

## Project Structure

```
cleveland-parent-news/
├── src/
│   ├── __init__.py
│   ├── collector.py      # Main data collection orchestrator
│   ├── rss_feeds.py      # RSS feed parser
│   ├── scrapers.py       # Website scrapers
│   └── filters.py        # Content filtering for parent-relevance
├── data/
│   ├── raw/              # Raw collected data
│   └── processed/        # Cleaned/filtered content
├── config/
│   └── sources.yaml      # News source configurations
└── notebooks/            # Analysis notebooks
```

## Data Sources

### News Outlets
- Cleveland.com (Plain Dealer)
- News 5 Cleveland (WKYC)
- Fox 8 Cleveland
- Cleveland Scene
- Axios Cleveland

### Community/Schools
- Cleveland Metropolitan School District
- Local library events
- Metroparks events
- Museum events (CMNH, Art Museum, etc.)

### Parent-Focused
- Local parenting groups
- Eventbrite family events
- Facebook community pages

## License

MIT
