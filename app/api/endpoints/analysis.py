from fastapi import APIRouter
from typing import List
import pandas as pd
from prophet import Prophet
from app.schemas.transaction import TransactionOutput

router = APIRouter()

@router.post("/forecast")
async def generate_forecast(history: List[TransactionOutput]):
    # 1. Convert to DataFrame
    df = pd.DataFrame([t.dict() for t in history])
    
    if df.empty: return {"error": "No data"}

    # 2. Prepare Data for Prophet (Daily Cumulative Balance)
    df['date'] = pd.to_datetime(df['date'])
    # We need CUMULATIVE sum to show "Runway", not just daily spending
    # Sort by date
    df = df.sort_values('date')
    # Calculate daily net change
    daily_change = df.groupby('date')['amount'].sum().reset_index()
    # Calculate running balance (assuming starting at 0 for relative change, or use first row)
    daily_change['balance'] = daily_change['amount'].cumsum()
    
    # Rename for Prophet
    prophet_df = daily_change.rename(columns={'date': 'ds', 'balance': 'y'})

    # 3. Train Prophet
    m = Prophet(yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False)
    m.fit(prophet_df)
    
    # 4. Predict Future (90 Days)
    future = m.make_future_dataframe(periods=90)
    forecast = m.predict(future)
    
    # 5. CALCULATE METRICS (The "CFO" Logic)
    
    # Get the last actual balance
    current_balance = prophet_df['y'].iloc[-1]
    
    # Get the predicted balance 30 days from now
    future_30_days = forecast.iloc[-60]['yhat'] # Approx 30 days out
    
    # Monthly Burn Rate (How much we lose per month)
    # If balance goes UP, burn rate is 0 (Profit)
    burn_rate = current_balance - future_30_days
    
    # Runway (Days until $0)
    runway_days = "Infinite"
    zero_date = "Never"
    
    if burn_rate > 0:
        # Avoid division by zero
        daily_burn = burn_rate / 30
        days_left = int(current_balance / daily_burn)
        runway_days = str(days_left)
        
        # Calculate exact date
        last_date = df['date'].max()
        zero_date_obj = last_date + pd.Timedelta(days=days_left)
        zero_date = zero_date_obj.strftime('%Y-%m-%d')

    # 6. Format Data for Chart
    chart_data = forecast[['ds', 'yhat']].tail(90).to_dict(orient="records")
    for d in chart_data:
        d['ds'] = d['ds'].strftime('%Y-%m-%d')

    return {
        "metrics": {
            "current_balance": round(current_balance, 2),
            "monthly_burn_rate": round(burn_rate, 2),
            "runway_days": runway_days,
            "zero_balance_date": zero_date
        },
        "chart_data": chart_data
    }