import time
import subprocess
import sys
import pkg_resources


#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать



REQUIRED_LIBRARIES = ['gspread', 'oauth2client']

def install_packages():
    for package in REQUIRED_LIBRARIES:
        try:
            dist = pkg_resources.get_distribution(package)
            print(f"{package} ({dist.version}) is already installed.")
        except pkg_resources.DistributionNotFound:
            print(f"{package} is not installed. Installing now...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def run_script(script_name):
    process = subprocess.Popen([sys.executable, script_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"Error running {script_name}: {stderr.decode('utf-8')}")
    else:
        print(f"Output of {script_name}: {stdout.decode('utf-8')}")

def main():
    install_packages()
    while True:
        print("Starting V1_sort.py...")
        run_script('V1_sort.py')
        print("Waiting for 15 seconds before running V2_sheet_sync.py...")
        time.sleep(15)
        print("Starting V2_sheet_sync.py...")
        run_script('V2_sheet_sync.py')
        print("Waiting for 5 minutes before the next cycle...")
        time.sleep(5 * 60)  # Wait for 5 minutes

if __name__ == "__main__":
    main()
