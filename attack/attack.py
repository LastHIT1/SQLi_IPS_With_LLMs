import requests
import argparse
import sys
import time
import csv

class bcolors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
def attack(url, payload_file, mode, delay=0.05):
    PARAM = "q"

    mode_names = {
        1: "No_Security",
        2: "LLM Only",
        3: "ML Only",
        4: "Filter Only"
    }

    csv_filename = f"attack_results_mode_{mode}_{mode_names[mode]}.csv"

    print(f"{bcolors.HEADER}[*] Starting attack on target: {url}")
    print(f"[*] with mode: {mode} ({mode_names[mode]}){bcolors.ENDC}")
    print(f"-" * 55)

    try:
        with open(payload_file, "r", encoding='utf-8') as f:
            payloads = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"{bcolors.FAIL}Payload file not found: {payload_file}{bcolors.ENDC}")
        sys.exit(1)
    
    session = requests.Session()
    session.headers.update({"User-Agent": "SQLi-Attack-Script/1.0"})

    with open(csv_filename, "w", newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Mode","Payload", "Status", "Latency(s)"])

        for payload in payloads:
            data = {PARAM: payload}
            status_text = "UNKNOWN"
            latency = 0.0

            try:
                start_time = time.perf_counter()

                response = session.get(url, params=data, timeout=5)

                end_time = time.perf_counter()
                latency = end_time - start_time
                
                if response.status_code == 403 or "Security Alert" in response.text or "Threat type classification" in response.text:
                    status_text = "BLOCKED"
                    print(f"{bcolors.FAIL}[BLOCKED] {bcolors.ENDC} {payload}")

                elif "database error" in response.text.lower() or "unterminated quoted string" in response.text.lower() or "syntax error" in response.text.lower():
                    status_text = "VULNERABLE"
                    print(f"{bcolors.WARNING}[VULNERABLE] {bcolors.ENDC} {payload}")

                elif response.status_code == 200:
                    status_text = "PASSED"
                    print(f"{bcolors.OKGREEN}[PASSED] {bcolors.ENDC} {payload}")
                else:
                    print(f"{bcolors.HEADER}[UNKNOWN] {bcolors.ENDC} {payload} - Status Code: {response.status_code}")

            except requests.RequestException as e:
                status_text = "ERROR"
                print(f"{bcolors.FAIL}[ERROR] Connection Refused or Timeout: {e}{bcolors.ENDC}")
                writer.writerow([mode, payload, status_text, 0.0])
                break

            writer.writerow([mode, payload, status_text, f"{latency:.4f}"])

            time.sleep(delay)
    print("-" * 60)
    print(f"Results saved to {csv_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform a brute-force attack on a login page.")
    parser.add_argument("--url", default="http://localhost:8080/", help="Target URL")
    parser.add_argument("--file", default="payloads.txt", help="File with payloads")
    parser.add_argument("mode", type=int, choices=[1, 2, 3, 4], help="Select test mode: 1 = No Security, 2 = LLM Only, 3 = ML Only, 4 = Filter Only")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between requests in seconds")

    args = parser.parse_args()

    attack(args.url, args.file, args.mode, args.delay)