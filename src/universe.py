"""Nifty 50 universe - static list, Yahoo suffix .NS"""
# ponytail: static list, live constituent changes are post-MVP
NIFTY50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "BAJFINANCE.NS",
    "WIPRO.NS", "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS",
    "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
    "TECHM.NS", "INDUSINDBK.NS", "ADANIENT.NS", "ADANIPORTS.NS", "BAJAJFINSV.NS",
    "COALINDIA.NS", "HDFCLIFE.NS", "SBILIFE.NS", "BRITANNIA.NS", "EICHERMOT.NS",
    "GRASIM.NS", "HEROMOTOCO.NS", "CIPLA.NS", "DRREDDY.NS", "BPCL.NS",
    "APOLLOHOSP.NS", "DIVISLAB.NS", "BAJAJ-AUTO.NS", "TATACONSUM.NS", "TATAMOTORS.NS",
    "ONGC.NS", "HINDALCO.NS", "LTIM.NS", "M&M.NS", "SHRIRAMFIN.NS",
]

# Smaller subset for fast CI/backtest demo (15 large caps covering sectors)
NIFTY15 = NIFTY50[:15]

# ponytail: manual sector map, exhaustive list unnecessary — same-sector pruning only
SECTORS = {
    "Banks": ["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","KOTAKBANK.NS","AXISBANK.NS","INDUSINDBK.NS"],
    "IT": ["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS","LTIM.NS"],
    "Auto": ["MARUTI.NS","M&M.NS","TATAMOTORS.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS","EICHERMOT.NS"],
    "Pharma": ["SUNPHARMA.NS","CIPLA.NS","DRREDDY.NS","DIVISLAB.NS","APOLLOHOSP.NS"],
    "Energy": ["RELIANCE.NS","ONGC.NS","BPCL.NS","NTPC.NS","POWERGRID.NS","COALINDIA.NS"],
    "Other": ["HINDUNILVR.NS","BHARTIARTL.NS","ITC.NS","LT.NS","ASIANPAINT.NS","BAJFINANCE.NS","TITAN.NS","ULTRACEMCO.NS","NESTLEIND.NS","JSWSTEEL.NS","TATASTEEL.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","HDFCLIFE.NS","SBILIFE.NS","BRITANNIA.NS","GRASIM.NS","BAJAJ-AUTO.NS","TATACONSUM.NS","HINDALCO.NS","SHRIRAMFIN.NS"],
}

def same_sector_pairs(tickers: list[str]) -> list[tuple[str,str]]:
    sset = set(tickers)
    pairs = []
    for members in SECTORS.values():
        m = [t for t in members if t in sset]
        for i in range(len(m)):
            for j in range(i+1, len(m)):
                pairs.append((m[i], m[j]))
    return pairs
