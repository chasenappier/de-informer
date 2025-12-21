# 🏛️ The Master Registry of North Carolina Lottery Games

A high-reliability **Inventory Registry** that catalogs every scratch-off game published by the NC Lottery. This is the **Source of Truth** for the entire decoupled fleet.

## 🎯 Objective
The Librarian tracks the "Identity" and "Static DNA" of every game. It is built on the **Truth-First** paradigm, capturing both Digital Data and Visual Evidence.

- **Game GUID**: A permanent, random identifier for every game.
- **Static DNA**: Overall Odds, Prize Tiers, and Total Prize counts.
- **Visual Receipts**: A full-page screenshot is captured and vaulted every run (6 hrs).

## 🛡️ The Notary (Logic)
1. **Discovery**: Uses a headless browser (Playwright) to load the NC Lottery summary page.
2. **Evidence Capture**: Takes a **Full-Page Screenshot** (The Receipt) and vaults it in R2.
3. **Extraction**: Parses the HTML bones to update the `registry.json`.
4. **Life Cycle Management**:
   - **BIRTH**: New GUIDs are issued. Deep-dive to capture overall odds.
   - **STASIS**: Registry updated with current state.
   - **DEATH**: Games missing for 3 consecutive runs are marked as `RETIRED`.
5. **Safety Brake**: Aborts if fewer than 40 games are found.

## 🛰️ Fleet Context (Decoupled Architecture)
This component is **Cog 01**:
*   **Librarian (This Repo)**: The Source of Truth for *Identity* and *Evidence*.
*   **Visual Scout (Cog 02)**: (External) Captures and vaults high-res game art.
*   **Accountant (Future)**: Will track granular *Inventory* changes using these GUIDs.

## 🛠️ Stack
- **Python**: Core logic.
- **Playwright**: Headless browser for visual evidence.
- **BeautifulSoup4**: HTML parsing.
- **GitHub Actions**: Automation every 6 hours.
- **JSON Ledger**: `registry.json` acts as the repository database.
- **Cloudflare R2**: Holds the "Receipt" screenshots and the public JSON mirror.
