from __future__ import print_function
import subprocess
import sys
import time

# Ensure compatibility with Python 2 and 3 for input()
try:
    input_func = raw_input  # Python 2 uses raw_input()
except NameError:
    input_func = input  # Python 3 uses input()

def fdisk_device_list():
    def is_boot_device(device_path):
        """Check if the device or its partition is a boot or root device"""

        cmd = ['lsblk', '-o', 'NAME,MOUNTPOINT', device_path]

        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            # Ensure compatibility with Python 2 & 3
            if isinstance(output, bytes):
                output = output.decode('utf-8')
        except subprocess.CalledProcessError as e:
            # Ensure compatibility with Python 2 & 3
            error_output = e.output
            if isinstance(error_output, bytes):
                error_output = error_output.decode('utf-8')
            print("Error fetching info for {}: {}".format(device_path, error_output.strip()))
            return False

        for line in output.splitlines():
            columns = line.split()
            if len(columns) == 2 and (columns[1] == "/boot" or columns[1] == "/"):
                return True

        return False

    # Run fdisk to list all disks
    p1 = subprocess.Popen(['fdisk', '-l'], stdout=subprocess.PIPE)
    fdisk_output = p1.communicate()[0]
    if isinstance(fdisk_output, bytes):  # Ensure compatibility with both Python versions
        fdisk_output = fdisk_output.decode('utf-8')
    
    # Get a list of disks excluding mapper devices
    all_disks = [line.split()[1].rstrip(':') for line in fdisk_output.splitlines() if line.startswith("Disk /dev") and not line.startswith("Disk /dev/mapper/")]

    # Sort the disk list
    all_disks.sort()

    # Exclude boot devices
    disks_to_show = [disk for disk in all_disks if not is_boot_device(disk)]

    # Display available disks
    for idx, disk in enumerate(disks_to_show, 0):
        print("{}. {}".format(idx, disk))

    try:
        # Ask user to select the disks or press * to select all
        selected_indices = input_func("Please input the device numbers to use (e.g., '0 1 2') or '*' to select all: ")
        if selected_indices.strip() == "*":
            selected_disks = disks_to_show  # Select all disks
        else:
            selected_disks = [disks_to_show[int(idx)] for idx in selected_indices.split()]
    except (ValueError, IndexError):
        print("Invalid input. Please provide correct device numbers.")
        return []

    return selected_disks

def clean_drive():
    # Get the list of disks to clean
    disk_list = fdisk_device_list()
    for i, disks in enumerate(disk_list):
        # Step 1: Show which disk is being processed
        print('Cleaning {}:{}'.format(i, disks))
        time.sleep(1)

        # Step 2: Use parted to clean the disk by creating a new GPT partition table
        command = ['sudo', 'parted', '-s', disks, 'mklabel', 'gpt']
        try:
            # Execute the command to create a new GPT partition table
            subprocess.check_output(command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            # Ensure compatibility with Python 2 & 3
            error_output = e.output
            if isinstance(error_output, bytes):
                error_output = error_output.decode('utf-8')
            print("Error cleaning {}: {}".format(disks, error_output.strip()))

        time.sleep(1)

if __name__ == '__main__':
    clean_drive()
