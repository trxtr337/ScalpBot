import multiprocessing
import subprocess
import time
import pkg_resources
import sys
import os

REQUIRED_LIBRARIES = ['redis']

def install_packages():
    for package in REQUIRED_LIBRARIES:
        try:
            dist = pkg_resources.get_distribution(package)
            print(f"{package} ({dist.version}) is already installed.")
        except pkg_resources.DistributionNotFound:
            print(f"{package} is not installed. Installing now...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def run_consumer(python_interpreter):
    command = [python_interpreter, "T1_receiver.py"]
    subprocess.run(command)

if __name__ == '__main__':
    # Установка необходимых пакетов
    install_packages()

    # Путь к интерпретатору Python в виртуальном окружении
    python_interpreter = os.path.join(sys.prefix, 'Scripts', 'python.exe')

    # Количество получателей
    num_consumers = 500

    # Запуск процессов получателей
    processes = []
    start_time = time.time()
    print(f"Started at: {start_time}")

    for _ in range(num_consumers):
        p = multiprocessing.Process(target=run_consumer, args=(python_interpreter,))
        p.start()
        processes.append(p)

    # Ожидание времени для проверки задержки
    time.sleep(10)  # Ждем 10 секунд для запуска всех процессов

    end_time = time.time()
    print(f"Ended at: {end_time}")

    # Вывод времени задержки
    delay = end_time - start_time
    print(f"Total delay: {delay} seconds")

    # Процессы продолжают работать, пока вы не остановите их вручную
