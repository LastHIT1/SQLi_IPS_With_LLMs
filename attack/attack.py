import requests
import argparse
import sys
import time
import csv

# Color for terminal output
class bcolors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def attack(url, payload_file, mode, delay=0.05):
    PARAM = "q"
    
    # What security feature is on
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

    state = {
        "TP": 0,
        "FN": 0,
        "TN": 0,
        "FP": 0
    }

    payload_data =[]

    # Open csv file
    try:
        with open(payload_file, "r", encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    payload_data.append((row[0].strip(), row[1].strip().lower()))
    except FileNotFoundError:
        print(f"{bcolors.FAIL}Payload file not found: {payload_file}{bcolors.ENDC}")
        sys.exit(1)

    session = requests.Session()
    session.headers.update({"User-Agent": "SQLi-Attack-Script/1.0"})

    with open(csv_filename, "w", newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Mode","Payload", "Expected", "Status", "Latency(s)", "Classification"])

        for payload, expected_type in payload_data:
            data = {PARAM: payload}
            status_text = "N/A"
            latency = 0.0
            classification = "N/A"

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

                is_malicious = expected_type == "malicious"
                is_blocked = status_text == "BLOCKED"

                if is_malicious:
                    if is_blocked:
                        state["TP"] += 1
                        classification = "True Positive"
                        color = bcolors.OKGREEN
                    else:
                        state["FN"] += 1
                        classification = "False Negative"
                        color = bcolors.FAIL
                else:
                    if is_blocked:
                        state["FP"] += 1
                        classification = "False Positive"
                        color = bcolors.WARNING
                    else:
                        state["TN"] += 1
                        classification = "True Negative"
                        color = bcolors.OKGREEN

                print(f"{color}[{classification}] Exp:{expected_type} -> Got:{status_text} | {payload[:40]}...{bcolors.ENDC}")
                
            except requests.RequestException as e:
                status_text = "ERROR"
                print(f"{bcolors.FAIL}[ERROR] Connection Refused or Timeout: {e}{bcolors.ENDC}")
                writer.writerow([mode, payload, expected_type, status_text, 0.0, "ERROR"])
                break

            writer.writerow([mode, payload, expected_type, status_text, f"{latency:.4f}", classification])

            time.sleep(delay)
    print("-" * 60)
    print(f"Results saved to {csv_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform a brute-force attack on a login page.")
    parser.add_argument("--url", default="http://localhost:8080/", help="Target URL")
    parser.add_argument("--file", default="payloads.csv", help="File with payloads")
    parser.add_argument("mode", type=int, choices=[1, 2, 3, 4], help="Select test mode: 1 = No Security, 2 = LLM Only, 3 = ML Only, 4 = Filter Only")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between requests in seconds")

    args = parser.parse_args()

    attack(args.url, args.file, args.mode, args.delay)
