Goal

Build a public portfolio project that demonstrates a near-real-time stock + crypto analytics pipeline using:

GitHub Actions
Python
Alpaca API
Binance API
Databricks Free Edition
Delta Lake
Bronze / Silver / Gold tables
GitHub Pages or separate project frontend

This is not a high-frequency trading system. It is a near-real-time analytics lakehouse project.

Final Architecture
GitHub Actions scheduled workflow
        ↓
Python script fetches stock + crypto data
        ↓
Data is normalized into JSONL batch format
        ↓
GitHub Actions uploads raw batch to Databricks Volume
        ↓
GitHub Actions triggers Databricks processing
        ↓
Databricks processes Bronze → Silver → Gold
        ↓
GitHub Actions queries Gold summary table
        ↓
GitHub Actions creates latest_summary.json
        ↓
Frontend reads latest_summary.json and displays dashboard
Hosting Decision

Keep the existing portfolio on Cloudflare.

Host this project separately using either:

Option A: GitHub Pages
Option B: separate Cloudflare Pages project

Preferred MVP:

GitHub Pages for the Databricks project showcase
Existing Cloudflare portfolio links to it

This avoids consuming the existing portfolio’s Cloudflare Pages build quota.

Repository Structure
market-lakehouse-project/
├── ingestion/
│   ├── fetch_market_data.py
│   ├── normalize_market_data.py
│   ├── upload_to_databricks.py
│   ├── query_databricks_summary.py
│   └── run_pipeline.py
│
├── databricks/
│   ├── setup/
│   │   ├── create_catalog_objects.sql
│   │   └── create_volume.sql
│   │
│   ├── notebooks/
│   │   ├── bronze_ingestion.py
│   │   ├── silver_transform.py
│   │   └── gold_aggregation.py
│   │
│   └── sql/
│       ├── latest_summary.sql
│       ├── symbol_performance.sql
│       └── volatility_summary.sql
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── latest_summary.json
│
├── docs/
│   ├── architecture.md
│   ├── data_model.md
│   └── demo_script.md
│
├── .github/
│   └── workflows/
│       └── market_pipeline.yml
│
├── sample_data/
│   └── sample_market_batch.jsonl
│
├── README.md
├── requirements.txt
└── .gitignore
Data Sources

Use these for MVP:

Stocks

Use Alpaca.

Symbols:

AAPL
MSFT
NVDA
TSLA
AMZN
Crypto

Use Binance.

Symbols:

BTCUSDT
ETHUSDT
SOLUSDT
Data Format

Normalize all fetched data into one common schema before uploading to Databricks.

Target fields:

source
asset_type
symbol
price
volume
event_time
ingestion_time
batch_id

Example asset types:

stock
crypto

Example sources:

alpaca
binance

Each GitHub Actions run should create one small JSONL batch file.

Databricks Storage

Create a Unity Catalog Volume:

main.default.market_landing

Raw landing path:

/Volumes/main/default/market_landing/raw/

Checkpoint path:

/Volumes/main/default/market_landing/checkpoints/

Schema path:

/Volumes/main/default/market_landing/schemas/
Databricks Tables

Create three layers.

Bronze Table
main.default.bronze_market_events

Purpose:

Store raw uploaded market events with minimal modification.

Fields:

source
asset_type
symbol
price
volume
event_time
ingestion_time
batch_id
source_file
Silver Table
main.default.silver_market_ticks

Purpose:

Clean, typed, deduplicated market data.

Transformations:

Cast price to numeric
Cast volume to numeric
Cast event_time to timestamp
Remove null symbols
Remove invalid prices
Remove duplicate records using batch_id + symbol + event_time
Standardize symbol names
Gold Tables
Latest Summary
main.default.gold_market_summary

Purpose:

Latest project dashboard data.

Fields:

symbol
asset_type
latest_price
previous_price
price_change
price_change_percent
volume
high
low
last_updated
Candles Table
main.default.gold_market_candles

Purpose:

Aggregated time-window analytics.

Fields:

symbol
asset_type
window_start
window_end
open
high
low
close
volume
GitHub Actions Workflow

Run on a schedule.

MVP frequency:

Every 30 or 60 minutes

Do not start with every 5 minutes.

Workflow responsibilities:

1. Checkout repository
2. Set up Python
3. Install dependencies
4. Fetch stock data
5. Fetch crypto data
6. Normalize records
7. Write JSONL batch
8. Upload batch to Databricks Volume
9. Trigger Databricks processing
10. Query Gold summary table
11. Save result as frontend/latest_summary.json
12. Deploy/update project frontend
Databricks API Direction

Important:

GitHub Actions calls Databricks API.
Databricks should not call external APIs.

This avoids Databricks Free Edition outbound internet limitations.

Correct:

GitHub Actions → Databricks

Avoid:

Databricks → Alpaca/Binance/Cloudflare
Secrets

Use GitHub Secrets only.

Required secrets:

DATABRICKS_HOST
DATABRICKS_TOKEN
DATABRICKS_WAREHOUSE_ID
ALPACA_API_KEY
ALPACA_SECRET_KEY

Optional later:

CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_PROJECT_NAME

Never commit:

.env
API keys
Databricks tokens
Alpaca credentials
Cloudflare credentials
databricks.cfg
debug logs with headers
Frontend

Build a simple static project page.

It should show:

Project title
Architecture diagram
Last updated time
Latest stock prices
Latest crypto prices
Top movers
Price change percentage
Volume
Short explanation of Bronze / Silver / Gold architecture
GitHub repo link
Databricks project explanation

The frontend reads:

frontend/latest_summary.json

MVP can be static.

Later, replace static JSON with KV/R2/API if needed.

README Requirements

README should include:

Project overview
Architecture diagram
Tech stack
Data sources
Databricks Bronze/Silver/Gold explanation
GitHub Actions pipeline explanation
Security notes
How to run locally
How to deploy
Screenshots
Limitations
Future improvements

Important wording:

This project demonstrates a near-real-time market analytics lakehouse, not a trading platform.
MVP Scope

Build only this first:

5 stock symbols
3 crypto symbols
GitHub Actions every 30–60 minutes
JSONL batch upload to Databricks Volume
Bronze table
Silver table
Gold summary table
latest_summary.json
Simple frontend dashboard

Avoid for MVP:

Kafka
Event Hubs
WebSockets
Machine learning
User authentication
Complex charting
Real-time streaming claims
Cloudflare Worker integration
Acceptance Criteria

The MVP is complete when:

GitHub Actions runs successfully on schedule
Market data is fetched from Alpaca and Binance
A JSONL batch is uploaded to Databricks
Bronze table receives raw records
Silver table contains cleaned records
Gold table contains latest summary metrics
latest_summary.json is generated from Databricks Gold data
Frontend displays latest market summary
No secrets are committed to the repo
README clearly explains the architecture
Future Enhancements

After MVP:

Add 1-minute or 5-minute candle charts
Add volatility calculations
Add top movers
Add anomaly detection
Add historical trend chart
Add Cloudflare R2/KV for dynamic public summary data
Add Databricks dashboard screenshots
Add cost/free-tier explanation page
Add CI validation for scripts
Add sample data replay mode
Codex Instruction

Build this project incrementally.

Priority order:

1. Repo structure
2. Ingestion scripts
3. Databricks upload
4. Databricks table setup
5. Databricks processing scripts
6. Gold summary query
7. latest_summary.json generation
8. Frontend dashboard
9. GitHub Actions automation
10. README and documentation

Focus on:

Clean architecture
Safe secret handling
Small free-tier-friendly data volume
Databricks Bronze/Silver/Gold modeling
Clear portfolio presentation