import os
import time
import datetime
import subprocess

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

# Read the configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# Handle compatibility with Python 2 and 3
try:
    vm_host = config.get('VMHost', 'Host')
except AttributeError:
    vm_host = config['VMHost']['Host']

def echo_time(message):
    print("[{}]: {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))

def log_error(message):
    with open('ssh_errors.log', 'a') as log_file:
        log_file.write("[{}]: {}\n".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))

def waiting_ping_reply():
    count = 60
    while count != 0:
        echo_time("Checking ping reply...")
        try:
            ret = subprocess.check_call(['ping', '-c', '1', '-i', '1', '-w', '1', vm_host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("{} : {}".format(vm_host, "ok" if ret == 0 else "no reply!"))
            if ret == 0:
                echo_time("Ping reply ok.")
                break
        except subprocess.CalledProcessError as e:
            error_message = "Ping failed with error: {}".format(e)
            echo_time(error_message)
            log_error(error_message)
            count -= 1
            time.sleep(60)
    return ret

waiting_ping_reply()
