import subprocess

try:
    subprocess.check_call(['python', 'ipmi.py', 'power', 'on'])
except subprocess.CalledProcessError as e:
    error_message = "Power-on command failed with error: {}".format(e)
    print(error_message)
    sys.exit(1)  # Exit on failure
