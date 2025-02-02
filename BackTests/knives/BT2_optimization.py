import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import time
from itertools import product

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


# Функция для расчета ATR
def calculate_atr(df, window):
    df['tr'] = np.maximum(df['high'] - df['low'],
                          np.maximum(abs(df['high'] - df['close'].shift()),
                                     abs(df['low'] - df['close'].shift())))
    df['atr'] = df['tr'].rolling(window=window).mean()
    return df


# Функция для расчета изменения цены за последнюю свечу
def calculate_price_change(df):
    df['price_change'] = (df['close'] - df['close'].shift()) / df['close'].shift() * 100
    return df


# Торговая стратегия
def trading_strategy(df, atr_window, thresholds):
    df = calculate_atr(df, atr_window)
    df = calculate_price_change(df)
    df['signal'] = 0
    position = 0
    entry_price = 0
    entry_time = None
    entry_mid_price = 0
    ban_until = None

    for i in range(1, len(df)):
        current_time = df['timestamp'].iloc[i]

        # Фильтры на бан сделок
        if ban_until is not None and current_time < ban_until:
            continue
        if df['atr'].iloc[i] > 4:
            continue

        if position == 0:
            if df['atr'].iloc[i] < 2 and abs(df['price_change'].iloc[i]) > thresholds['atr_2']:
                df.at[i, 'signal'] = -1 if df['price_change'].iloc[
                                               i] > 0 else 1  # Short signal if price increased, Long signal if price decreased
                position = -df['price_change'].iloc[i] // abs(df['price_change'].iloc[i])  # -1 for short, 1 for long
                entry_price = df['close'].iloc[i]
                entry_time = current_time
                entry_mid_price = (df['open'].iloc[i] + df['close'].iloc[i]) / 2
            elif df['atr'].iloc[i] < 3 and abs(df['price_change'].iloc[i]) > thresholds['atr_3']:
                df.at[i, 'signal'] = -1 if df['price_change'].iloc[
                                               i] > 0 else 1  # Short signal if price increased, Long signal if price decreased
                position = -df['price_change'].iloc[i] // abs(df['price_change'].iloc[i])  # -1 for short, 1 for long
                entry_price = df['close'].iloc[i]
                entry_time = current_time
                entry_mid_price = (df['open'].iloc[i] + df['close'].iloc[i]) / 2
            elif df['atr'].iloc[i] < 4 and abs(df['price_change'].iloc[i]) > thresholds['atr_4']:
                df.at[i, 'signal'] = -1 if df['price_change'].iloc[
                                               i] > 0 else 1  # Short signal if price increased, Long signal if price decreased
                position = -df['price_change'].iloc[i] // abs(df['price_change'].iloc[i])  # -1 for short, 1 for long
                entry_price = df['close'].iloc[i]
                entry_time = current_time
                entry_mid_price = (df['open'].iloc[i] + df['close'].iloc[i]) / 2
        elif position != 0:
            hold_duration = (current_time - entry_time).total_seconds() / 60
            if hold_duration > 7 and df['price_change'].iloc[i] > 0:
                df.at[i, 'signal'] = 2 if position == 1 else -2  # Close long in profit or short in profit
                position = 0
                ban_until = current_time + pd.Timedelta(hours=1)
            elif hold_duration > 12:
                if df['price_change'].iloc[i] > 0 or df['price_change'].iloc[i] < 0:
                    df.at[i, 'signal'] = 2 if position == 1 else -2  # Close long in profit or short in profit
                else:
                    df.at[i, 'signal'] = 3 if position == 1 else -3  # Close long in loss or short in loss
                position = 0
                ban_until = current_time + pd.Timedelta(hours=1)
            elif (position == 1 and df['close'].iloc[i] >= entry_mid_price) or (
                    position == -1 and df['close'].iloc[i] <= entry_mid_price):
                df.at[i, 'signal'] = 4 if position == 1 else -4  # Auto take profit
                position = 0
                ban_until = current_time + pd.Timedelta(hours=1)

    return df


# Бектестинг стратегии
def backtest(df, trade_volume):
    pnl_history = []
    trades = []

    entry_price = None
    entry_index = None

    for i in range(len(df)):
        if df['signal'].iloc[i] in [1, -1]:  # Open position
            entry_price = df['close'].iloc[i]
            entry_index = i
            trades.append({
                'type': 'Long' if df['signal'].iloc[i] == 1 else 'Short',
                'entry_price': entry_price,
                'exit_price': None,
                'profit': None,
                'exit_type': None
            })
        elif df['signal'].iloc[i] in [2, -2, 3, -3, 4, -4] and entry_price is not None:  # Close position
            exit_price = df['close'].iloc[i]
            pnl = (exit_price - entry_price) / entry_price * 100 if trades[-1]['type'] == 'Long' else (
                                                                                                                  entry_price - exit_price) / entry_price * 100
            trades[-1]['exit_price'] = exit_price
            trades[-1]['profit'] = pnl
            trades[-1]['exit_type'] = 'Profit' if df['signal'].iloc[i] in [2, -2, 4, -4] else 'Loss'
            entry_price = None
            entry_index = None
            pnl_history.append(pnl)

    return pnl_history, trades


