import pandas as pd
from prophet import Prophet
import logging

# Suppress Prophet's excessive logging
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logging.getLogger('prophet').setLevel(logging.WARNING)

def predict_runway(history_df: pd.DataFrame, months_to_forecast: int = 3):
    """
    Analyzes cash flow history to predict insolvency (Runway).
    
    Required Input Columns:
    - 'date': datetime objects or strings
    - 'balance': float (The account balance at the end of that day)
    """
    # 1. Data Validation
    if history_df.empty or len(history_df) < 5:
        return {
            "status": "insufficient_data", 
            "message": "Need at least 5 days of balance history to forecast."
        }
    
    # 2. Prepare Data for Prophet (Strict Format: 'ds' for date, 'y' for value)
    df = history_df.copy()
    df['ds'] = pd.to_datetime(df['date'])
    df['y'] = df['balance']
    
    # 3. Fit the Model (The "Learning" Phase)
    # We disable yearly_seasonality because startups change too fast for annual cycles to matter
    m = Prophet(yearly_seasonality=False, daily_seasonality=False)
    m.add_seasonality(name='monthly', period=30.5, fourier_order=5) # Custom monthly cycle
    m.fit(df)
    
    # 4. Predict the Future
    future = m.make_future_dataframe(periods=months_to_forecast * 30) 
    forecast = m.predict(future)
    
    # 5. Find the "Crash Date" (When balance hits $0)
    # Filter for future dates only
    last_real_date = df['ds'].max()
    future_forecast = forecast[forecast['ds'] > last_real_date]
    
    # Find rows where prediction ('yhat') is negative
    insolvency = future_forecast[future_forecast['yhat'] < 0]
    
    if not insolvency.empty:
        burn_date = insolvency.iloc[0]['ds'].strftime('%Y-%m-%d')
        return {
            "status": "DANGER", 
            "runway_end_date": burn_date,
            "message": f"Projected insolvency date: {burn_date}"
        }
    
    # If we survive the forecast window
    min_balance = future_forecast['yhat'].min()
    return {
        "status": "SAFE", 
        "lowest_projected_balance": round(min_balance, 2),
        "message": f"Sustainable for at least {months_to_forecast} months."
    }
    