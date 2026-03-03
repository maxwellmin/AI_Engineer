#!/usr/bin/env python3
"""Start Django server as a subprocess."""

import subprocess
import sys
import os
import time

# Change to project directory
os.chdir('/Users/maxrocketman/myproject/melon')

# Set environment
env = os.environ.copy()
env['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'

# Start server
print("Starting Django server...", flush=True)
process = subprocess.Popen(
    ['poetry', 'run', 'python', 'manage.py', 'runserver', '8000'],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Wait a bit for server to start
time.sleep(3)

# Check if server is running
if process.poll() is None:
    print(f"Django server started successfully (PID: {process.pid})", flush=True)
    print("Server is running on http://localhost:8000", flush=True)

    # Keep the script running to maintain the server
    try:
        # Read and print server output
        for line in process.stdout:
            print(line, end='', flush=True)
    except KeyboardInterrupt:
        print("\nStopping server...", flush=True)
        process.terminate()
        process.wait()
else:
    print(f"Server failed to start (exit code: {process.returncode})", flush=True)
    print("Output:", flush=True)
    print(process.stdout.read(), flush=True)
    sys.exit(1)
