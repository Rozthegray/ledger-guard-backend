import pandas as pd

def audit_transaction(current_amount: float, vendor: str, history_df: pd.DataFrame):
    """
    Detects anomalies. Returns a dict with status and risk level.
    """
    # Safety check for empty history
    if history_df.empty:
        return {"status": "OK", "risk_score": 0.0, "note": "No history available"}

    # Filter for this specific vendor
    vendor_history = history_df[history_df['vendor'] == vendor]
    
    if vendor_history.empty:
        return {"status": "OK", "risk_score": 0.0, "note": "New vendor"}
        
    avg_spend = vendor_history['amount'].mean()
    std_dev = vendor_history['amount'].std()
    
    # Handle case where there's only 1 previous transaction (std_dev is NaN)
    if pd.isna(std_dev):
        std_dev = avg_spend * 0.2 # Assume 20% variance allowed if we have no data
        
    # Logic: Is this transaction > 2 Standard Deviations from the mean?
    # This is statistically significant outlier detection.
    threshold = avg_spend + (2 * std_dev)
    
    if current_amount > threshold:
        return {
            "status": "ALERT", 
            "risk_score": 0.9,
            "note": f"Spike Detected. Usual: ${avg_spend:.2f}, Current: ${current_amount:.2f}"
        }
        
    return {"status": "OK", "risk_score": 0.1, "note": "Normal behavior"}