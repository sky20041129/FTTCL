import os
import sys
import subprocess
import datetime

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

if len(sys.argv) == 1:
    print("Usage: python cmdall.py <commands>")
    sys.exit()

def echo_time(message):
    print("[{}]: {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))

def log_error(message):
    with open('ssh_errors.log', 'a') as log_file:
        log_file.write("[{}]: {}\n".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))

CMD = ' '.join(sys.argv[1:])

echo_time("ssh {} {}".format(vm_host, CMD))
try:
    subprocess.check_call(['ssh', vm_host, CMD])
except subprocess.CalledProcessError as e:
    error_message = "SSH command failed with error: {}".format(e)
    echo_time(error_message)
    log_error(error_message)
    sys.exit(1)  # Exit on failure
