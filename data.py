import binance

def get_old_klines(client, symbol, interval, timestamp):
    klines = client.get_historical_klines(symbol, interval, timestamp)
    return klines