## Setup
To set up the application on your device run the following commands on your terminal:
```bash
git clone https://github.com/cagan-elden/crypto-trading-bot
pip install python-binance
pip install numpy
```
Then get your own binance-api-keys from: https://www.binance.com/

Paste them into `appsettling.json`

```json
{
    "api": {
        "api_key":    "PASTE YOUR api_key FROM BINANCE HERE!",
        "api_secret": "PASTE YOUR api_secret FROM BINANCE HERE!"
    }
}
```

## Configuration
By default, 8 altcoins are signalled. If you want to change the altcoins being scanned or add more altcoins to signal *(although it is not recommended for efficiency)* change the elements of the code block given bellow in `main.py`:

```python
# MULTI-COIN SETUP
self.symbols = [
  'XRPUSDT',
  'ADAUSDT',
  'DOGEUSDT',
  'SOLUSDT',
  'MATICUSDT',
  'DOTUSDT',
  'AVAXUSDT',
  'LINKUSDT'
]
```

By default, the trading-bot only provides signals on the command-prompt and stores the signal history in `trading_bot.log`. Even though it is not recommended for financial-safety purposes, you can create automated bullish & bearish orders in this code-block in `main.py` using `execute_buy()` and `execute_sell()` methods:

```python      
try:
  while True:
    time.sleep(1)
                
      # Print status every 60 seconds
      if time.time() - last_status > 60:
        self.print_status()
        last_status = time.time()
```

**PS:** Client is solely responsible for any trades executed using this software. Trading cryptocurrencies involves significant financial risk and past-performance or generated-signals do not guarantee future results.
