import time
import csv
import datetime
import subprocess
import json
import urllib.request
import urllib.error
import sys
import os

# Configuration
API_URL = "http://localhost:8000/api/health"
GO2RTC_URL = "http://localhost:1984/api/streams"
REPORT_FILE = "stress_test_report.csv"
CHECK_INTERVAL = 60  # seconds

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def check_api_health():
    try:
        with urllib.request.urlopen(API_URL, timeout=5) as response:
            if response.status == 200:
                return "OK", response.read().decode('utf-8')
            else:
                return "FAIL", f"Status Code: {response.status}"
    except Exception as e:
        return "ERROR", str(e)

def check_go2rtc_streams():
    try:
        with urllib.request.urlopen(GO2RTC_URL, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                # Expecting data to be a dict of streams
                stream_count = len(data) if isinstance(data, dict) else 0
                return "OK", stream_count, data
            else:
                return "FAIL", 0, {}
    except Exception as e:
        return "ERROR", 0, str(e)

def get_docker_stats():
    try:
        # Get stats for all running containers
        # Format: Name, Memory Percentage, CPU Percentage
        cmd = ["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.MemPerc}}|{{.CPUPerc}}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        stats = {}
        for line in result.stdout.strip().split('\n'):
            if not line: continue
            parts = line.split('|')
            if len(parts) == 3:
                name = parts[0]
                mem = parts[1]
                cpu = parts[2]
                stats[name] = f"Mem: {mem}, CPU: {cpu}"
        return stats
    except Exception as e:
        return {"error": str(e)}

def check_logs_for_errors():
    try:
        # Check logs of the last minute for errors
        cmd = ["docker-compose", "logs", "--since", "1m"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        error_count = 0
        output = result.stdout + result.stderr
        
        for line in output.split('\n'):
            if "Error" in line or "Exception" in line or "Traceback" in line:
                error_count += 1
                
        return error_count
    except Exception as e:
        print(f"Error checking logs: {e}")
        return -1

def init_csv():
    headers = ["Timestamp", "API_Status", "Stream_Count", "Docker_Stats", "Log_Errors", "Notes"]
    
    # Create file with headers if it doesn't exist
    if not os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

def log_to_csv(row):
    with open(REPORT_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(row)

def main():
    print(f"Starting stress test... Output: {REPORT_FILE}")
    init_csv()
    
    while True:
        timestamp = get_timestamp()
        
        # 1. API Health
        api_status, api_details = check_api_health()
        
        # 2. Streams
        stream_status, stream_count, stream_details = check_go2rtc_streams()
        
        # 3. Docker Stats
        docker_stats = get_docker_stats()
        docker_stats_str = json.dumps(docker_stats)
        
        # 4. Logs
        log_errors = check_logs_for_errors()
        
        # Console Output & Critical Alerts
        print(f"[{timestamp}] API: {api_status} | Streams: {stream_count} | Log Errors: {log_errors}")
        
        if api_status != "OK":
            print(f"\033[91mCRITICAL: API is DOWN! ({api_details})\033[0m")
        
        if stream_status != "OK":
             print(f"\033[91mCRITICAL: Stream API issue! ({stream_details})\033[0m")
        elif stream_count < 3:
             # Assuming we expect 3 cameras as per prompt
             print(f"\033[91mWARNING: Only {stream_count}/3 streams active!\033[0m")
             
        # Log to CSV
        log_to_csv([timestamp, api_status, stream_count, docker_stats_str, log_errors, ""])
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping stress test.")
