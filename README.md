# 🏛️ The Master Registry of North Carolina Lottery Games

A high-reliability **Inventory Registry** that catalogs every scratch-off game published by the NC Lottery. This is the **Source of Truth** for the entire decoupled fleet.

## 🎯 Objective
The Librarian tracks the "Identity" and "Static DNA" of every game. It is built on the **Truth-First** paradigm, capturing both Digital Data and Visual Evidence.

## 🏗️ The "Assembly Line" Architecture
The system is decoupled into three distinct rooms to ensure data integrity and auditability:

1.  **🔍 The Sensor (`sensor_nc.py`)**: Responsible for looking at the website, capturing raw evidence (HTML/Screenshots), and extracting the raw "Bones" of the data.
2.  **⚖️ The Notary (`notary.py`)**: The brain of the registry. It matches raw data to permanent **GUIDs**, manages the game lifecycle (Birth/Stasis/Death), and runs the **Integrity Checksum**.
3.  **🏛️ The Vault (`vault.py`)**: Standardizes and syncs the session package to Cloudflare R2 for long-term storage and public mirrors.

## 🛡️ Truth-First Features
- **Deterministic GUIDs**: Every game is issued a random, permanent UUID for life-long tracking.
- **DNA Healing**: Automatically re-attempts to capture missing "Overall Odds" metadata in subsequent runs.
- **Integrity Checksum**: Validates the "Total State Wealth" to prevent corrupted runs from ever overwriting the Source of Truth.
- **Human Jitter**: Mimics natural user behavior with randomized delays and modern User-Agent rotation.

## 📂 Standardized Vault (R2)
Every run is tagged with a unique `RUN_ID`, and evidence is vaulted in an auditable directory tree:
- `raw_html/YYYY/MM/raw_html_[RUN_ID].html`
- `full_screenshot/YYYY/MM/screenshot_[RUN_ID].png`
- `registry_history/YYYY/MM/registry_[RUN_ID].json`
- `registry.json` (The "Live Mirror" at the bucket root)

## 🛠️ Stack
- **Python**: Core logic and orchestrator (`main.py`).
- **Playwright**: Headless browser for visual evidence.
- **GitHub Actions**: Automated periodic census (every 6 hrs).
- **Cloudflare R2**: The permanent evidence vault.

---
🚀 **Antigravity Handshake**: Connected and verified. "Assembly Line" V1 Deployment complete.
