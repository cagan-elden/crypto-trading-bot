import json
import time
from collections import deque
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance import ThreadedWebsocketManager
import logging
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class MultiCoinTradingBot:
    def __init__(self, config_file='appsettling.json'):
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.client = Client(config['api']['api_key'], config['api']['api_secret'])
        self.twm = ThreadedWebsocketManager(api_key=config['api']['api_key'], api_secret=config['api']['api_secret'])
        
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
        
        # Settings
        self.lookback = 100
        self.trade_quantity = 0.015  # 1.5% per coin (can hold multiple)
        self.max_positions = 3  # Maximum simultaneous positions
        
        # Strategy params
        self.rsi_period = 14
        self.rsi_oversold = 35  # More aggressive
        self.rsi_overbought = 65
        self.stop_loss_pct = 0.025  # 2.5%
        self.take_profit_pct = 0.05  # 5%
        
        # Data storage for each coin
        self.data = {}
        for symbol in self.symbols:
            self.data[symbol] = {
                'closes': deque(maxlen=self.lookback),
                'volumes': deque(maxlen=self.lookback),
                'current_price': 0,
                'last_check': 0,
                'in_position': False,
                'entry_price': 0,
                'quantity': 0
            }
        
        # Load initial data for all coins
        self._init_all_data()
        
        logging.info(f"Multi-coin bot initialized for {len(self.symbols)} pairs")
        logging.info(f"Max positions: {self.max_positions}")
    
    def _init_all_data(self):
        """Load initial data for all trading pairs"""
        for symbol in self.symbols:
            try:
                klines = self.client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1MINUTE, limit=self.lookback)
                for k in klines:
                    self.data[symbol]['closes'].append(float(k[4]))
                    self.data[symbol]['volumes'].append(float(k[5]))
                self.data[symbol]['current_price'] = self.data[symbol]['closes'][-1]
                logging.info(f"Loaded {symbol}: {len(self.data[symbol]['closes'])} candles")
            except Exception as e:
                logging.error(f"Failed to load {symbol}: {e}")
    
    def get_active_positions(self):
        """Count current open positions"""
        return sum(1 for s in self.symbols if self.data[s]['in_position'])
    
    def calculate_rsi_fast(self, closes):
        """Fast RSI calculation"""
        if len(closes) < self.rsi_period + 1:
            return 50
        
        prices = np.array(list(closes)[-(self.rsi_period+1):])
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_ema_fast(self, closes, period):
        """Fast EMA calculation"""
        if len(closes) < period:
            return np.mean(list(closes))
        
        prices = np.array(list(closes)[-period:])
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_macd_fast(self, closes):
        """Fast MACD calculation"""
        if len(closes) < 26:
            return 0, 0
        
        ema12 = self.calculate_ema_fast(closes, 12)
        ema26 = self.calculate_ema_fast(closes, 26)
        macd = ema12 - ema26
        signal = macd * 0.85
        
        return macd, signal
    
    def analyze_symbol(self, symbol):
        """Analyze a specific symbol"""
        coin_data = self.data[symbol]
        closes = coin_data['closes']
        volumes = coin_data['volumes']
        
        if len(closes) < 30:
            return None, 0
        
        # Calculate indicators
        rsi = self.calculate_rsi_fast(closes)
        macd, signal = self.calculate_macd_fast(closes)
        
        # Volume analysis
        recent_vol = np.mean(list(volumes)[-5:])
        avg_vol = np.mean(list(volumes)[-20:]) if len(volumes) >= 20 else recent_vol
        volume_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
        
        # Price momentum
        price_change = (coin_data['current_price'] - closes[-10]) / closes[-10] if len(closes) >= 10 else 0
        
        # Calculate signal strength (0-100)
        signal_strength = 0
        trade_signal = None
        
        if not coin_data['in_position']:
            # BUY scoring
            if rsi < self.rsi_oversold:
                signal_strength += 40
            if macd > signal:
                signal_strength += 30
            if volume_ratio > 1.1:
                signal_strength += 20
            if price_change > -0.01:
                signal_strength += 10
            
            if signal_strength >= 60:  # Need 60+ points to buy
                trade_signal = 'BUY'
        
        else:
            # SELL conditions
            if rsi > self.rsi_overbought and macd < signal:
                trade_signal = 'SELL'
        
        return trade_signal, signal_strength
    
    def check_exit(self, symbol):
        """Check exit conditions for a symbol"""
        coin_data = self.data[symbol]
        if not coin_data['in_position']:
            return False
        
        current_price = coin_data['current_price']
        entry_price = coin_data['entry_price']
        change = (current_price - entry_price) / entry_price
        
        if change <= -self.stop_loss_pct:
            logging.warning(f"[{symbol}] STOP LOSS: {change*100:.2f}%")
            return True
        
        if change >= self.take_profit_pct:
            logging.info(f"[{symbol}] TAKE PROFIT: {change*100:.2f}%")
            return True
        
        return False
    
    def get_balance(self, asset='USDT'):
        """Get balance"""
        try:
            balance = self.client.get_asset_balance(asset=asset)
            return float(balance['free'])
        except:
            return 0
    
    def execute_buy(self, symbol):
        """Execute buy for a symbol"""
        if self.get_active_positions() >= self.max_positions:
            logging.info(f"[{symbol}] Skipped - Max positions reached ({self.max_positions})")
            return False
        
        try:
            balance = self.get_balance('USDT')
            if balance < 15:
                logging.warning(f"[{symbol}] Insufficient balance")
                return False
            
            amount = balance * self.trade_quantity
            current_price = self.data[symbol]['current_price']
            
            # Get symbol info for precision
            info = self.client.get_symbol_info(symbol)
            step_size = float([f['stepSize'] for f in info['filters'] if f['filterType'] == 'LOT_SIZE'][0])
            precision = len(str(step_size).rstrip('0').split('.')[-1])
            
            qty = round(amount / current_price, precision)
            
            order = self.client.order_market(symbol=symbol, side='BUY', quantity=qty)
            
            self.data[symbol]['in_position'] = True
            self.data[symbol]['entry_price'] = current_price
            self.data[symbol]['quantity'] = qty
            
            logging.info(f"[{symbol}] BUY {qty} @ {current_price:.4f} | Positions: {self.get_active_positions()}/{self.max_positions}")
            return True
            
        except Exception as e:
            logging.error(f"[{symbol}] Buy error: {e}")
            return False
    
    def execute_sell(self, symbol):
        """Execute sell for a symbol"""
        try:
            coin_data = self.data[symbol]
            qty = coin_data['quantity']
            
            if qty <= 0:
                return False
            
            order = self.client.order_market(symbol=symbol, side='SELL', quantity=qty)
            
            current_price = coin_data['current_price']
            profit = ((current_price - coin_data['entry_price']) / coin_data['entry_price']) * 100
            
            self.data[symbol]['in_position'] = False
            self.data[symbol]['entry_price'] = 0
            self.data[symbol]['quantity'] = 0
            
            logging.info(f"[{symbol}] SELL {qty} @ {current_price:.4f} | P/L: {profit:.2f}% | Positions: {self.get_active_positions()}/{self.max_positions}")
            return True
            
        except Exception as e:
            logging.error(f"[{symbol}] Sell error: {e}")
            return False
    
    def handle_kline(self, msg):
        """WebSocket handler for kline data"""
        if msg['e'] == 'error':
            return
        
        symbol = msg['s']
        kline = msg['k']
        
        if kline['x']:  # Closed candle
            self.data[symbol]['closes'].append(float(kline['c']))
            self.data[symbol]['volumes'].append(float(kline['v']))
        
        self.data[symbol]['current_price'] = float(kline['c'])
        
        # Check exit first
        if self.check_exit(symbol):
            self.execute_sell(symbol)
            return
        
        # Throttle analysis (every 3 seconds per coin)
        now = time.time()
        if now - self.data[symbol]['last_check'] < 3:
            return
        
        self.data[symbol]['last_check'] = now
        
        # Analyze and trade
        signal, strength = self.analyze_symbol(symbol)
        
        if signal == 'BUY':
            logging.info(f"[{symbol}] BUY SIGNAL (strength: {strength}) | Price: {self.data[symbol]['current_price']:.4f}")
            self.execute_buy(symbol)
        elif signal == 'SELL':
            logging.info(f"[{symbol}] SELL SIGNAL")
            self.execute_sell(symbol)
    
    def print_status(self):
        """Print current status of all coins"""
        active = self.get_active_positions()
        logging.info(f"\n{'='*60}")
        logging.info(f"PORTFOLIO STATUS | Active: {active}/{self.max_positions}")
        logging.info(f"{'='*60}")
        
        for symbol in self.symbols:
            coin = self.data[symbol]
            status = "IN POSITION" if coin['in_position'] else "WATCHING"
            price = coin['current_price']
            
            if coin['in_position']:
                pnl = ((price - coin['entry_price']) / coin['entry_price']) * 100
                logging.info(f"{symbol:12} | {status:12} | Price: {price:8.4f} | P/L: {pnl:+6.2f}%")
            else:
                logging.info(f"{symbol:12} | {status:12} | Price: {price:8.4f}")
        
        logging.info(f"{'='*60}\n")
    
    def run(self):
        """Start multi-coin trading"""
        logging.info(">> Starting MULTI-COIN bot with WebSocket...")
        
        self.twm.start()
        
        # Start WebSocket for each symbol
        for symbol in self.symbols:
            self.twm.start_kline_socket(
                callback=self.handle_kline,
                symbol=symbol,
                interval='1m'
            )
            logging.info(f">> Streaming {symbol}")
        
        logging.info(f"\n>> Monitoring {len(self.symbols)} coins in real-time!\n")
        
        # Status update every 60 seconds
        last_status = time.time()
        
        try:
            while True:
                time.sleep(1)
                
                # Print status every 60 seconds
                if time.time() - last_status > 60:
                    self.print_status()
                    last_status = time.time()
                    
        except KeyboardInterrupt:
            logging.info("\nStopping bot...")
            self.twm.stop()

if __name__ == "__main__":
    bot = MultiCoinTradingBot()
    bot.run()