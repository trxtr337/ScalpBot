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

# Функция для расчета стандартного отклонения и полос Боллинджера
def calculate_bollinger_bands(df, window):
    df['mean'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()
    df['upper_band'] = df['mean'] + 3 * df['std']
    df['lower_band'] = df['mean'] - 3 * df['std']
    df['mid_band_upper'] = df['mean'] + 1.5 * df['std']
    df['mid_band_lower'] = df['mean'] - 1.5 * df['std']
    return df

# Торговая стратегия
def trading_strategy(df, window, stop_loss):
    df = calculate_bollinger_bands(df, window)
    df['signal'] = 0
    position = 0
    entry_price = 0
    in_ban = False

    for i in range(1, len(df)):
        if not in_ban:
            if position == 0:
                if df['close'].iloc[i] < df['lower_band'].iloc[i]:
                    df.at[i, 'signal'] = 1  # Buy signal
                    position = 1
                    entry_price = df['close'].iloc[i]
                elif df['close'].iloc[i] > df['upper_band'].iloc[i]:
                    df.at[i, 'signal'] = -1  # Short signal
                    position = -1
                    entry_price = df['close'].iloc[i]
            elif position == 1:
                if df['close'].iloc[i] > df['mean'].iloc[i]:
                    df.at[i, 'signal'] = -2  # Close long position
                    position = 0
                elif df['close'].iloc[i] < entry_price * (1 - stop_loss):
                    df.at[i, 'signal'] = -3  # Stop loss for long position
                    position = 0
                    in_ban = True
            elif position == -1:
                if df['close'].iloc[i] < df['mean'].iloc[i]:
                    df.at[i, 'signal'] = 2  # Close short position
                    position = 0
                elif df['close'].iloc[i] > entry_price * (1 + stop_loss):
                    df.at[i, 'signal'] = 3  # Stop loss for short position
                    position = 0
                    in_ban = True
        else:
            if df['close'].iloc[i] > df['mid_band_lower'].iloc[i] and df['close'].iloc[i] < df['mid_band_upper'].iloc[i]:
                in_ban = False  # Exit ban if price returns to mid range

    return df

# Бектестинг стратегии
def backtest(df, trade_volume, stop_loss):
    pnl_history = []
    trades = []

    entry_price = None
    entry_index = None

    for i in range(len(df)):
        if df['signal'].iloc[i] == 1 or df['signal'].iloc[i] == -1:  # Open position
            entry_price = df['close'].iloc[i]
            entry_index = i
            trades.append({
                'type': 'Long' if df['signal'].iloc[i] == 1 else 'Short',
                'entry_price': entry_price,
                'exit_price': None,
                'profit': None,
                'exit_type': None
            })
        elif df['signal'].iloc[i] in [-2, 2, -3, 3] and entry_price is not None:  # Close position
            exit_price = df['close'].iloc[i]
            pnl = (exit_price - entry_price) / entry_price * 100 if trades[-1]['type'] == 'Long' else (entry_price - exit_price) / entry_price * 100
            trades[-1]['exit_price'] = exit_price
            trades[-1]['profit'] = pnl
            trades[-1]['exit_type'] = 'Mean' if df['signal'].iloc[i] in [-2, 2] else 'Stop Loss'
            entry_price = None
            entry_index = None
            pnl_history.append(pnl)

    return pnl_history, trades

# Основная функция для Streamlit
def main():
    st.title("Алготрейдинг Бектестинг Бот")
    st.sidebar.header("Настройки стратегии")

    # Выбор монеты и временного интервала
    symbol = st.sidebar.selectbox("Выберите монету", ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'DOGE/USDT', 'LTC/USDT', 'ADA/USDT', 'SOL/USDT', 'DOT/USDT', 'AVAX/USDT'])
    timeframe = st.sidebar.selectbox("Выберите временной интервал", ['1m', '5m', '15m', '1h', '1d'])

    # Выбор дат
    start_date = st.sidebar.date_input("Дата начала", pd.to_datetime("2022-01-01"))
    end_date = st.sidebar.date_input("Дата окончания", pd.to_datetime("2022-12-31"))

    window = st.sidebar.slider("Окно для расчета стандартного отклонения", min_value=5, max_value=100, value=20, step=1)
    trade_volume = st.sidebar.number_input("Объем сделки", value=1000.0)
    stop_loss = st.sidebar.slider("Стоп-лосс (в процентах)", min_value=0.01, max_value=0.10, value=0.05, step=0.01)

    if st.sidebar.button("Запустить бектест"):
        df = fetch_ohlcv(symbol, timeframe, start_date, end_date)
        df = trading_strategy(df, window, stop_loss)
        pnl_history, trades = backtest(df, trade_volume, stop_loss)

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

        # График цен и торговых сигналов
        plt.figure(figsize=(10, 5))
        plt.plot(df['timestamp'], df['close'], label='Цена закрытия')
        plt.plot(df['timestamp'], df['mean'], label='Скользящая средняя')
        plt.plot(df['timestamp'], df['upper_band'], label='Верхняя полоса')
        plt.plot(df['timestamp'], df['lower_band'], label='Нижняя полоса')
        buy_signals = df[df['signal'] == 1]
        close_long_signals = df[df['signal'] == -2]
        short_signals = df[df['signal'] == -1]
        close_short_signals = df[df['signal'] == 2]
        stop_loss_long = df[df['signal'] == -3]
        stop_loss_short = df[df['signal'] == 3]
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
        plt.xlabel('Дата')
        plt.ylabel('Цена')
        plt.legend()
        st.pyplot(plt)

if __name__ == "__main__":
    main()
