import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import time

# Инициализация Binance API
exchange = ccxt.binance({
    'apiKey': 'PobDVcnYrEgtST1D4DQZyk4f3l2Z8afkL2yWRtID8geuTm16aOw8CnhTtjznSfD4',
    'secret': 'cKAFB09CGbf5aahYNsh8X72b4JFQWTpmVlxJBsvP0Vm5PwFcsjDmtivLrVMBcOpK',
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
    },
})

# Функция для получения исторических данных
def fetch_ohlcv(symbol, timeframe, start_date, end_date):
    since = exchange.parse8601(f"{start_date}T00:00:00Z")
    end_time = exchange.parse8601(f"{end_date}T00:00:00Z")
    ohlcv = []
    while since < end_time:
        try:
            data = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not data:
                break
            since = data[-1][0] + 1
            ohlcv.extend(data)
            time.sleep(exchange.rateLimit / 1000)  # Уважение к лимитам API
        except ccxt.BaseError as e:
            print(f"Ошибка API: {e}")
            time.sleep(10)  # Ожидание перед повторной попыткой
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df[df['timestamp'] <= pd.to_datetime(end_date)]
    return df

# Функция для интерполяции данных
def interpolate_data(df1, df2):
    common_time_index = pd.date_range(start=df1['timestamp'].min(), end=df1['timestamp'].max(), freq='1T')
    df1_interp = pd.DataFrame({'timestamp': common_time_index})
    df2_interp = pd.DataFrame({'timestamp': common_time_index})
    df1_interp['close'] = np.interp(common_time_index.astype(np.int64) // 10**9, df1['timestamp'].astype(np.int64) // 10**9, df1['close'])
    df2_interp['close'] = np.interp(common_time_index.astype(np.int64) // 10**9, df2['timestamp'].astype(np.int64) // 10**9, df2['close'])
    return df1_interp, df2_interp

# Функция для расчета корреляции
def calculate_correlation(df1, df2, window):
    df1, df2 = interpolate_data(df1, df2)
    df = pd.DataFrame({'BTC_close': df1['close'], 'ETH_close': df2['close']})
    df['correlation'] = df['BTC_close'].rolling(window=window).corr(df['ETH_close'])
    df['timestamp'] = df1['timestamp']
    return df

# Торговая стратегия
def trading_strategy(df, correlation_threshold, stop_loss_correlation, take_profit_correlation):
    df['signal'] = 0
    position_btc = 0
    position_eth = 0
    entry_correlation = 0

    for i in range(1, len(df)):
        if position_btc == 0 and position_eth == 0:
            if df['correlation'].iloc[i] < correlation_threshold:
                df.at[i, 'signal'] = 1  # Open positions
                position_btc = -1  # Short BTC
                position_eth = 1  # Long ETH
                entry_correlation = df['correlation'].iloc[i]
            elif df['correlation'].iloc[i] > 1 - correlation_threshold:
                df.at[i, 'signal'] = -1  # Open positions
                position_btc = 1  # Long BTC
                position_eth = -1  # Short ETH
                entry_correlation = df['correlation'].iloc[i]
        else:
            if position_btc == -1 and position_eth == 1:
                if df['correlation'].iloc[i] > entry_correlation + stop_loss_correlation:
                    df.at[i, 'signal'] = -2  # Close positions (Stop Loss)
                    position_btc = 0
                    position_eth = 0
                elif df['correlation'].iloc[i] > take_profit_correlation:
                    df.at[i, 'signal'] = 2  # Close positions (Take Profit)
                    position_btc = 0
                    position_eth = 0
            elif position_btc == 1 and position_eth == -1:
                if df['correlation'].iloc[i] < entry_correlation - stop_loss_correlation:
                    df.at[i, 'signal'] = -2  # Close positions (Stop Loss)
                    position_btc = 0
                    position_eth = 0
                elif df['correlation'].iloc[i] < 1 - take_profit_correlation:
                    df.at[i, 'signal'] = 2  # Close positions (Take Profit)
                    position_btc = 0
                    position_eth = 0

    return df

# Бектестинг стратегии
def backtest(df, trade_volume, stop_loss, take_profit):
    pnl_history = []
    trades = []

    for i in range(len(df)):
        if df['signal'].iloc[i] in [1, -1]:  # Open positions
            entry_price_btc = df['BTC_close'].iloc[i]
            entry_price_eth = df['ETH_close'].iloc[i]
            trades.append({
                'type': 'Short BTC' if df['signal'].iloc[i] == 1 else 'Long BTC',
                'entry_price_btc': entry_price_btc,
                'entry_price_eth': entry_price_eth,
                'exit_price_btc': None,
                'exit_price_eth': None,
                'profit': None,
                'exit_type': None
            })
        elif df['signal'].iloc[i] in [-2, 2] and len(trades) > 0:  # Close positions
            exit_price_btc = df['BTC_close'].iloc[i]
            exit_price_eth = df['ETH_close'].iloc[i]
            entry_trade = trades[-1]
            pnl_btc = (entry_trade['entry_price_btc'] - exit_price_btc) / entry_trade['entry_price_btc'] * 100 if entry_trade['type'] == 'Short BTC' else (exit_price_btc - entry_trade['entry_price_btc']) / entry_trade['entry_price_btc'] * 100
            pnl_eth = (exit_price_eth - entry_trade['entry_price_eth']) / entry_trade['entry_price_eth'] * 100 if entry_trade['type'] == 'Short BTC' else (entry_trade['entry_price_eth'] - exit_price_eth) / entry_trade['entry_price_eth'] * 100
            total_pnl = pnl_btc + pnl_eth
            entry_trade['exit_price_btc'] = exit_price_btc
            entry_trade['exit_price_eth'] = exit_price_eth
            entry_trade['profit'] = total_pnl
            entry_trade['exit_type'] = 'Stop Loss' if df['signal'].iloc[i] == -2 else 'Take Profit'
            pnl_history.append(total_pnl)

    return pnl_history, trades

# Основная функция для Streamlit
def main():
    st.title("Алготрейдинг Бектестинг Бот")
    st.sidebar.header("Настройки стратегии")

    # Выбор дат
    start_date = st.sidebar.date_input("Дата начала", pd.to_datetime("2022-01-01"))
    end_date = st.sidebar.date_input("Дата окончания", pd.to_datetime("2022-12-31"))
    timeframe = st.sidebar.selectbox("Выберите временной интервал", ['1m', '5m', '15m', '1h', '1d'])

    window = st.sidebar.slider("Окно для расчета корреляции", min_value=5, max_value=100, value=20, step=1)
    trade_volume = st.sidebar.number_input("Объем сделки", value=1000.0)
    correlation_threshold = st.sidebar.slider("Порог корреляции", min_value=-1.0, max_value=1.0, value=0.6, step=0.01)
    stop_loss_correlation = st.sidebar.slider("Стоп-лосс корреляции", min_value=-1.0, max_value=1.0, value=0.4, step=0.01)
    take_profit_correlation = st.sidebar.slider("Тейк-профит корреляции", min_value=-1.0, max_value=1.0, value=0.85, step=0.01)

    if st.sidebar.button("Запустить бектест"):
        df_btc = fetch_ohlcv('BTC/USDT', timeframe, start_date, end_date)
        df_eth = fetch_ohlcv('ETH/USDT', timeframe, start_date, end_date)
        df = calculate_correlation(df_btc, df_eth, window)
        df = trading_strategy(df, correlation_threshold, stop_loss_correlation, take_profit_correlation)
        pnl_history, trades = backtest(df, trade_volume, stop_loss_correlation, take_profit_correlation)

        # Отображение таблицы с результатами сделок
        trades_df = pd.DataFrame(trades)
        trades_df['profit'] = trades_df['profit'].apply(lambda x: f"{x:.2f}%" if x is not None else None)
        st.write(trades_df)

        # Отображение PnL
        total_pnl = trades_df['profit'].apply(lambda x: float(x.strip('%')) if x is not None else 0).sum()
        st.write(f"Общий PnL: {total_pnl:.2f}%")

        # График PnL
        plt.figure(figsize=(10, 5))
        plt.plot(np.cumsum([float(x.strip('%')) for x in trades_df['profit'] if x is not None]), label='PnL')
        plt.xlabel('Сделки')
        plt.ylabel('PnL (%)')
        plt.legend()
        st.pyplot(plt)

        # График корреляции и торговых сигналов
        plt.figure(figsize=(10, 5))
        plt.plot(df['timestamp'], df['correlation'], label='Корреляция BTC/ETH')
        open_signals = df[(df['signal'] == 1) | (df['signal'] == -1)]
        close_signals = df[(df['signal'] == 2) | (df['signal'] == -2)]
        plt.scatter(open_signals['timestamp'], open_signals['correlation'], marker='^', color='green', label='Открытие позиций')
        plt.scatter(close_signals['timestamp'], close_signals['correlation'], marker='v', color='red', label='Закрытие позиций')
        plt.xlabel('Дата')
        plt.ylabel('Корреляция')
        plt.legend()
        st.pyplot(plt)

if __name__ == "__main__":
    main()
