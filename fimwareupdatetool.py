# -*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function

import os
import time
import logging
import subprocess
import sys
from threading import Timer

# Base directory for the script
BASE_DIR = "C:\\Users\\Administrator\\Documents\\Broadcom\\FW\\Win"

# Configure logging
LOG_FILE = os.path.join(BASE_DIR, 'fw_update_test.log')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
file_handler = logging.FileHandler(LOG_FILE)
stream_handler = logging.StreamHandler(sys.stdout)
logging.getLogger().addHandler(file_handler)
logging.getLogger().addHandler(stream_handler)

# Define FW paths
FW_PATHS = {
    "Old": os.path.join(BASE_DIR, "Old"),
    "New": os.path.join(BASE_DIR, "New")
}

# Full path to storcli64.exe
STORCLI_PATH = os.path.join(BASE_DIR, "storcli64.exe")

# FW download commands
FW_COMMANDS = {
    "Old": "{} /c0 download file=PRAID_CP600i_NOPAD.rom noverchk".format(STORCLI_PATH),
    "New": "{} /c0 download file=PRAID_CP600i_NOPAD.rom noverchk".format(STORCLI_PATH)
}

# State file to track the progress
STATE_FILE = os.path.join(BASE_DIR, "fw_update_state.txt")
# Results file to store FW update results
RESULTS_FILE = os.path.join(BASE_DIR, "fw_update_results.txt")

def get_timestamp():
    # Returns the current local time formatted as a string
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def reset_device():
    # Logs the reboot action and reboots the device immediately
    logging.info("Rebooting the device")
    os.system('shutdown /r /t 0')


#def reboot_and_wait():
    # Calls reset_device to reboot and logs the waiting period
    reset_device()
    sys.stdout.write("Waiting for device to reboot...\n")
    sys.stdout.flush()
    logging.info("Waiting for device to reboot for 90 seconds")
    time.sleep(90)  # Wait for 90 seconds to ensure the device is fully rebooted


def reboot_and_wait():
    # Logs the reboot action and initiates device reboot
    reset_device()
    sys.stdout.write("Device is rebooting...\n")
    sys.stdout.flush()
    logging.info("Device reboot initiated")

    # Wait for 90 seconds to ensure the system has fully initialized after reboot
    logging.info("Waiting for 90 seconds to allow the system to fully initialize after reboot")
    time.sleep(90)  # Wait for 90 seconds to allow the system to fully initialize

    sys.stdout.write("System initialization complete, proceeding to next step...\n")
    sys.stdout.flush()
    logging.info("System initialization complete, proceeding to next step")


def update_firmware(version):
    # Updates the firmware to the specified version ('old' or 'new')
    logging.info("Starting FW update to {} version".format(version))
    path = FW_PATHS[version]
    os.chdir(path)
    command = FW_COMMANDS[version]
    
    def kill_proc(proc):
        # Kills the process if it runs longer than 300 seconds
        proc.kill()
        logging.error("FW update timed out")
        print("FW update timed out")

    result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timer = Timer(300, kill_proc, [result])  # Set timeout to 300 seconds
    try:
        timer.start()
        stdout, stderr = result.communicate()
        output = stdout.decode('utf-8')
        logging.info("FW update output: {}".format(output))
        if result.returncode == 0 and "Status = Success" in output:
            logging.info("FW update completed successfully, waiting for 10 seconds...")
            time.sleep(10)
            return True
        else:
            logging.error("FW update failed: {}".format(stderr.decode('utf-8')))
            print("FW update failed: {}".format(stderr.decode('utf-8')))
            return False
    except Exception as e:
        result.kill()
        stdout, stderr = result.communicate()
        logging.error("FW update error: {}".format(str(e)))
        print("FW update error: {}".format(str(e)))
        return False
    finally:
        timer.cancel()

