# DCF Stock Valuation Tool

A comprehensive web application for stock valuation using the Discounted Cash Flow (DCF) model. This tool provides professional-grade financial analysis with an intuitive user interface.

## Features

- **Real-time Stock Data**: Fetch live stock data using Yahoo Finance API
- **DCF Model Implementation**: Complete discounted cash flow valuation
- **Interactive Charts**: Visual representation of cash flows and valuation metrics
- **Sensitivity Analysis**: Test different scenarios and assumptions
- **Responsive Design**: Modern, mobile-friendly interface
- **Professional Reports**: Detailed valuation breakdowns and recommendations

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

### Basic Analysis

1. **Enter Stock Ticker**: Type a valid stock symbol (e.g., AAPL, MSFT, GOOGL)
2. **Set Growth Rates**: Define annual growth rates for the projection period
3. **Configure Parameters**: Adjust tax rate, risk-free rate, and other assumptions
4. **Run Analysis**: Click "Analyze Stock" to get the valuation

### Advanced Features

- **Popular Stocks**: Quick selection from a curated list of major stocks
- **Sensitivity Analysis**: Test how changes in assumptions affect valuation
- **Interactive Charts**: Visualize cash flow projections and value composition
- **Export Results**: Save analysis results for further review

## DCF Model Explanation

The Discounted Cash Flow model estimates a stock's intrinsic value by:

1. **Projecting Future Cash Flows**: Estimate free cash flows for 5-10 years
2. **Calculating Terminal Value**: Estimate value beyond the projection period
3. **Discounting to Present Value**: Apply WACC to bring future cash flows to present value
4. **Determining Fair Value**: Sum of present values minus net debt

### Key Assumptions

- **Growth Rates**: Expected annual growth in free cash flows
- **WACC**: Weighted Average Cost of Capital (risk-free rate + beta × market risk premium)
- **Terminal Growth**: Long-term growth rate (typically 2-3%)
- **Tax Rate**: Corporate tax rate

## File Structure

```
├── app.py                 # Flask web application
├── dcf_calculator.py      # Core DCF calculation logic
├── data_interface.py      # Stock data fetching interface
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Main HTML template
└── static/
    ├── css/
    │   └── style.css     # Custom CSS styling
    └── js/
        └── app.js        # JavaScript functionality
```

## API Endpoints

- `GET /` - Main application page
- `POST /analyze` - Run DCF analysis
- `POST /sensitivity` - Run sensitivity analysis
- `GET /stock_info/<ticker>` - Get stock information
- `GET /popular_stocks` - Get list of popular stocks

## Configuration

### Environment Variables

You can customize the application by modifying these values in `app.py`:

- `app.secret_key`: Flask secret key for sessions
- `risk_free_rate`: Default risk-free rate (default: 4%)
- `market_risk_premium`: Market risk premium (default: 6%)
- `terminal_growth_rate`: Terminal growth rate (default: 2.5%)

### Customization

- **Growth Rate Templates**: Modify default growth rates in the HTML template
- **Chart Colors**: Customize chart colors in the CSS file
- **Analysis Parameters**: Adjust default parameters in the JavaScript file

## Troubleshooting

### Common Issues

1. **"Could not fetch data for [ticker]"**
   - Ensure the ticker symbol is valid
   - Check your internet connection
   - Some tickers may not be available in the Yahoo Finance database

2. **"No FCF data available"**
   - The company may not have sufficient financial data
   - Try a different ticker or time period

3. **Charts not displaying**
   - Ensure JavaScript is enabled in your browser
   - Check browser console for errors

### Performance Tips

- Use shorter projection periods for faster analysis
- Limit sensitivity analysis to fewer data points
- Clear browser cache if experiencing issues

## Disclaimer

This tool is for educational and informational purposes only. It should not be considered as financial advice. Always consult with a qualified financial advisor before making investment decisions.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the application.

## License

This project is open source and available under the MIT License.

## Support

For questions or support, please refer to the documentation or create an issue in the project repository.
