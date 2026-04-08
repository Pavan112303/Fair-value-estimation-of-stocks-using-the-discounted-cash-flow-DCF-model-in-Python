# DCF Fair Value Estimation Web App

A Flask-based stock valuation application that estimates intrinsic value using the Discounted Cash Flow (DCF) method, with an interactive frontend, optional premium analytics, watchlist support, PDF report export, and currency conversion utilities.

## What This Project Solves

This project helps you answer one practical question:

"Based on projected cash flows and required return assumptions, is this stock undervalued, fairly valued, or overvalued?"

The app combines financial data retrieval, valuation logic, and clean visual output in one workflow so you can move from ticker input to decision-ready valuation insights quickly.

## Key Features

- DCF fair value estimation from projected free cash flow (FCF)
- Multi-market ticker handling (US and Indian markets)
- Fallback logic when direct FCF history is limited
- Sensitivity analysis to evaluate assumption risk
- Monte Carlo, peer analysis, and risk metric hooks (premium section)
- Watchlist management
- Currency conversion utility with fallback exchange logic
- PDF report export for valuation summaries
- Valuation history persistence via SQLite

## Tech Stack

- Backend: Python, Flask
- Data: yfinance + custom data interface helpers
- Numerical processing: pandas, numpy
- Visualization: matplotlib, seaborn, Chart.js
- Reports: reportlab
- Frontend: HTML, CSS, JavaScript, Bootstrap
- Storage: SQLite (`valuation_history.db`)

## Project Structure

```text
.
|-- app.py
|-- config.py
|-- data_interface.py
|-- dcf_calculator.py
|-- requirements.txt
|-- requirements-minimal.txt
|-- templates/
|   |-- index.html
|   `-- landing.html
`-- static/
    |-- css/
    |   `-- style.css
    `-- js/
        `-- app.js
```

## How the Valuation Flow Works

1. User enters a ticker and valuation assumptions in the UI.
2. Backend resolves ticker and market context.
3. App fetches company financials and market metadata.
4. FCF series is derived; if unavailable, fallback estimation is attempted.
5. DCF engine computes enterprise value and fair value per share.
6. App compares fair value with current market price to derive upside/downside.
7. Recommendation label is assigned (`STRONG BUY`, `BUY`, `HOLD`, `SELL`, `STRONG SELL`).
8. Result is rendered in dashboard cards, tables, charts, and optional export tools.

## DCF Method (High-Level)

The implementation follows the standard idea:

- Project future FCF for a defined horizon
- Estimate terminal value after explicit forecast period
- Discount projected value back to present using required return assumptions
- Adjust for debt/cash and divide by shares outstanding for per-share fair value

Conceptually:

$$
	ext{Fair Value per Share} = \frac{\text{PV(Explicit FCF)} + \text{PV(Terminal Value)} - \text{Net Debt}}{\text{Shares Outstanding}}
$$

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. Clone this repository.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python app.py
```

4. Open:

```text
http://localhost:5000
```

## Usage Guide

### Basic Analysis

1. Select market (US or IN).
2. Enter ticker (for Indian symbols, use `.NS` or `.BO` as needed).
3. Set growth rates, tax rate, projection years, and risk-free rate.
4. Click Analyze.
5. Review fair value, current price, upside/downside, and recommendation.

### Tools Tab

- Currency Converter: convert values between supported currencies
- Watchlist: add/view tickers quickly
- PDF Export: generate report snapshots

## Main API Endpoints

- `GET /` - Landing page
- `GET /analyze` - Main analysis UI
- `POST /analyze` - Run stock valuation
- `POST /convert_currency` - Convert amount from one currency to another
- `GET /valuation_history/<ticker>` - Retrieve stored valuation history
- `GET /popular_stocks` - Fetch curated stock list
- `POST /watchlist` and `GET /watchlist` - Watchlist utilities
- `GET /export_pdf/<ticker>` - Generate valuation report PDF

## Configuration Notes

- Flask `secret_key` is currently defined in source; move this to environment variables for production.
- Currency conversion first attempts market quote lookup and then uses fallback rates when required.
- SQLite is used for local history; production deployments should migrate to managed storage.

## Limitations

- Public market data can be delayed or incomplete.
- Some tickers may not have enough reported fields for robust FCF extraction.
- DCF output is highly sensitive to growth, discount, and terminal assumptions.

## Troubleshooting

1. Ticker not found:
   - Verify symbol format and market suffix.
   - Try known symbols to validate connectivity.

2. FCF-related errors:
   - Some firms have sparse/irregular cash flow statements.
   - Adjust horizon assumptions and retry.

3. Charts not visible:
   - Check browser console for JavaScript errors.
   - Hard refresh static assets.

4. Currency conversion unavailable:
   - Verify internet access for quote fetch.
   - Fallback rates should still provide approximate conversion.

## Security and Production Suggestions

- Move secrets and API-sensitive config to environment variables.
- Add structured logging and request tracing.
- Add unit tests for DCF scenarios and edge cases.
- Introduce CI checks for linting and test coverage.

## Disclaimer

This project is for educational and analytical use only. It is not investment advice. Always validate assumptions independently and consult a qualified financial advisor for investment decisions.

## License

MIT License (or project owner preferred license).
