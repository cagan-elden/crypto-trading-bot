import pandas as pd
import numpy as np
import math

# math operators
def sigma_func(values):
    return sum(values)

def sma(prices, period):
    return prices.rolling(window=period).mean()

# indicators
def ema(prices, period):
    val = prices.ewm(span=period, adjust=False).mean()
    return val

def macd(prices, fast=12, slow=26, signal=9):
    macd_val = ema(prices, fast) - ema(prices, slow)
    signal_val = ema(macd_val, signal)
    histogram = macd_val - signal_val

    return {
        'macd': macd_val,
        'signal': signal_val,
        'histogram': histogram
    }

def rsi(prices, period=14):
    delta = prices.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = ema(pd.Series(gain), period)
    avg_loss = ema(pd.Series(loss), period)

    rs = avg_gain / avg_loss
    val = 100 - (100 / (1 + rs))
    return val

def atr(high, low, close_b, period=14):
    tr = pd.concat([
        high - low,
        (high - close_b.shift()).abs(),
        (low - close_b.shift()).abs()
    ], axis=1).max(axis=1)
    val = ema(tr, period)
    return val

def supertrend(high, low, close, atr_period=10, multiplier=3.0):
    atr_val = atr(high, low, close, atr_period)
    hl2 = (high + low) / 2

    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val
    return upper_band, lower_band
    
def bb(prices, period=20, k=2):
    mid = sma(prices, period)
    std = prices.rolling(window=period).std()

    upper = mid + k * std
    lower = mid - k * std
    return upper, mid, lower

def adx(high, low, close, period=14):
    plus_dm = high.diff()
    minus_dm = low.diff().abs()

    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)

    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(pd.Series(plus_dm), period) / atr_val
    minus_di = 100 * ema(pd.Series(minus_dm), period) / atr_val

    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    adx_val = ema(dx, period)
    return adx_val

def volume_change(vol, period=20):
    vol_pct = (vol - vol.shift(1)) / vol.shift(1) * 100
    vol_avg = sma(vol, period)
    vol_conf = vol > 1.5 * vol_avg
    return vol_pct, vol_conf