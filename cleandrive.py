from __future__ import print_function
import subprocess
import pexpect
import sys
import time
import re

# Ensure compatibility with Python 2 and 3 for input()
try:
    input_func = raw_input  # Python 2
except NameError:
    input_func = input  # Python 3

def is_boot_or_mnt_device(device_path):
    """Check if the device or its partition is a boot device or mounted under /mnt/[device]."""
    cmd = ['lsblk', '-o', 'NAME,MOUNTPOINT', device_path]

    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        if isinstance(output, bytes):
            output = output.decode('utf-8')
    except subprocess.CalledProcessError as e:
        error_output = e.output
        if isinstance(error_output, bytes):
            error_output = error_output.decode('utf-8')
        print("Error fetching info for {}: {}".format(device_path, error_output.strip()))
        return False

    # Get the base name of the device (e.g., sda, sdb)
    base_device = device_path.split('/')[-1]

    # Check if the device is mounted under /mnt or if it is a boot device
    for line in output.splitlines():
        columns = line.split()
        if len(columns) == 2:
            mount_point = columns[1]
            if mount_point == "/" or mount_point == "/boot" or mount_point.startswith("/mnt/{}".format(base_device)):
                return True

    return False

def fdisk_device_list():
    """Get the list of disk devices excluding boot devices and /mnt/[device] devices."""
    p1 = subprocess.Popen(['fdisk', '-l'], stdout=subprocess.PIPE)
    fdisk_output = p1.communicate()[0]
    if isinstance(fdisk_output, bytes):
        fdisk_output = fdisk_output.decode('utf-8')

    # Get a list of disks excluding /dev/mapper
    all_disks = [line.split()[1].rstrip(':') for line in fdisk_output.splitlines() if line.startswith("Disk /dev") and not line.startswith("Disk /dev/mapper/")]

    # Sort the disk list
    all_disks.sort()

    # Exclude boot devices and devices under /mnt/[device]
    disks_to_show = [disk for disk in all_disks if not is_boot_or_mnt_device(disk)]

    # Display available disks
    for idx, disk in enumerate(disks_to_show, 0):
        print("{}. {}".format(idx, disk))

    try:
        # First prompt: select specific disks or all using '*'
        selected_indices = input_func("Please input the device numbers to use (e.g., '0 1 2') or '*' to select all: ")
        if selected_indices.strip() == "*":
            selected_disks = disks_to_show  # Select all disks
        else:
            selected_disks = [disks_to_show[int(idx)] for idx in selected_indices.split()]
    except (ValueError, IndexError):
        print("Invalid input. Please provide correct device numbers.")
        return []

    return selected_disks

def get_device_uuid(device_path):
    """Retrieve the UUID of a device using blkid."""
    output = subprocess.check_output(["blkid", device_path])
    if isinstance(output, bytes):
        output = output.decode('utf-8')
    uuid_match = re.search(r'UUID="(\S+)"', output)
    if uuid_match:
        return uuid_match.group(1)
    else:
        raise ValueError("Could not find UUID for device {}".format(device_path))

def update_fstab(entries):
    """Update /etc/fstab by appending new mount points."""
    # Read current fstab content
    with open("/etc/fstab", "r") as f:
        content = f.read().rstrip()

    # Append new entries to fstab
    new_content = "\n".join(entries)
    full_content = "{}\n{}\n".format(content, new_content)

    # Write the updated content back to /etc/fstab using tee
    cmd = 'echo "{}" | sudo tee /etc/fstab > /dev/null'.format(full_content)
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print("Failed to update /etc/fstab with error:", stderr)
    else:
        print("Fstab updated successfully with the following entries:")
        for entry in entries:
            print(entry)

def main():
    """Main process for formatting and mounting partitions."""
    # First, get the list of non-boot, non-mnt disks
    disk_list = fdisk_device_list()
    if not disk_list:
        print("No disks available for partitioning and mounting.")
        return

    print('Creating and mounting partitions from {} disks...'.format(len(disk_list)))
    i = 0
    fstab_entries = []  # List to store fstab entries

    # Loop through each selected disk
    for disks in disk_list:
        print('{}:{}'.format(i, disks))
        i += 1

        # Create a new partition using gdisk
        child = pexpect.spawn('gdisk ' + disks)
        child.logfile = getattr(sys.stdout, 'buffer', sys.stdout)
        child.sendline('n')
        child.expect('\):')
        child.sendline()  # Use default partition number
        child.expect('\):')
        child.sendline()  # Use default first sector
        child.expect(' ')
        child.sendline()  # Use default last sector
        child.expect('')
        child.sendline()  # Accept default
        child.sendline('w')  # Write the partition table
        child.sendline('y')  # Confirm write
        time.sleep(1)
        child.expect(pexpect.EOF)
        time.sleep(1)

        # Format the partition to ext4
        partition_path = disks + '1'
        mkfs_cmd = 'mkfs -F -t ext4 ' + partition_path
        child = pexpect.spawn(mkfs_cmd, timeout=1800)  # Set timeout to 30 minutes (1800 seconds)
        child.logfile = getattr(sys.stdout, 'buffer', sys.stdout)
        child.expect(pexpect.EOF)

        # Retrieve the UUID and mount the partition
        uuid = get_device_uuid(partition_path)
        mkdir_cmd = 'mkdir /mnt/' + disks[5:]
        mount_cmd = 'mount UUID=' + uuid + ' /mnt/' + disks[5:]
        child = pexpect.spawn(mkdir_cmd)
        child.logfile = getattr(sys.stdout, 'buffer', sys.stdout)
        child.expect(pexpect.EOF)
        child = pexpect.spawn(mount_cmd)
        child.logfile = getattr(sys.stdout, 'buffer', sys.stdout)
        child.expect(pexpect.EOF)
        time.sleep(1)

        # Add the new partition to /etc/fstab
        fstab_entry = 'UUID={} {} ext4 defaults 0 0'.format(uuid, '/mnt/' + disks[5:])
        fstab_entries.append(fstab_entry)

    # Update /etc/fstab after all partitions are created and mounted
    update_fstab(fstab_entries)

if __name__ == '__main__':
    main()
