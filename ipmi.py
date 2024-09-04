import subprocess
import sys

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

# Read the configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# Handle compatibility with Python 2 and 3
try:
    irmc_host = config.get('iRMC', 'Host')
    irmc_user = config.get('iRMC', 'User')
    irmc_password = config.get('iRMC', 'Password')
except AttributeError:
    irmc_host = config['iRMC']['Host']
    irmc_user = config['iRMC']['User']
    irmc_password = config['iRMC']['Password']

if len(sys.argv) < 3:
    print("Usage: python ipmi.py <power> <on|off|status>")
    sys.exit(1)

action = sys.argv[1]
state = sys.argv[2]

if action == 'power' and state in ['on', 'off', 'status']:
    cmd = "ipmitool -H {} -U {} -P {} chassis power {}".format(irmc_host, irmc_user, irmc_password, state)
else:
    print("Invalid command")
    sys.exit(1)

print(cmd)
try:
    subprocess.check_call(cmd, shell=True)
except subprocess.CalledProcessError as e:
    error_message = "IPMI command failed with error: {}".format(e)
    print(error_message)
    sys.exit(1)  # Exit on failure
