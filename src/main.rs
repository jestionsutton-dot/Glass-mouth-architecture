use hmac::{Hmac, Mac};
use sha2::Sha256;
use serde::{Serialize, Deserialize};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::thread;
use std::time::Duration;
use std::env;
use chrono::Utc;

type HmacSha256 = Hmac<Sha256>;

#[derive(Serialize, Deserialize, Debug)]
pub struct AuditRecord {
    pub turn_id: u64,
    pub violation_type: String,
    pub payload_summary: String,
    pub prev_hash: String,
    pub hash: String,
    pub created_at: String,
}

pub struct VaultLedger {
    secret_key: Vec<u8>,
    ledger_file: String,
    last_hash: String,
    turn_counter: u64,
}

impl VaultLedger {
    pub fn new(secret: &str, ledger_path: &str) -> Self {
        let mut ledger = Self {
            secret_key: secret.as_bytes().to_vec(),
            ledger_file: ledger_path.to_string(),
            last_hash: "0".repeat(64),
            turn_counter: 0,
        };
        ledger.load_latest_hash();
        ledger
    }

    fn load_latest_hash(&mut self) {
        if let Ok(content) = fs::read_to_string(&self.ledger_file) {
            if let Some(last_line) = content.lines().last() {
                if let Ok(record) = serde_json::from_str::<AuditRecord>(last_line) {
                    self.last_hash = record.hash;
                    self.turn_counter = record.turn_id;
                }
            }
        }
    }

    pub fn record_violation(&mut self, violation_type: &str, payload: &str) -> AuditRecord {
        // Enforce the 2000ms clock gate for payload normalization
        thread::sleep(Duration::from_millis(2000));

        self.turn_counter += 1;
        let timestamp = Utc::now().to_rfc3339();

        let message = format!("{}:{}:{}:{}", self.turn_counter, violation_type, payload, self.last_hash);

        let mut mac = HmacSha256::new_from_slice(&self.secret_key).expect("HMAC key error");
        mac.update(message.as_bytes());
        let result = mac.finalize();
        let current_hash = hex::encode(result.into_bytes());

        let record = AuditRecord {
            turn_id: self.turn_counter,
            violation_type: violation_type.to_string(),
            payload_summary: payload.to_string(),
            prev_hash: self.last_hash.clone(),
            hash: current_hash.clone(),
            created_at: timestamp,
        };

        let serialized = serde_json::to_string(&record).unwrap();
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.ledger_file)
            .expect("Failed to open audit ledger");
        writeln!(file, "{}", serialized).expect("Failed to write to ledger");

        self.last_hash = current_hash;
        record
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let violation = args.get(1).map(|s| s.as_str()).unwrap_or("UNKNOWN_VIOLATION");
    let payload = args.get(2).map(|s| s.as_str()).unwrap_or("No payload summary provided");

    let mut vault = VaultLedger::new("SUTTON_STANDARD_SECRET_KEY", "vault_audit_ledger.ndjson");
    let record = vault.record_violation(violation, payload);

    println!("[+] VAULT ANCHOR COMMITTED [Turn ID: {} | Hash: {}]", record.turn_id, &record.hash[..16]);
}
