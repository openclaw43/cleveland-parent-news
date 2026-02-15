# Cleveland Parent News

A local news aggregator and blog focused on Cleveland, Ohio happenings for parents.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/openclaw43/cleveland-parent-news.git
cd cleveland-parent-news

# Install dependencies with UV
uv sync

# Run the collector
uv run python -m src.collector

# Generate newsletter from collected data
uv run python -m src.newsletter
```

## What It Does

1. **Collects** news from Cleveland-area RSS feeds (Fox 8, Axios, Cleveland Scene)
2. **Filters** articles for parent-relevance using keyword scoring
3. **Stores** articles in SQLite database with deduplication
4. **Generates** Substack-ready newsletter with top stories

## Project Structure

```
cleveland-parent-news/
├── src/
│   ├── collector.py      # Main orchestrator
│   ├── rss_feeds.py      # RSS parser
│   ├── scrapers.py       # Web scrapers
│   ├── filters.py        # Content filtering
│   ├── database.py       # SQLite storage
│   └── newsletter.py     # Newsletter generator
├── config/
│   └── sources.yaml      # Data source configuration
├── data/
│   ├── raw/              # Collected articles
│   └── processed/        # Filtered content
└── RESEARCH.md           # Comprehensive data source research
```

## Data Sources

### Working RSS Feeds
- **Fox 8 Cleveland** ✅
- **Axios Cleveland** ✅
- **Cleveland Scene** ✅
- **Cleveland.com** ⚠️ (needs encoding fix)
- **WKYC** ⚠️ (needs encoding fix)

### Research Phase
See `RESEARCH.md` for 50+ additional sources including:
- School districts (CMSD, Beachwood, Shaker, etc.)
- Museums & cultural venues
- Metroparks & libraries
- Event calendars

## Configuration

Edit `config/sources.yaml` to:
- Add/remove RSS feeds
- Configure scrapers
- Adjust parent-relevance keywords
- Set rate limiting

## Automation

Set up a daily cron job:

```bash
# Add to crontab
0 6 * * * cd /path/to/cleveland-parent-news && uv run python -m src.collector
```

Or use the built-in scheduler:

```python
# In src/collector.py, uncomment:
# schedule.every().day.at("06:00").do(main)
```

## Dependencies

Managed with [Astral UV](https://docs.astral.sh/uv/):
- `feedparser` - RSS parsing
- `requests` - HTTP requests
- `beautifulsoup4` - HTML scraping
- `pyyaml` - Configuration
- `schedule` - Cron-like scheduling

## License

MIT

---

*Built with OpenCode + GLM-5, packaged with Astral UV*
