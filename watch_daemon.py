import time
import os
import json
from master_dispatcher import evaluate_payload, handoff_to_rust_vault

WATCH_FILE = "incoming_payload.json"

def run_watcher():
    print("[*] GLASS MOUTH Background Watcher Daemon Initialized.")
    print(f"[*] Monitoring target: {WATCH_FILE}")
    
    # Initialize a baseline safe payload file if it doesn't exist
    if not os.path.exists(WATCH_FILE):
        baseline = {
            "payload_text": "System initialized. Awaiting telemetry...",
            "dom_attributes": {"opacity": 1.0, "color": "#000000", "background_color": "#ffffff"}
        }
        with open(WATCH_FILE, "w") as f:
            json.dump(baseline, f, indent=2)

    last_mtime = os.path.getmtime(WATCH_FILE)

    try:
        while True:
            time.sleep(1)
            if os.path.exists(WATCH_FILE):
                current_mtime = os.path.getmtime(WATCH_FILE)
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    print("\n[+] New payload telemetry detected. Inspecting...")
                    
                    try:
                        with open(WATCH_FILE, "r") as f:
                            data = json.load(f)
                        
                        payload_text = data.get("payload_text", "")
                        dom_attrs = data.get("dom_attributes", {})
                        
                        violations = evaluate_payload(payload_text, dom_attrs)
                        if violations:
                            print(f"[!] Anomalies flagged: {violations}")
                            for violation in violations:
                                handoff_to_rust_vault(violation, payload_text)
                        else:
                            print("[+] Payload clean. No anomalies detected.")
                    except Exception as e:
                        print(f"[!] Error parsing payload file: {e}")
    except KeyboardInterrupt:
        print("\n[*] Watcher daemon shutting down gracefully.")

if __name__ == "__main__":
    run_watcher()
