import ccxt
import pandas as pd
import numpy as np
import streamlit as st
import time
from datetime import datetime, timedelta
from itertools import product

# Инициализация Binance API
exchange = ccxt.binance({
    'apiKey': 'your_api_key',
    'secret': 'your_secret_key',
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


# Функция для расчета скользящей корреляции
def calculate_rolling_correlation(df1, df2, window):
    correlation = df1['close'].rolling(window).corr(df2['close'])
    return correlation


# Функция для расчета индикатора RSI
def calculate_rsi(df, period=14):
    delta = df['close'].diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# Функция для расчета индикатора MACD
def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    fast_ema = df['close'].ewm(span=fast_period, min_periods=fast_period).mean()
    slow_ema = df['close'].ewm(span=slow_period, min_periods=slow_period).mean()
    macd = fast_ema - slow_ema
    signal = macd.ewm(span=signal_period, min_periods=signal_period).mean()
    return macd, signal


# Торговая стратегия
def trading_strategy(df_eth, df_btc, window, entry_threshold, stop_loss_threshold, max_holding_period,
                     rsi_threshold=70):
    correlation = calculate_rolling_correlation(df_eth, df_btc, window)
    mean_correlation = correlation.mean()
    std_correlation = correlation.std()
    upper_bound_entry = mean_correlation + entry_threshold * std_correlation
    lower_bound_entry = mean_correlation - entry_threshold * std_correlation
    upper_bound_stop_loss = mean_correlation + stop_loss_threshold * std_correlation
    lower_bound_stop_loss = mean_correlation - stop_loss_threshold * std_correlation

    df_eth['signal'] = 0
    df_btc['signal'] = 0

    df_eth['rsi'] = calculate_rsi(df_eth)
    df_btc['rsi'] = calculate_rsi(df_btc)

    macd_eth, signal_eth = calculate_macd(df_eth)
    macd_btc, signal_btc = calculate_macd(df_btc)

    position = 0
    entry_time = None

    for i in range(window, len(correlation)):
        current_time = df_eth['timestamp'].iloc[i]
        if position == 0:
            if correlation.iloc[i] > upper_bound_entry and df_eth['rsi'].iloc[i] < rsi_threshold and macd_eth.iloc[i] > \
                    signal_eth.iloc[i]:
                df_eth.at[i, 'signal'] = -1  # Short ETH
                df_btc.at[i, 'signal'] = 1  # Long BTC
                position = -1
                entry_time = current_time
            elif correlation.iloc[i] < lower_bound_entry and df_eth['rsi'].iloc[i] > (100 - rsi_threshold) and \
                    macd_eth.iloc[i] < signal_eth.iloc[i]:
                df_eth.at[i, 'signal'] = 1  # Long ETH
                df_btc.at[i, 'signal'] = -1  # Short BTC
                position = 1
                entry_time = current_time
        elif position != 0:
            holding_period = (current_time - entry_time).total_seconds() / 60
            if (correlation.iloc[i] < mean_correlation and position == -1) or (
                    correlation.iloc[i] > mean_correlation and position == 1):
                df_eth.at[i, 'signal'] = 2  # Close position (mean reversion)
                df_btc.at[i, 'signal'] = -2 if position == 1 else 2  # Close opposite position
                position = 0
            elif holding_period > max_holding_period:
                df_eth.at[i, 'signal'] = 3  # Close position (time limit)
                df_btc.at[i, 'signal'] = 3
                position = 0
            elif (correlation.iloc[i] > upper_bound_stop_loss and position == -1) or (
                    correlation.iloc[i] < lower_bound_stop_loss and position == 1):
                df_eth.at[i, 'signal'] = 4  # Close position (stop loss)
                df_btc.at[i, 'signal'] = -4 if position == 1 else 4  # Close opposite position
                position = 0

    return df_eth, df_btc


# Функция для бектестинга стратегии
def backtest(df_eth, df_btc, trade_volume):
    pnl_history = []
    trades = []

    for i in range(len(df_eth)):
        if df_eth['signal'].iloc[i] in [1, -1]:  # Open position
            entry_price_eth = df_eth['close'].iloc[i]
            entry_price_btc = df_btc['close'].iloc[i]
            trades.append({
                'type': 'Long ETH' if df_eth['signal'].iloc[i] == 1 else 'Short ETH',
                'entry_price_eth': entry_price_eth,
                'entry_price_btc': entry_price_btc,
                'exit_price_eth': None,
                'exit_price_btc': None,
                'profit': None,
                'exit_type': None
            })
        elif df_eth['signal'].iloc[i] in [2, -2, 3, 4] and trades:
            exit_price_eth = df_eth['close'].iloc[i]
            exit_price_btc = df_btc['close'].iloc[i]
            pnl_eth = (exit_price_eth - trades[-1]['entry_price_eth']) / trades[-1]['entry_price_eth'] * 100 if \
            trades[-1]['type'] == 'Long ETH' else (trades[-1]['entry_price_eth'] - exit_price_eth) / trades[-1][
                'entry_price_eth'] * 100
            pnl_btc = (exit_price_btc - trades[-1]['entry_price_btc']) / trades[-1]['entry_price_btc'] * 100 if \
            trades[-1]['type'] == 'Short ETH' else (trades[-1]['entry_price_btc'] - exit_price_btc) / trades[-1][
                'entry_price_btc'] * 100
            pnl = pnl_eth + pnl_btc
            trades[-1]['exit_price_eth'] = exit_price_eth
            trades[-1]['exit_price_btc'] = exit_price_btc
            trades[-1]['profit'] = pnl
            trades[-1]['exit_type'] = 'Correlation mean' if df_eth['signal'].iloc[i] in [2, -2] else 'Time limit' if \
            df_eth['signal'].iloc[i] == 3 else 'Stop loss'
            pnl_history.append(pnl)

    return pnl_history, trades


# Функция для оптимизации параметров
def optimize_parameters(df_eth, df_btc, param_grid, trade_volume):
    best_params = None
    best_pnl = -np.inf

    for params in param_grid:
        window, entry_threshold, stop_loss_threshold, max_holding_period, rsi_threshold = params
        df_eth, df_btc = trading_strategy(df_eth, df_btc, window, entry_threshold, stop_loss_threshold,
                                          max_holding_period, rsi_threshold)
        pnl_history, trades = backtest(df_eth, df_btc, trade_volume)
        total_pnl = np.sum(pnl_history)
        if total_pnl > best_pnl:
            best_pnl = total_pnl
            best_params = params

    return best_params, best_pnl


# Основная функция для Streamlit
def main():
    st.title("Алготрейдинг Бектестинг Бот")
    st.sidebar.header("Настройки стратегии")

    # Выбор временного интервала
    timeframe = st.sidebar.selectbox("Выберите временной интервал", ['1h', '1d'])

    # Выбор дат
    start_date = st.sidebar.date_input("Дата начала", pd.to_datetime("2022-01-01"))
    end_date = st.sidebar.date_input("Дата окончания", pd.to_datetime("2022-12-31"))

    trade_volume = st.sidebar.number_input("Объем сделки", value=1000.0)

    if st.sidebar.button("Запустить оптимизацию"):
        df_eth = fetch_ohlcv('ETH/USDT', timeframe, start_date, end_date)
        df_btc = fetch_ohlcv('BTC/USDT', timeframe, start_date, end_date)

        if df_eth.empty or df_btc.empty:
            st.error("Данные не загружены. Проверьте даты или API.")
            return

        # Определение сетки параметров для Grid Search
        param_grid = list(product(
            range(10, 31, 5),  # window
            np.arange(1.0, 2.5, 0.5),  # entry_threshold
            np.arange(2.0, 3.5, 0.5),  # stop_loss_threshold
            range(300, 720, 120),  # max_holding_period
            range(60, 80, 10)  # rsi_threshold
        ))

        best_params, best_pnl = optimize_parameters(df_eth, df_btc, param_grid, trade_volume)
        st.write(f"Лучшие параметры: {best_params}")
        st.write(f"Лучший PnL: {best_pnl:.2f}%")

        # Применение лучших параметров
        window, entry_threshold, stop_loss_threshold, max_holding_period, rsi_threshold = best_params
        df_eth, df_btc = trading_strategy(df_eth, df_btc, window, entry_threshold, stop_loss_threshold,
                                          max_holding_period, rsi_threshold)
        pnl_history, trades = backtest(df_eth, df_btc, trade_volume)

        # Отображение таблицы с результатами сделок
        trades_df = pd.DataFrame(trades)
        st.write(trades_df)

        if 'profit' in trades_df.columns:
            trades_df['profit'] = trades_df['profit'].apply(lambda x: f"{x:.2f}%" if x is not None else None)
            total_pnl = trades_df['profit'].apply(lambda x: float(x.strip('%')) if x is not None else 0).sum()
            st.write(f"Общий PnL: {total_pnl:.2f}%")
            st.line_chart(np.cumsum([float(x.strip('%')) for x in trades_df['profit'] if x is not None]))

        # График цен и торговых сигналов
        st.line_chart(df_eth.set_index('timestamp')['close'])
        st.line_chart(df_btc.set_index('timestamp')['close'])

        signals = df_eth[df_eth['signal'] != 0].copy()
        signals['timestamp'] = signals['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        st.write(signals[['timestamp', 'signal']])


if __name__ == "__main__":
    main()
