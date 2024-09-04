import subprocess
import sys

try:
    subprocess.check_call(['python', 'cmdall.py', 'poweroff'])
except subprocess.CalledProcessError as e:
    error_message = "Shutdown command failed with error: {}".format(e)
    print(error_message)
    sys.exit(1)  # Exit on failure
