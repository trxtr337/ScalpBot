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

# Функция для расчета ATR
def calculate_atr(df, window):
    df['tr'] = np.maximum(df['high'] - df['low'],
                          np.maximum(abs(df['high'] - df['close'].shift()),
                                     abs(df['low'] - df['close'].shift())))
    df['atr'] = df['tr'].rolling(window=window).mean()
    return df

# Функция для расчета полос Боллинджера
def calculate_bollinger_bands(df, window):
    df['mean'] = df['close'].rolling(window=window).mean()
    return df

# Торговая стратегия "подбора ножей"
def trading_strategy(df, window, atr_window, atr_multiplier, stop_loss_multiplier, price_change_threshold=0.025):
    df = calculate_bollinger_bands(df, window)
    df = calculate_atr(df, atr_window)
    df['signal'] = 0
    position = 0
    entry_price = 0
    last_stop_loss_time = pd.Timestamp(0)  # Инициализация начального времени

    for i in range(1, len(df)):
        current_time = df['timestamp'].iloc[i]

        # Проверка на 6-часовой интервал после стоп-лосса
        if (current_time - last_stop_loss_time).total_seconds() < 6 * 3600:
            continue

        if position == 0:
            # Проверка на проход множителя ATR и движение минимум на 2.5% за одноминутный интервал и открытие позиции против движения
            price_change = (df['close'].iloc[i] - df['close'].iloc[i-1]) / df['close'].iloc[i-1]
            if i > 0 and df['close'].iloc[i] - df['mean'].iloc[i] > atr_multiplier * df['atr'].iloc[i] and price_change > price_change_threshold:
                df.at[i, 'signal'] = -1  # Short signal
                position = -1
                entry_price = df['close'].iloc[i]
            elif i > 0 and df['mean'].iloc[i] - df['close'].iloc[i] > atr_multiplier * df['atr'].iloc[i] and price_change < -price_change_threshold:
                df.at[i, 'signal'] = 1  # Buy signal
                position = 1
                entry_price = df['close'].iloc[i]
        elif position == 1:
            if df['close'].iloc[i] > df['mean'].iloc[i]:
                df.at[i, 'signal'] = -2  # Close long position
                position = 0
            elif df['close'].iloc[i] < entry_price - stop_loss_multiplier * df['atr'].iloc[i]:
                df.at[i, 'signal'] = -3  # Stop loss for long position
                position = 0
                last_stop_loss_time = current_time
        elif position == -1:
            if df['close'].iloc[i] < df['mean'].iloc[i]:
                df.at[i, 'signal'] = 2  # Close short position
                position = 0
            elif df['close'].iloc[i] > entry_price + stop_loss_multiplier * df['atr'].iloc[i]:
                df.at[i, 'signal'] = 3  # Stop loss for short position
                position = 0
                last_stop_loss_time = current_time

    return df


# Бектестинг стратегии
def backtest(df, trade_volume, stop_loss_multiplier):
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
    symbol = st.sidebar.selectbox("Выберите монету", ['TOMO/USDT', 'BLZ/USDT', 'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'DOGE/USDT', 'LTC/USDT', 'ADA/USDT', 'SOL/USDT', 'DOT/USDT', 'AVAX/USDT'])
    timeframe = st.sidebar.selectbox("Выберите временной интервал", ['1m', '5m', '15m', '1h', '1d'])

    # Выбор дат
    start_date = st.sidebar.date_input("Дата начала", pd.to_datetime("2022-01-01"))
    end_date = st.sidebar.date_input("Дата окончания", pd.to_datetime("2022-12-31"))

    window = st.sidebar.slider("Окно для расчета средней цены", min_value=5, max_value=100, value=20, step=1)
    atr_window = st.sidebar.slider("Окно для расчета ATR", min_value=5, max_value=100, value=14, step=1)
    atr_multiplier = st.sidebar.slider("Множитель ATR для сигнала", min_value=0.5, max_value=5.0, value=1.5, step=0.1)
    stop_loss_multiplier = st.sidebar.slider("Множитель ATR для стоп-лосса", min_value=0.5, max_value=10.0, value=1.0, step=0.1)
    trade_volume = st.sidebar.number_input("Объем сделки", value=1000.0)

    if st.sidebar.button("Запустить бектест"):
        df = fetch_ohlcv(symbol, timeframe, start_date, end_date)
        df = trading_strategy(df, window, atr_window, atr_multiplier, stop_loss_multiplier)
        pnl_history, trades = backtest(df, trade_volume, stop_loss_multiplier)

        # Отображение таблицы с результатами сделок
        trades_df = pd.DataFrame(trades)
        st.write(trades_df)

        # Отображение PnL
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
        plt.plot(df['timestamp'], df['close'], label='Цена закрытия')
        plt.plot(df['timestamp'], df['mean'], label='Скользящая средняя')
        buy_signals = df[df['signal'] == 1]
        close_long_signals = df[df['signal'] == -2]
        short_signals = df[df['signal'] == -1]
        close_short_signals = df[df['signal'] == 2]
        stop_loss_long = df[df['signal'] == -3]
        stop_loss_short = df[df['signal'] == 3]
        plt.scatter(buy_signals['timestamp'], buy_signals['close'], marker='^', color='green', label='Покупка')
        plt.scatter(close_long_signals['timestamp'], close_long_signals['close'], marker='v', color='red', label='Закрытие лонга')
        plt.scatter(short_signals['timestamp'], short_signals['close'], marker='v', color='blue', label='Шорт')
        plt.scatter(close_short_signals['timestamp'], close_short_signals['close'], marker='^', color='orange', label='Закрытие шорта')
        plt.scatter(stop_loss_long['timestamp'], stop_loss_long['close'], marker='x', color='purple', label='Стоп-лосс лонга')
        plt.scatter(stop_loss_short['timestamp'], stop_loss_short['close'], marker='x', color='brown', label='Стоп-лосс шорта')
        plt.xlabel('Дата')
        plt.ylabel('Цена')
        plt.legend()
        st.pyplot(plt)

if __name__ == "__main__":
    main()
