import hmac
import hashlib
import json
import os

SECRET_KEY = b"SUTTON_STANDARD_SECRET_KEY"
LEDGER_PATH = "vault_audit_ledger.ndjson"

def verify_ledger():
    print("[*] Initializing GLASS MOUTH Cryptographic Chain Verifier...")
    
    if not os.path.exists(LEDGER_PATH):
        print(f"[!] Error: Ledger file '{LEDGER_PATH}' not found.")
        return

    with open(LEDGER_PATH, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print("[+] Ledger is empty.")
        return

    expected_prev_hash = "0" * 64
    chain_intact = True
    verified_count = 0

    for i, line in enumerate(lines):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"[!] Line {i+1}: JSON decode error: {e}")
            chain_intact = False
            continue

        turn_id = rec.get("turn_id")
        violation = rec.get("violation_type")
        payload = rec.get("payload_summary")
        prev_hash = rec.get("prev_hash")
        stored_hash = rec.get("hash")

        # Skip legacy or non-vault log entries if any exist
        if turn_id is None or stored_hash is None:
            continue

        # Verify recursive linkage
        if prev_hash != expected_prev_hash:
            print(f"[!] Chain broken at Turn {turn_id}! Expected prev_hash: {expected_prev_hash[:16]}..., found: {prev_hash[:16]}...")
            chain_intact = False

        # Recompute HMAC-SHA256 signature
        message = f"{turn_id}:{violation}:{payload}:{prev_hash}"
        mac = hmac.new(SECRET_KEY, message.encode("utf-8"), hashlib.sha256)
        computed_hash = mac.hexdigest()

        if computed_hash != stored_hash:
            print(f"[!] Hash mismatch at Turn {turn_id}! Stored: {stored_hash[:16]}..., Computed: {computed_hash[:16]}...")
            chain_intact = False
        else:
            print(f"[+] Turn {turn_id:03d} [{violation}] -> Verified (Hash: {stored_hash[:16]}...)")
            verified_count += 1

        expected_prev_hash = stored_hash

    print("\n" + "="*50)
    if chain_intact:
        print(f"[SUCCESS] Ledger integrity verified. {verified_count} cryptographic turns validated. Zero tampering detected.")
    else:
        print("[ALERT] Integrity violation detected! Cryptographic chain compromised.")
    print("="*50)

if __name__ == "__main__":
    verify_ledger()