def check_firmware(expected_fw_version, expected_package_version):
    logging.info("Checking FW version")
    check_command = '{} /c0 show | findstr /c:FW'.format(STORCLI_PATH)
    
    def kill_proc(proc):
        proc.kill()
        logging.error("FW check timed out")
        print("FW check timed out")

    result = subprocess.Popen(check_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timer = Timer(120, kill_proc, [result])  # Set timeout to 120 seconds
    try:
        timer.start()
        stdout, stderr = result.communicate()
        output = stdout.decode('utf-8')
        if result.returncode == 0:
            logging.info("FW check output: {}".format(output))
            if expected_fw_version in output and expected_package_version in output:
                logging.info("FW version {} and package version {} found".format(expected_fw_version, expected_package_version))
                return True, output
            else:
                logging.error("Expected FW version {} or package version {} not found".format(expected_fw_version, expected_package_version))
                return False, output
        else:
            logging.error("Error checking firmware: {}".format(stderr.decode('utf-8')))
            print("Error checking firmware: {}".format(stderr.decode('utf-8')))
            return False, stderr.decode('utf-8')
    except Exception as e:
        result.kill()
        stdout, stderr = result.communicate()
        logging.error("FW check error: {}".format(str(e)))
        print("FW check error: {}".format(str(e)))
        return False, str(e)
    finally:
        timer.cancel()

def compare_versions(version1, version2):
    v1 = [int(x) for x in version1.split('.')]
    v2 = [int(x) for x in version2.split('.')]
    return v1 < v2

def print_firmware_info(expected_fw_version, expected_package_version):
    success, fw_info = check_firmware(expected_fw_version, expected_package_version)
    if success:
        sys.stdout.write(fw_info + '\n')
        sys.stdout.flush()
        logging.info("Current FW Info: {}".format(fw_info))
    return success, fw_info

def read_state():
    # Reads the current state from the STATE_FILE
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = f.read().strip()
                if state:
                    return state.split(",")
        except Exception as e:
            logging.error("Error reading state file: {}".format(str(e)))
    return [0, "start"]

def write_state(iteration, step):
    # Writes the current iteration and step to the STATE_FILE
    try:
        with open(STATE_FILE, "w") as f:
            f.write("{},{}".format(iteration, step))
    except Exception as e:
        logging.error("Error writing state file: {}".format(str(e)))

def write_results(iteration, step, status, fw_info=""):
    # Writes the results of the current step to the RESULTS_FILE
    try:
        with open(RESULTS_FILE, "a") as f:
            f.write("Cycle {}: Step {} - {}\n".format(iteration, step, status))
            if fw_info:
                f.write("FW Info: {}\n".format(fw_info))
            f.write("\n")
    except Exception as e:
        logging.error("Error writing results file: {}".format(str(e)))

def main():
    current_iteration, current_step = read_state()
    current_iteration = int(current_iteration)
    total_iterations = 10  # Modify this line to adjust the number of iterations

    old_fw_version = "5.260.01-3921"
    old_package_version = "52.26.0-5122"
    new_fw_version = "5.280.01-3981"
    new_package_version = "52.28.0-5358"

    while current_iteration < total_iterations:
        iteration_number = current_iteration + 1
        timestamp = get_timestamp()

        if current_step == "start":
            # Step 1: Downgrade FW to old version
            sys.stdout.write("Cycle {} ({}): Downgrading to old FW\n".format(iteration_number, timestamp))
            sys.stdout.flush()
            logging.info("Cycle {} ({}): Downgrading to old FW".format(iteration_number, timestamp))
            update_result = update_firmware("Old")
            if update_result:
                sys.stdout.write("Cycle {} ({}): Downgrade to old FW successful\n".format(iteration_number, timestamp))
                sys.stdout.flush()
                logging.info("Downgrade to old FW successful for cycle {}".format(iteration_number))
                write_state(current_iteration, "post_downgrade_reboot")
                write_results(iteration_number, "1", "Downgrade ok")
                reboot_and_wait()
                return  # Exit to allow the system to reboot
            else:
                sys.stdout.write("Cycle {} ({}): Downgrade to old FW failed\n".format(iteration_number, timestamp))
                sys.stdout.flush()
                logging.error("Downgrade to old FW failed for cycle {}".format(iteration_number))
                write_results(iteration_number, "1", "Downgrade failed")
                return  # Stop the script if update fails

        elif current_step == "post_downgrade_reboot":
            # Step 2: Verify downgrade
            sys.stdout.write("Cycle {} ({}): Verifying downgrade\n".format(iteration_number, timestamp))
            sys.stdout.flush()
            logging.info("Cycle {} ({}): Verifying downgrade".format(iteration_number, timestamp))
            try:
                success, fw_info = print_firmware_info(old_fw_version, old_package_version)
                if success:
                    logging.info("Post-reboot FW check successful for old FW cycle {}".format(iteration_number))
                    sys.stdout.write("Cycle {} ({}): Post-reboot FW check successful for old FW\n".format(iteration_number, timestamp))
                    sys.stdout.flush()
                    write_results(iteration_number, "2", "Reboot and verify ok", fw_info)
                    write_state(current_iteration, "upgrade_fw")
                    current_step = "upgrade_fw"  # Update current_step to proceed to the next step
                else:
                    logging.error("Post-reboot FW check failed for old FW cycle {}".format(iteration_number))
                    sys.stdout.write("Cycle {} ({}): Post-reboot FW check failed for old FW\n".format(iteration_number, timestamp))
                    sys.stdout.flush()
                    write_results(iteration_number, "2", "Reboot and verify failed", fw_info)
                    return  # Stop the script if check fails
            except subprocess.CalledProcessError:
                logging.error("Post-reboot FW check failed for old FW cycle {}".format(iteration_number))
                sys.stdout.write("Cycle {} ({}): Post-reboot FW check failed for old FW\n".format(iteration_number, timestamp))
                sys.stdout.flush()
                write_results(iteration_number, "2", "Reboot and verify failed")
                return  # Stop the script if check fails

        elif current_step == "upgrade_fw":
            # Step 3: Upgrade FW to new version
            sys.stdout.write("Cycle {} ({}): Upgrading to new FW\n".format(iteration_number, timestamp))
            sys.stdout.flush()
            logging.info("Cycle {} ({}): Upgrading to new FW".format(iteration_number, timestamp))
            update_result = update_firmware("New")
            if update_result:
                sys.stdout.write("Cycle {} ({}): Upgrade to new FW successful\n".format(iteration_number, timestamp))
                sys.stdout.flush()
                logging.info("Upgrade to new FW successful for cycle {}".format(iteration_number))
                write_state(current_iteration, "post_upgrade_reboot")
                write_results(iteration_number, "3", "Upgrade ok")
                reboot_and_wait()
                return  # Exit to allow the system to reboot
            else:
                sys.stdout.write("Cycle {} ({}): Upgrade to new FW failed\n".format(iteration_number, timestamp))
                sys.stdout.flush()
                logging.error("Upgrade to new FW failed for cycle {}".format(iteration_number))
                write_results(iteration_number, "3", "Upgrade failed")
                return  # Stop the script if update fails

        elif current_step == "post_upgrade_reboot":
            # Step 4: Verify upgrade
            sys.stdout.write("Cycle {} ({}): Verifying upgrade\n".format(iteration_number, timestamp))
            sys.stdout.flush()
            logging.info("Cycle {} ({}): Verifying upgrade".format(iteration_number, timestamp))
            try:
                success, fw_info = print_firmware_info(new_fw_version, new_package_version)
                if success:
                    logging.info("Post-reboot FW check successful for new FW cycle {}".format(iteration_number))
                    sys.stdout.write("Cycle {} ({}): Post-reboot FW check successful for new FW\n".format(iteration_number, timestamp))
                    sys.stdout.flush()
                    write_results(iteration_number, "4", "Reboot and verify ok", fw_info)
                    # Increment the iteration and update the state
                    current_iteration += 1
                    write_state(current_iteration, "start")
                    current_step = "start"  # Reset current_step to start the next iteration
                else:
                    logging.error("Post-reboot FW check failed for new FW cycle {}".format(iteration_number))
                    sys.stdout.write("Cycle {} ({}): Post-reboot FW check failed for new FW\n".format(iteration_number, timestamp))
                    sys.stdout.flush()
                    write_results(iteration_number, "4", "Reboot and verify failed", fw_info)
                    return  # Stop the script if check fails
            except subprocess.CalledProcessError:
                logging.error("Post-reboot FW check failed for new FW cycle {}".format(iteration_number))
                sys.stdout.write("Cycle {} ({}): Post-reboot FW check failed for new FW\n".format(iteration_number, timestamp))
                sys.stdout.flush()
                write_results(iteration_number, "4", "Reboot and verify failed")
                return  # Stop the script if check fails

    logging.info("FW update tests completed")
    # Remove state file after completion
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

if __name__ == '__main__':
    main()
