from binance import Client
import json

# API connection
with open('appsettling.json', 'r') as appsettling:
    api_data = json.load(appsettling)

api_key    = api_data["api"]["api_key"]
api_secret = api_data["api"]["api_secret"]

client  = Client(api_key, api_secret)
account = client.get_account()

"""
# Get account portfolio
balances = account['balances']

assets = [
    {
        'asset' : i['asset'],
        'free'  : float(i['free']),
        'locked': float(i['locked']),
        'amount': float(i['free']) + float(i['locked'])
    }
    for i in balances
    if float(i['free']) > 0 or float(i['locked'])
]

total_portfolio_usdt = 0 + assets[0]['amount'] # 0 + USDT
for i in assets:
    if i['asset'] == 'USDT':
        continue
    print(i['asset'])
    current_price = client.get_symbol_ticker(symbol=i['asset']+'USDT')
    total_portfolio_usdt += float(current_price['price'])*i['amount']
"""

# Get all coin prices now
coin_tickers = client.get_all_tickers()