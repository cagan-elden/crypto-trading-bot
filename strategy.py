from indicators import *

def generate_signals(df_15m, df_1h, df_4h, df_1d):
    """
    Expects four DataFrames (15m, 1h, 4h, 1d) with columns: ['open','high','low','close','volume']
    All DataFrames must be indexed by datetime and have no duplicate indices.
    Returns df_15m with added columns: buy_signal (bool), sell_signal (bool), position (1 long, -1 short, 0 flat)
    """
    df1d = df_1d.copy()
    df1d['EMA50_1d'] = ema(df1d['close'], 50)
    df1d['EMA200_1d'] = ema(df1d['close'], 200)
    df1d['trend_long_1d'] = df1d['close'] > df1d['EMA200_1d']

    df4h = df_4h.copy()
    df4h['EMA21_4h'] = ema(df4h['close'], 21)
    df4h['EMA55_4h'] = ema(df4h['close'], 55)
    macd_4h, signal_4h, hist_4h = macd(df4h['close'])
    df4h['macd_4h'] = macd_4h
    df4h['signal_4h'] = signal_4h
    df4h['hist_4h'] = hist_4h
    df4h['rsi_4h'] = rsi(df4h['close'], 14)
    df4h['adx_4h'] = adx(df4h['high'], df4h['low'], df4h['close'], 14)
    df4h['trend_long_4h'] = (df4h['EMA21_4h'] > df4h['EMA55_4h']) & (df4h['macd_4h'] > df4h['signal_4h']) & (df4h['adx_4h'] > 25)

    df1h = df_1h.copy()
    df1h['EMA20_1h'] = ema(df1h['close'], 20)
    df1h['EMA50_1h'] = ema(df1h['close'], 50)
    macd_1h, signal_1h, hist_1h = macd(df1h['close'])
    df1h['macd_1h'] = macd_1h
    df1h['signal_1h'] = signal_1h
    df1h['hist_1h'] = hist_1h
    df1h['rsi_1h'] = rsi(df1h['close'], 14)
    df1h['atr_1h'] = atr(df1h['high'], df1h['low'], df1h['close'], 14)
    st_1h, st_upper_1h, st_lower_1h, st_dir_1h = supertrend(df1h['high'], df1h['low'], df1h['close'], 10, 3.0)
    df1h['supertrend_1h'] = st_1h
    bb_up_1h, bb_mid_1h, bb_low_1h = bb(df1h['close'], 20, 2)
    df1h['bb_up_1h'] = bb_up_1h
    df1h['bb_mid_1h'] = bb_mid_1h
    df1h['bb_low_1h'] = bb_low_1h
    df1h['vol_pct_1h'], df1h['vol_conf_1h'] = volume_change(df1h['volume'], 20)

    df15 = df_15m.copy()
    df15['EMA20_15m'] = ema(df15['close'], 20)
    macd_15m, signal_15m, hist_15m = macd(df15['close'])
    df15['macd_15m'] = macd_15m
    df15['signal_15m'] = signal_15m
    df15['hist_15m'] = hist_15m
    df15['rsi_15m'] = rsi(df15['close'], 14)
    df15['atr_15m'] = atr(df15['high'], df15['low'], df15['close'], 14)
    st_15m, st_up_15m, st_low_15m, st_dir_15m = supertrend(df15['high'], df15['low'], df15['close'], 10, 3.0)
    df15['supertrend_15m'] = st_15m
    df15['bb_up_15m'], df15['bb_mid_15m'], df15['bb_low_15m'] = bb(df15['close'], 20, 2)
    df15['vol_pct_15m'], df15['vol_conf_15m'] = volume_change(df15['volume'], 20)

    df15 = df15.sort_index()
    df1h = df1h.sort_index()
    df4h = df4h.sort_index()
    df1d = df1d.sort_index()

    def reindex_to(base_idx, src_series):
        return src_series.reindex(base_idx, method='ffill')

    for col in ['EMA20_1h','EMA50_1h','macd_1h','signal_1h','hist_1h','rsi_1h','atr_1h','supertrend_1h','bb_mid_1h','vol_pct_1h','vol_conf_1h']:
        df15[col] = reindex_to(df15.index, df1h[col])

    for col in ['EMA21_4h','EMA55_4h','macd_4h','signal_4h','hist_4h','rsi_4h','adx_4h','trend_long_4h']:
        df15[col] = reindex_to(df15.index, df4h[col])

    df15['trend_long_1d'] = reindex_to(df15.index, df1d['trend_long_1d'])

    # signal
    buy_conditions = pd.DataFrame(index=df15.index)
    buy_conditions['trend_ok'] = (df15['trend_long_1d'] == True) & (df15['trend_long_4h'] == True)
    buy_conditions['momentum_ok'] = (df15['macd_1h'] > df15['signal_1h']) & (df15['rsi_1h'] > 50) & (df15['adx_4h'] > 20)
    buy_conditions['volatility_ok'] = (df15['close'] > df15['bb_mid_1h']) & (df15['vol_conf_1h'] == True)
    buy_conditions['entry_fine'] = (df15['macd_15m'] > df15['signal_15m']) & (df15['rsi_15m'] > 45) & (df15['vol_pct_15m'] > 20)

    df15['buy_signal'] = ((buy_conditions[['trend_ok','momentum_ok','volatility_ok']].sum(axis=1) >= 2) & (buy_conditions['entry_fine']))

    sell_conditions = pd.DataFrame(index=df15.index)
    sell_conditions['trend_flip'] = (df15['EMA20_1h'] < df15['EMA50_1h']) | (df15['macd_1h'] < df15['signal_1h'])
    sell_conditions['weak_trend'] = df15['adx_4h'] < 20
    sell_conditions['overbought'] = df15['rsi_15m'] > 70
    sell_conditions['vol_drop'] = df15['vol_conf_1h'] == False

    df15['sell_signal'] = (sell_conditions[['trend_flip','weak_trend','overbought','vol_drop']].sum(axis=1) >= 2)

    pos = 0
    positions = []
    for i in range(len(df15)):
        if pos == 0 and df15['buy_signal'].iat[i]:
            pos = 1
        elif pos == 1 and df15['sell_signal'].iat[i]:
            pos = 0
        positions.append(pos)
    df15['position'] = positions

    return df15