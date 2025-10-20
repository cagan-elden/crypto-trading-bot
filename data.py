import binance
import pandas as pd
import time

def get_historical_klines(client, symbol: str, interval: str, start_str: str, limit: int = 1000):
    raw = client.get_historical_klines(symbol, interval, start_str=start_str, limit=limit)
    df = pd.DataFrame(raw, columns=[
        'open_time','open','high','low','close','volume',
        'close_time','quote_asset_volume','num_trades',
        'taker_buy_base','taker_buy_quote','ignore'
    ])
    # convert numeric columns
    for col in ['open','high','low','close','volume']:
        df[col] = df[col].astype(float)
    # convert timestamps to datetime
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    df.set_index('open_time', inplace=True)
    return df

def get_latest_price(client, symbol: str):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

def get_account_balances(client):
    account = client.get_account()
    balances = {}
    for b in account['balances']:
        free = float(b['free'])
        locked = float(b['locked'])
        balances[b['asset']] = {'free': free, 'locked': locked, 'total': free+locked}
    return balances

def get_klines_batch(client, symbol, interval, start_str, end_str=None, limit=1000, sleep_sec=0.5):
    all_data = []
    df = client.get_historical_klines(client, symbol, interval, start_str, limit)
    all_data.append(df)
    
    while True:
        last_time = df.index[-1]
        if end_str and last_time >= pd.to_datetime(end_str):
            break
        time.sleep(sleep_sec)
        df = client.get_historical_klines(client, symbol, interval, start_str=str(last_time + pd.Timedelta(seconds=1)), limit=limit)
        if df.empty:
            break
        all_data.append(df)
    result = pd.concat(all_data)
    result = result[~result.index.duplicated(keep='first')]
    return result