# -*- coding: utf-8 -*-
import os
import time
import datetime
import subprocess
import sys

# Handle configparser for both Python 2 and 3
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

# Read the configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# Extract configuration details
if sys.version_info[0] < 3:
    test_name = config.get('DEFAULT', 'TestName')
    vm_host = config.get('VMHost', 'Host')
    irmc_host = config.get('iRMC', 'Host')
    irmc_user = config.get('iRMC', 'User')
    irmc_password = config.get('iRMC', 'Password')
    LOOP = config.getint('DEFAULT', 'Loop')
    OFFTIME = config.getint('DEFAULT', 'OffTime')
else:
    test_name = config['DEFAULT']['TestName']
    vm_host = config['VMHost']['Host']
    irmc_host = config['iRMC']['Host']
    irmc_user = config['iRMC']['User']
    irmc_password = config['iRMC']['Password']
    LOOP = int(config['DEFAULT']['Loop'])
    OFFTIME = int(config['DEFAULT']['OffTime'])

RETRY_COUNT = 3
RETRY_INTERVAL = 30

FLGFILE = 'DELETE-TO-STOP-RUNNING'

def echo_time(script_name, message):
    """Print a timestamped message to the terminal with the script name."""
    print("[{}] {}: {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), script_name, message))

def log_message(script_name, message, log, cycle_count):
    """Log a timestamped message to the log file with the script name and cycle count."""
    formatted_message = "[{}] {} Cycle {}: {}\n".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), script_name, cycle_count, message)
    log.write(formatted_message)
    log.flush()  # Ensure immediate write to the file

def run_command_with_retries(command, log, cycle_count, operation, script_name, shell=False):
    """Run a shell command with retries, logging the outcome."""
    attempts = 0
    while attempts < RETRY_COUNT:
        try:
            log_message(script_name, "Executing command: {} for operation: {}".format(' '.join(command), operation), log, cycle_count)
            output = subprocess.check_output(command, shell=shell)
            log.write(output.decode('utf-8') if sys.version_info[0] >= 3 else output)
            log_message(script_name, "Completed: {}".format(operation), log, cycle_count)
            return True  # Indicates success
        except subprocess.CalledProcessError as e:
            attempts += 1
            error_message = "Attempt {}/{}: Command failed with error: {} for operation: {}".format(attempts, RETRY_COUNT, e, operation)
            echo_time(script_name, error_message)
            log_message(script_name, error_message, log, cycle_count)
            if attempts < RETRY_COUNT:
                time.sleep(RETRY_INTERVAL)
    final_error_message = "Command failed after {} attempts for operation: {}".format(RETRY_COUNT, operation)
    log_message(script_name, final_error_message, log, cycle_count)
    return False  # Indicates failure

def touch(file):
    """Create an empty file or update the timestamp of an existing file."""
    with open(file, 'a'):
        os.utime(file, None)

def remove(file):
    """Remove a file if it exists."""
    if os.path.exists(file):
        os.remove(file)

# Create base directory for all tests
BASE_LOGPATH = 'VM_Reboot_Cycle_log'
if not os.path.exists(BASE_LOGPATH):
    os.makedirs(BASE_LOGPATH)

# Find the next available Test directory
test_count = 1
while os.path.exists(os.path.join(BASE_LOGPATH, 'Test{}'.format(test_count))):
    test_count += 1

# Create a directory for the current test
TEST_LOGPATH = os.path.join(BASE_LOGPATH, 'Test{}'.format(test_count))
os.makedirs(TEST_LOGPATH)

touch(FLGFILE)

LOGFILE = os.path.join(TEST_LOGPATH, 'combined_log.txt')

with open(LOGFILE, 'a') as log:
    script_name = 'VM_Reboot'
    for CNT in range(1, LOOP + 1):
        if not os.path.exists(FLGFILE):
            break

        echo_time(script_name, "******* {}/{} start *******".format(CNT, LOOP))
        log_message(script_name, "******* {}/{} start *******".format(CNT, LOOP), log, CNT)

        echo_time(script_name, "******* Reboot Server *******")
        log_message(script_name, "******* Reboot Server *******", log, CNT)
        success = run_command_with_retries(['python', 'reboot-all.py'], log, CNT, "Reboot Server", script_name)
        if not success:
            echo_time(script_name, "Critical failure, stopping test.")
            log_message(script_name, "Critical failure, stopping test.", log, CNT)
            sys.exit(1)

        echo_time(script_name, "******* Sleep while reboot *******")
        log_message(script_name, "******* Sleep while reboot *******", log, CNT)
        time.sleep(OFFTIME)

        echo_time(script_name, "******* Waiting Power On *******")
        log_message(script_name, "******* Waiting Power On *******", log, CNT)
        try:
            subprocess.check_call(['python', 'wait_bootup_all.py'])
            log_message(script_name, "Completed: Waiting Power On", log, CNT)
        except subprocess.CalledProcessError as e:
            error_message = "Wait bootup script failed with error: {}".format(e)
            echo_time(script_name, error_message)
            log_message(script_name, error_message, log, CNT)
            echo_time(script_name, "Critical failure, stopping test.")
            log_message(script_name, "Critical failure, stopping test.", log, CNT)
            sys.exit(1)

        echo_time(script_name, "******* Waiting Boot OS *******")
        log_message(script_name, "******* Waiting Boot OS *******", log, CNT)
        time.sleep(OFFTIME)

        echo_time(script_name, "******* Check RAID Status *******")
        log_message(script_name, "******* Check RAID Status *******", log, CNT)
        success = run_command_with_retries(['python', 'check_vmware.py', str(CNT), TEST_LOGPATH], log, CNT, "Check RAID Status", script_name)
        if not success:
            echo_time(script_name, "Critical failure, stopping test.")
            log_message(script_name, "Critical failure, stopping test.", log, CNT)
            sys.exit(1)

        echo_time(script_name, "******* {}/{} end *******".format(CNT, LOOP))
        log_message(script_name, "******* {}/{} end *******".format(CNT, LOOP), log, CNT)

    log_message(script_name, "Completed {} cycles for Test{}.".format(LOOP, test_count), log, CNT)

remove(FLGFILE)
