# -*- coding: utf-8 -*-
import os
import datetime
import subprocess
import sys
import time

try:
    import configparser  # Python 3
except ImportError:
    import ConfigParser as configparser  # Python 2

# Read the configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# Extract configuration details
if sys.version_info[0] < 3:
    test_name = config.get('DEFAULT', 'TestName')
    vm_host = config.get('VMHost', 'Host')
    RAID_OFFTIME = config.getint('DEFAULT', 'RAIDOffTime')
else:
    test_name = config['DEFAULT']['TestName']
    vm_host = config['VMHost']['Host']
    RAID_OFFTIME = config.getint('DEFAULT', 'RAIDOffTime')

RETRY_COUNT = 3
RETRY_INTERVAL = 30

def echo_time(message):
    print("[{}]: {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))

def log_message(message, log, cycle_count):
    formatted_message = "[{}] Cycle {}: {}\n".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cycle_count, message)
    log.write(formatted_message)
    log.flush()  # 確保立即寫入文件

def run_command_with_retries(command, log, cycle_count, operation, shell=False):
    attempts = 0
    while attempts < RETRY_COUNT:
        try:
            log_message("Executing command: {} for operation: {}".format(' '.join(command), operation), log, cycle_count)
            output = subprocess.check_output(command, shell=shell)
            log.write(output.decode('utf-8') if sys.version_info[0] >= 3 else output)
            log_message("Completed: {}".format(operation), log, cycle_count)
            return True  # Indicates success
        except subprocess.CalledProcessError as e:
            attempts += 1
            error_message = "Attempt {}/{}: Command failed with error: {} for operation: {}".format(attempts, RETRY_COUNT, e, operation)
            echo_time(error_message)
            log_message(error_message, log, cycle_count)
            if attempts < RETRY_COUNT:
                time.sleep(RETRY_INTERVAL)
    final_error_message = "Command failed after {} attempts for operation: {}".format(RETRY_COUNT, operation)
    log_message(final_error_message, log, cycle_count)
    return False  # Indicates failure

def grep_vmkernel_errors(cycle_count, log):
    command = ['ssh', vm_host, 'grep -i "error\\|fail\\|warning\\|panic" /var/log/vmkernel.log']
    try:
        errors = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=False)
        log_message("Cycle {} vmkernel-log: \n{}".format(cycle_count, errors.decode('utf-8') if sys.version_info[0] >= 3 else errors), log, cycle_count)
    except subprocess.CalledProcessError as e:
        log_message("Error extracting vmkernel logs: {}".format(e), log, cycle_count)

# Get cycle_count and TEST_LOGPATH from command line arguments
cycle_count = int(sys.argv[1])
TEST_LOGPATH = sys.argv[2]

LOGFILE = os.path.join(TEST_LOGPATH, 'combined_log.txt')

with open(LOGFILE, 'a') as log:
    # Write the header for each cycle
    log_message("###########################################################", log, cycle_count)
    log_message("######                 CYCLE {} START                  ######".format(cycle_count), log, cycle_count)
    log_message("###########################################################", log, cycle_count)
    log_message("{} Test".format(test_name), log, cycle_count)
    log_message("Loop: {} / {}".format(cycle_count, config.getint('DEFAULT', 'Loop')), log, cycle_count)
    log_message("Start Date: {}".format(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')), log, cycle_count)
    log_message("###########################################################", log, cycle_count)

    commands = [
        ['ssh', vm_host, 'vmware -v'],
        ['ssh', vm_host, 'esxcli hardware platform get'],
        ['ssh', vm_host, 'esxcli hardware ipmi bmc get'],
        ['ssh', vm_host, 'esxcli storage core path list'],
        ['ssh', vm_host, 'esxcli storage core device list'],
        ['ssh', vm_host, 'df -h'],
        ['ssh', vm_host, 'lspci'],
        ['ssh', vm_host, 'esxcli system module list'],
        ['ssh', vm_host, 'esxcli software vib list'],
        ['ssh', vm_host, 'vmkload_mod -s lsi_msgpt3'],
        ['ssh', vm_host, 'vmkload_mod -l'],
        ['ssh', vm_host, 'esxcli storage filesystem list'],
        ['ssh', vm_host, 'vim-cmd vmsvc/getallvms'],
        ['ssh', vm_host, 'grep -i "error\\|fail\\|warning\\|panic" /var/log/vmkernel.log']
    ]

    for command in commands:
        success = run_command_with_retries(command, log, cycle_count, ' '.join(command))
        if not success:
            echo_time("Critical failure, stopping test.")
            log_message("Critical failure, stopping test.", log, cycle_count)
            sys.exit(1)

    # Write the footer for each cycle
    log_message("###########################################################", log, cycle_count)
    log_message("######                  CYCLE {} END                   ######".format(cycle_count), log, cycle_count)
    log_message("###########################################################", log, cycle_count)
    log_message("End Date: {}".format(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')), log, cycle_count)
    log_message("###########################################################", log, cycle_count)

    # Clear vmkernel.log
    log_message("Clearing vmkernel.log", log, cycle_count)
    try:
        subprocess.check_call(['ssh', vm_host, 'echo "" > /var/log/vmkernel.log'])
        log_message("Cleared vmkernel.log", log, cycle_count)
    except subprocess.CalledProcessError as e:
        log_message("Clearing vmkernel.log failed with error: {}".format(e), log, cycle_count)
        log_message("Critical failure, stopping test.", log, cycle_count)
        sys.exit(1)

    # Wait for the specified RAID_OFFTIME
    time.sleep(RAID_OFFTIME)
