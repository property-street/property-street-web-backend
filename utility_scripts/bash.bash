# Check which process is using a port (e.g., port 8000):
netstat -ano | findstr :8000

# Get the PID (Process ID) of the process using a port:

# Kill the process using that port:
taskkill /PID <> /F
