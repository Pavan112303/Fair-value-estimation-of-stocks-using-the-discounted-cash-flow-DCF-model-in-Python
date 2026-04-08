import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class DCFCalculator:
    """
    Discounted Cash Flow (DCF) Model for Stock Valuation
    
    This class implements a comprehensive DCF model that calculates the fair value
    of a stock based on projected cash flows, growth rates, and discount rates.
    """
    
    def __init__(self):
        self.risk_free_rate = 0.04  # 4% risk-free rate (can be updated)
        self.market_risk_premium = 0.06  # 6% market risk premium
        self.terminal_growth_rate = 0.025  # 2.5% terminal growth rate (US default)
        self.terminal_growth_rates = {
            'US': 0.025,  # 2.5% for US stocks
            'IN': 0.055,  # 5.5% for Indian stocks (higher GDP growth)
            'EU': 0.020,  # 2.0% for European stocks
            'CN': 0.045,  # 4.5% for Chinese stocks
            'default': 0.025
        }
        self.use_mid_year_convention = True  # Use mid-year discounting for accuracy
        
    def calculate_wacc(self, beta: float, debt_to_equity: float, 
                      tax_rate: float, cost_of_debt: float = None) -> float:
        """
        Calculate Weighted Average Cost of Capital (WACC)
        
        Args:
            beta: Stock's beta coefficient
            debt_to_equity: Debt to equity ratio
            tax_rate: Corporate tax rate
            cost_of_debt: Cost of debt (if None, estimated as risk_free_rate + 2%)
            
        Returns:
            WACC as decimal (e.g., 0.10 for 10%)
        """
        # Input validation
        if beta < 0 or beta > 5:
            raise ValueError(f"Beta {beta} is outside reasonable range (0-5). Please verify the data.")
        if debt_to_equity < 0:
            raise ValueError(f"Debt-to-equity ratio cannot be negative: {debt_to_equity}")
        if tax_rate < 0 or tax_rate > 1:
            raise ValueError(f"Tax rate must be between 0 and 1, got: {tax_rate}")
        
        if cost_of_debt is None:
            cost_of_debt = self.risk_free_rate + 0.02
            
        # Cost of equity using CAPM
        cost_of_equity = self.risk_free_rate + beta * self.market_risk_premium
        
        # Calculate weights
        total_value = 1 + debt_to_equity
        weight_equity = 1 / total_value
        weight_debt = debt_to_equity / total_value
        
        # WACC formula
        wacc = (weight_equity * cost_of_equity + 
                weight_debt * cost_of_debt * (1 - tax_rate))
        
        return wacc
    
    def project_cash_flows(self, current_fcf: float, growth_rates: List[float], 
                          years: int = 5) -> pd.DataFrame:
        """
        Project future free cash flows
        
        Args:
            current_fcf: Current year free cash flow
            growth_rates: List of growth rates for each year
            years: Number of projection years
            
        Returns:
            DataFrame with projected cash flows
        """
        # Validate FCF
        if current_fcf <= 0:
            raise ValueError(f"Current FCF must be positive for DCF valuation. Got: {current_fcf:,.0f}. Consider using alternative valuation methods for unprofitable companies.")
        
        # Validate growth rates
        for i, rate in enumerate(growth_rates):
            if rate < -0.5 or rate > 1.0:
                raise ValueError(f"Growth rate {rate*100:.1f}% in year {i+1} is outside reasonable range (-50% to 100%)")
        
        if len(growth_rates) != years:
            # If fewer growth rates provided, use the last rate for remaining years
            print(f"Warning: Only {len(growth_rates)} growth rates provided for {years} years. Extending with last rate.")
            growth_rates = growth_rates + [growth_rates[-1]] * (years - len(growth_rates))
        
        projections = []
        fcf = current_fcf
        
        for year in range(1, years + 1):
            growth_rate = growth_rates[year - 1]
            fcf = fcf * (1 + growth_rate)
            projections.append({
                'Year': year,
                'Growth_Rate': growth_rate,
                'Free_Cash_Flow': fcf
            })
        
        return pd.DataFrame(projections)
    
    def calculate_terminal_value(self, final_fcf: float, wacc: float, 
                               terminal_growth: float = None, market: str = 'US') -> float:
        """
        Calculate terminal value using Gordon Growth Model
        
        Args:
            final_fcf: Free cash flow in the final projection year
            wacc: Weighted average cost of capital
            terminal_growth: Terminal growth rate (defaults to market-specific rate)
            market: Market region (US, IN, EU, CN) for appropriate terminal growth
            
        Returns:
            Terminal value
        """
        if terminal_growth is None:
            terminal_growth = self.terminal_growth_rates.get(market, self.terminal_growth_rate)
        
        # Ensure terminal growth is always at least 1.5% below WACC for model stability
        # This handles low-beta defensive stocks in emerging markets
        min_spread = 0.015  # 1.5% minimum spread
        max_allowed_growth = wacc - min_spread
        
        if terminal_growth >= max_allowed_growth:
            original_growth = terminal_growth
            terminal_growth = max(max_allowed_growth, 0.02)  # Floor at 2%
            print(f"Warning: Terminal growth adjusted from {original_growth*100:.2f}% to {terminal_growth*100:.2f}% "
                  f"due to low WACC ({wacc*100:.2f}%). Using conservative rate.")
        
        if wacc <= terminal_growth:
            raise ValueError(f"WACC ({wacc*100:.2f}%) must be greater than terminal growth rate ({terminal_growth*100:.2f}%). "
                           f"This stock may have unrealistic inputs or be too defensive for DCF modeling.")
            
        terminal_value = (final_fcf * (1 + terminal_growth)) / (wacc - terminal_growth)
        return terminal_value
    
    def calculate_enterprise_value(self, projected_fcf: pd.DataFrame, 
                                 terminal_value: float, wacc: float) -> Dict:
        """
        Calculate enterprise value and equity value
        
        Args:
            projected_fcf: DataFrame with projected cash flows
            terminal_value: Terminal value
            wacc: Weighted average cost of capital
            
        Returns:
            Dictionary with valuation metrics
        """
        # Discount projected cash flows using mid-year convention for accuracy
        if self.use_mid_year_convention:
            # Mid-year convention: cash flows occur halfway through the year
            projected_fcf['Discount_Factor'] = 1 / (1 + wacc) ** (projected_fcf['Year'] - 0.5)
        else:
            # Year-end convention: cash flows occur at end of year
            projected_fcf['Discount_Factor'] = 1 / (1 + wacc) ** projected_fcf['Year']
            
        projected_fcf['Present_Value'] = (projected_fcf['Free_Cash_Flow'] * 
                                        projected_fcf['Discount_Factor'])
        
        # Sum of present values of projected cash flows
        pv_projected_fcf = projected_fcf['Present_Value'].sum()
        
        # Present value of terminal value
        final_year = projected_fcf['Year'].max()
        if self.use_mid_year_convention:
            pv_terminal_value = terminal_value / (1 + wacc) ** (final_year - 0.5)
        else:
            pv_terminal_value = terminal_value / (1 + wacc) ** final_year
        
        # Enterprise value
        enterprise_value = pv_projected_fcf + pv_terminal_value
        
        return {
            'pv_projected_fcf': pv_projected_fcf,
            'pv_terminal_value': pv_terminal_value,
            'enterprise_value': enterprise_value,
            'projected_fcf': projected_fcf
        }
    
    def calculate_fair_value(self, current_fcf: float, growth_rates: List[float],
                           beta: float, debt_to_equity: float, tax_rate: float,
                           shares_outstanding: float, net_debt: float = 0,
                           years: int = 5, wacc: Optional[float] = None,
                           market: str = 'US', current_price: float = 0) -> Dict:
        """
        Complete DCF valuation calculation
        
        Args:
            current_fcf: Current year free cash flow
            growth_rates: List of growth rates for projection years
            beta: Stock's beta coefficient
            debt_to_equity: Debt to equity ratio
            tax_rate: Corporate tax rate
            shares_outstanding: Number of shares outstanding
            net_debt: Net debt (debt - cash)
            years: Number of projection years
            
        Returns:
            Dictionary with complete valuation results
        """
        # Calculate WACC (allow override for sensitivity analysis)
        if wacc is None:
            wacc = self.calculate_wacc(beta, debt_to_equity, tax_rate)
        
        # Project cash flows
        projected_fcf = self.project_cash_flows(current_fcf, growth_rates, years)
        
        # Calculate terminal value with market-specific growth rate
        final_fcf = projected_fcf.iloc[-1]['Free_Cash_Flow']
        terminal_value = self.calculate_terminal_value(final_fcf, wacc, market=market)
        
        # Calculate enterprise value
        ev_results = self.calculate_enterprise_value(projected_fcf, terminal_value, wacc)
        
        # Calculate equity value
        equity_value = ev_results['enterprise_value'] - net_debt
        
        # Calculate fair value per share
        fair_value_per_share = equity_value / shares_outstanding
        
        # Get the actual terminal growth used (may be adjusted)
        terminal_growth_used = self.terminal_growth_rates.get(market, self.terminal_growth_rate)
        min_spread = 0.015
        max_allowed_growth = wacc - min_spread
        if terminal_growth_used >= max_allowed_growth:
            terminal_growth_used = max(max_allowed_growth, 0.02)
        
        # Calculate key metrics
        final_year_fcf = projected_fcf.iloc[-1]['Free_Cash_Flow']
        fcf_yield = final_year_fcf / ev_results['enterprise_value'] if ev_results['enterprise_value'] > 0 else 0
        
        # Calculate margin of safety and valuation multiples
        margin_of_safety = 0
        implied_pe = 0
        if current_price > 0:
            margin_of_safety = ((fair_value_per_share - current_price) / fair_value_per_share) * 100
            if current_fcf > 0:
                implied_pe = (equity_value / current_fcf)
        
        # Sanity check warnings
        warnings = []
        if implied_pe > 100:
            warnings.append(f"Very high implied P/E ratio ({implied_pe:.1f}x) - valuation may be unrealistic")
        if margin_of_safety < -80:
            warnings.append(f"Stock is severely overvalued (fair value {margin_of_safety:.1f}% below price)")
        if fcf_yield < 0.01:
            warnings.append("Very low FCF yield - company may be overvalued or in high growth phase")
        
        return {
            'wacc': wacc,
            'terminal_value': terminal_value,
            'terminal_growth_rate': terminal_growth_used,
            'enterprise_value': ev_results['enterprise_value'],
            'equity_value': equity_value,
            'fair_value_per_share': fair_value_per_share,
            'projected_fcf': projected_fcf,
            'pv_projected_fcf': ev_results['pv_projected_fcf'],
            'pv_terminal_value': ev_results['pv_terminal_value'],
            'final_year_fcf': final_year_fcf,
            'fcf_yield': fcf_yield,
            'net_debt': net_debt,
            'shares_outstanding': shares_outstanding,
            'margin_of_safety': margin_of_safety,
            'implied_pe': implied_pe,
            'warnings': warnings,
            'market': market
        }
    
    def sensitivity_analysis(self, base_params: Dict, 
                           wacc_range: Tuple[float, float] = (0.08, 0.15),
                           growth_range: Tuple[float, float] = (0.02, 0.08),
                           steps: int = 5) -> pd.DataFrame:
        """
        Perform sensitivity analysis on key parameters
        
        Args:
            base_params: Base case parameters
            wacc_range: Range of WACC values to test
            growth_range: Range of growth rates to test
            steps: Number of steps in each dimension
            
        Returns:
            DataFrame with sensitivity analysis results
        """
        wacc_values = np.linspace(wacc_range[0], wacc_range[1], steps)
        growth_values = np.linspace(growth_range[0], growth_range[1], steps)
        
        results = []
        
        for wacc in wacc_values:
            for growth in growth_values:
                # Create modified growth rates
                modified_growth_rates = [growth] * len(base_params['growth_rates'])
                
                # Calculate valuation with modified parameters
                valuation = self.calculate_fair_value(
                    current_fcf=base_params['current_fcf'],
                    growth_rates=modified_growth_rates,
                    beta=base_params['beta'],
                    debt_to_equity=base_params['debt_to_equity'],
                    tax_rate=base_params['tax_rate'],
                    shares_outstanding=base_params['shares_outstanding'],
                    net_debt=base_params.get('net_debt', 0),
                    years=len(modified_growth_rates),
                    wacc=wacc,
                    market=base_params.get('market', 'US'),
                    current_price=base_params.get('current_price', 0)
                )
                
                results.append({
                    'WACC': wacc,
                    'Growth_Rate': growth,
                    'Fair_Value': valuation['fair_value_per_share'],
                    'Enterprise_Value': valuation['enterprise_value']
                })
        
        return pd.DataFrame(results)
    
    def monte_carlo_simulation(self, base_params: Dict, iterations: int = 10000) -> Dict:
        """
        Run Monte Carlo simulation for valuation uncertainty analysis
        
        Args:
            base_params: Base case parameters (current_fcf, growth_rates, beta, debt_to_equity, tax_rate, shares_outstanding, net_debt)
            iterations: Number of simulation iterations
            
        Returns:
            Dictionary with statistical results and distribution
        """
        # Dynamic volatility based on beta and company characteristics
        beta = base_params.get('beta', 1.0)
        
        # Higher beta = more volatile company = wider distributions
        fcf_volatility = min(0.15 + (beta - 1.0) * 0.05, 0.30)  # 15-30% based on beta
        growth_volatility = min(0.20 + (beta - 1.0) * 0.08, 0.40)  # 20-40% based on beta
        beta_volatility = 0.10  # Keep beta volatility relatively stable
        
        results = []
        
        for _ in range(iterations):
            try:
                # Vary FCF with dynamic volatility
                fcf_var = base_params['current_fcf'] * np.random.normal(1.0, fcf_volatility)
                
                # Vary growth rates with dynamic volatility
                growth_var = [max(0, g * np.random.normal(1.0, growth_volatility)) for g in base_params['growth_rates']]
                
                # Vary WACC components
                beta_var = max(0.1, base_params['beta'] * np.random.normal(1.0, beta_volatility))
                debt_to_equity_var = max(0, base_params['debt_to_equity'] * np.random.normal(1.0, 0.15))
                
                # Calculate WACC with variations
                wacc_var = self.calculate_wacc(
                    beta=beta_var,
                    debt_to_equity=debt_to_equity_var,
                    tax_rate=base_params['tax_rate']
                )
                
                # Calculate valuation (pass market if available)
                result = self.calculate_fair_value(
                    current_fcf=fcf_var,
                    growth_rates=growth_var,
                    beta=beta_var,
                    debt_to_equity=debt_to_equity_var,
                    tax_rate=base_params['tax_rate'],
                    shares_outstanding=base_params['shares_outstanding'],
                    net_debt=base_params.get('net_debt', 0),
                    wacc=wacc_var,
                    years=len(growth_var),
                    market=base_params.get('market', 'US'),
                    current_price=base_params.get('current_price', 0)
                )
                results.append(result['fair_value_per_share'])
            except:
                continue
        
        if not results:
            return {'error': 'Monte Carlo simulation failed'}
        
        results_array = np.array(results)
        
        return {
            'mean': float(np.mean(results_array)),
            'median': float(np.median(results_array)),
            'std_dev': float(np.std(results_array)),
            'percentile_10': float(np.percentile(results_array, 10)),
            'percentile_25': float(np.percentile(results_array, 25)),
            'percentile_75': float(np.percentile(results_array, 75)),
            'percentile_90': float(np.percentile(results_array, 90)),
            'min': float(np.min(results_array)),
            'max': float(np.max(results_array)),
            'distribution_sample': [float(x) for x in results_array[:100]],  # Return sample for chart
            'fcf_volatility': fcf_volatility,
            'growth_volatility': growth_volatility
        }
    
    def calculate_ddm(self, current_dividend: float, dividend_growth_rate: float, 
                      required_return: float, years: int = 10) -> Dict:
        """
        Calculate fair value using Gordon Growth Model (Dividend Discount Model)
        
        Args:
            current_dividend: Current annual dividend per share
            dividend_growth_rate: Long-term dividend growth rate
            required_return: Required rate of return (discount rate)
            years: Number of projection years
            
        Returns:
            Dictionary with DDM valuation results
        """
        if required_return <= dividend_growth_rate:
            return {'error': 'Required return must be greater than growth rate'}
        
        # Calculate present value of projected dividends
        pv_dividends = 0
        projected_dividends = []
        
        for year in range(1, years + 1):
            future_dividend = current_dividend * ((1 + dividend_growth_rate) ** year)
            discount_factor = 1 / ((1 + required_return) ** year)
            pv = future_dividend * discount_factor
            pv_dividends += pv
            projected_dividends.append({
                'Year': year,
                'Projected_Dividend': future_dividend,
                'Discount_Factor': discount_factor,
                'Present_Value': pv
            })
        
        # Calculate terminal value using Gordon Growth Model
        terminal_dividend = current_dividend * ((1 + dividend_growth_rate) ** years)
        terminal_value = (terminal_dividend * (1 + dividend_growth_rate)) / (required_return - dividend_growth_rate)
        pv_terminal_value = terminal_value / ((1 + required_return) ** years)
        
        # Fair value per share
        fair_value = pv_dividends + pv_terminal_value
        
        return {
            'fair_value_per_share': fair_value,
            'method': 'DDM',
            'pv_dividends': pv_dividends,
            'pv_terminal_value': pv_terminal_value,
            'terminal_value': terminal_value,
            'projected_dividends': projected_dividends,
            'required_return': required_return,
            'dividend_growth_rate': dividend_growth_rate,
            'current_dividend': current_dividend
        }
    
    def calculate_risk_metrics(self, base_params: Dict, valuation: Dict) -> Dict:
        """
        Calculate risk metrics for valuation
        
        Args:
            base_params: Base parameters used in valuation
            valuation: Valuation results
            
        Returns:
            Dictionary with risk metrics and scores
        """
        fair_value = valuation.get('fair_value_per_share', 0)
        wacc = valuation.get('wacc', 0.1)
        fcf_yield = valuation.get('fcf_yield', 0)
        beta = base_params.get('beta', 1.0)
        debt_to_equity = base_params.get('debt_to_equity', 0)
        
        # Calculate risk score (0-100)
        # Higher beta = higher risk
        beta_risk = min(100, (beta / 2.0) * 100) if beta > 0 else 0
        
        # High debt-to-equity = higher risk
        leverage_risk = min(100, (debt_to_equity / 2.0) * 100) if debt_to_equity >= 0 else 0
        
        # High WACC = higher risk
        wacc_risk = min(100, (wacc / 0.2) * 100) if wacc > 0 else 0
        
        # Low FCF yield = higher risk
        fcf_risk = max(0, 100 - (fcf_yield * 1000)) if fcf_yield > 0 else 100
        
        # Overall risk score (weighted average)
        overall_risk_score = (beta_risk * 0.3 + leverage_risk * 0.25 + wacc_risk * 0.25 + fcf_risk * 0.2)
        
        # Risk level categorization
        if overall_risk_score < 30:
            risk_level = 'Low'
        elif overall_risk_score < 50:
            risk_level = 'Medium'
        elif overall_risk_score < 70:
            risk_level = 'High'
        else:
            risk_level = 'Very High'
        
        return {
            'overall_risk_score': float(overall_risk_score),
            'risk_level': risk_level,
            'beta_risk': float(beta_risk),
            'leverage_risk': float(leverage_risk),
            'wacc_risk': float(wacc_risk),
            'fcf_risk': float(fcf_risk),
            'beta': float(beta),
            'debt_to_equity': float(debt_to_equity),
            'wacc': float(wacc),
            'fcf_yield': float(fcf_yield)
        }