# Функция для оптимизации параметров
def optimize_parameters(df, param_grid, trade_volume):
    best_params = None
    best_pnl = -np.inf

    for params in param_grid:
        atr_window, atr_2, atr_3, atr_4 = params
        thresholds = {'atr_2': atr_2, 'atr_3': atr_3, 'atr_4': atr_4}
        df_strategy = trading_strategy(df.copy(), atr_window, thresholds)
        pnl_history, trades = backtest(df_strategy, trade_volume)
        total_pnl = np.sum(pnl_history)
        if total_pnl > best_pnl:
            best_pnl = total_pnl
            best_params = params

    return best_params, best_pnl


# Основная функция для Streamlit
def main():
    st.title("Алготрейдинг Бектестинг Бот")
    st.sidebar.header("Настройки стратегии")

    # Настройки оптимизации
    symbol = 'BLZ/USDT'
    timeframe = '1h'
    start_date = '2022-01-01'
    end_date = '2024-01-01'
    trade_volume = 1000.0

    if st.sidebar.button("Запустить оптимизацию"):
        # Загрузка данных один раз
        df = fetch_ohlcv(symbol, timeframe, start_date, end_date)

        # Определение сетки параметров для Grid Search
        atr_window_range = range(5, 21, 5)
        atr_2_range = np.arange(4.0, 10.0, 0.5)
        atr_3_range = np.arange(5.0, 12.0, 0.5)
        atr_4_range = np.arange(6.0, 14.0, 0.5)
        param_grid = list(product(atr_window_range, atr_2_range, atr_3_range, atr_4_range))

        best_params, best_pnl = optimize_parameters(df, param_grid, trade_volume)
        st.write(f"Лучшие параметры: {best_params}")
        st.write(f"Лучший PnL: {best_pnl:.2f}%")

        # Применение лучших параметров
        atr_window, atr_2, atr_3, atr_4 = best_params
        thresholds = {'atr_2': atr_2, 'atr_3': atr_3, 'atr_4': atr_4}
        df_strategy = trading_strategy(df.copy(), atr_window, thresholds)
        pnl_history, trades = backtest(df_strategy, trade_volume)

        # Отображение таблицы с результатами сделок
        trades_df = pd.DataFrame(trades)
        st.write(trades_df)

        if 'profit' in trades_df.columns:
            trades_df['profit'] = trades_df['profit'].apply(lambda x: f"{x:.2f}%" if x is not None else None)
            total_pnl = trades_df['profit'].apply(lambda x: float(x.strip('%')) if x is not None else 0).sum()
            st.write(f"Общий PnL: {total_pnl:.2f}%")

            # График PnL
            plt.figure(figsize=(10, 5))
            plt.plot(np.cumsum([float(x.strip('%')) for x in trades_df['profit'] if x is not None]), label='PnL')
            plt.xlabel('Сделки')
            plt.ylabel('PnL (%)')
            plt.legend()
            st.pyplot(plt)

        # График цен и торговых сигналов
        plt.figure(figsize=(10, 5))
        plt.plot(df_strategy['timestamp'], df_strategy['close'], label='Цена закрытия')
        buy_signals = df_strategy[df_strategy['signal'] == 1]
        close_long_signals = df_strategy[df_strategy['signal'] == 2]
        short_signals = df_strategy[df_strategy['signal'] == -1]
        close_short_signals = df_strategy[df_strategy['signal'] == -2]
        stop_loss_long = df_strategy[df_strategy['signal'] == 3]
        stop_loss_short = df_strategy[df_strategy['signal'] == -3]
        auto_take_profit_long = df_strategy[df_strategy['signal'] == 4]
        auto_take_profit_short = df_strategy[df_strategy['signal'] == -4]
        plt.scatter(buy_signals['timestamp'], buy_signals['close'], marker='^', color='green', label='Покупка')
        plt.scatter(close_long_signals['timestamp'], close_long_signals['close'], marker='v', color='red',
                    label='Закрытие лонга')
        plt.scatter(short_signals['timestamp'], short_signals['close'], marker='v', color='blue', label='Шорт')
        plt.scatter(close_short_signals['timestamp'], close_short_signals['close'], marker='^', color='orange',
                    label='Закрытие шорта')
        plt.scatter(stop_loss_long['timestamp'], stop_loss_long['close'], marker='x', color='purple',
                    label='Стоп-лосс лонга')
        plt.scatter(stop_loss_short['timestamp'], stop_loss_short['close'], marker='x', color='brown',
                    label='Стоп-лосс шорта')
        plt.scatter(auto_take_profit_long['timestamp'], auto_take_profit_long['close'], marker='*', color='cyan',
                    label='Авто тейк-профит лонга')
        plt.scatter(auto_take_profit_short['timestamp'], auto_take_profit_short['close'], marker='*', color='magenta',
                    label='Авто тейк-профит шорта')
        plt.xlabel('Дата')
        plt.ylabel('Цена')
        plt.legend()
        st.pyplot(plt)


if __name__ == "__main__":
    main()
