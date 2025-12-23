# 🏛️ The Master Registry of North Carolina Lottery Games

A **production-grade, self-healing** inventory system that monitors NC Lottery scratch-off games with evidence-based validation and enterprise observability.

## 🎯 What It Does

The Librarian tracks the "Identity" and "Static DNA" of every scratch-off game, built on the **Truth-First** paradigm:
- 📸 **Visual Evidence**: Full-page screenshots + raw HTML captured every run
- 🔐 **Deterministic GUIDs**: Every game gets a permanent UUID for life-long tracking
- 📊 **Statistical Anomaly Detection**: Rejects data that deviates from historical patterns
- 🔄 **Self-Healing**: 3-strike retry loop with exponential backoff

## 🏗️ Architecture: Assembly Line Pattern

The system is decoupled into three rooms for data integrity:

### 1. 🔍 The Sensor ([`sensor_nc.py`](sensor_nc.py))
- Navigates to NC Lottery website using Playwright
- Captures raw evidence (HTML + screenshot)
- Extracts game data using BeautifulSoup
- **New:** Structured JSON logging with run metadata

### 2. ⚖️ The Notary ([`notary.py`](notary.py))
- Validates game count against safety threshold (40 games)
- Assigns permanent GUIDs to new games
- Manages lifecycle: Birth → Active → Retired (3-strike death)
- Runs integrity checksum on total state wealth

### 3. 🏛️ The Vault ([`vault.py`](vault.py))
- Uploads evidence to Cloudflare R2
- Maintains versioned history by run ID
- Provides public mirror at bucket root

## 🚀 Production Features (Dec 2024 Update)

### Observability
- **Structured Logging**: JSON logs with run_id, game_count, duration_ms tracking
- **Metrics Export**: Time-series data in `metrics.json` for Grafana ingestion
- **Heartbeat Monitoring**: Better Uptime integration for proactive alerts

### Self-Healing
- **3-Strike Retry**: Survives transient network failures
- **Pulse History**: 200-run memory for anomaly detection
- **DNA Recovery**: Auto-fetches missing "Overall Odds" metadata

### Multi-State Ready
- **Provider Pattern**: Abstract interface for state-specific scrapers
- **Config-Driven**: `states.yaml` for declarative state management
- **NC Provider**: Reference implementation (`providers/nc_lottery.py`)

### Testing
- **Unit Tests**: `pytest test_notary.py` validates core logic
- **Coverage**: Safety threshold, GUID integrity, statistical validation

## 📂 Evidence Vault (R2)

Every run creates an immutable audit trail:
```
raw_html/YYYY/MM/raw_html_[RUN_ID].html
full_screenshot/YYYY/MM/screenshot_[RUN_ID].png
registry_history/YYYY/MM/registry_[RUN_ID].json
registry.json (live mirror at root)
```

## 🛠️ Stack

| Component | Technology |
|-----------|-----------|
| **Runtime** | Python 3.10+ |
| **Browser** | Playwright (Chromium headless) |
| **Parsing** | BeautifulSoup4 |
| **Storage** | Cloudflare R2 (S3-compatible) |
| **Automation** | GitHub Actions (6-hour cron) |
| **Monitoring** | Better Uptime + JSON logs |
| **Testing** | pytest |

## 📦 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium --with-deps
```

### 2. Configure Environment
```bash
cp .env.example .env
# Fill in R2 credentials and optional monitoring URLs
```

### 3. Run Census
```bash
python main.py
```

### 4. Run Tests
```bash
pytest test_notary.py -v
```

## 🔧 Configuration

### Required (R2 Credentials)
```env
R2_ACCESS_KEY=your_access_key
R2_SECRET_KEY=your_secret_key
R2_BUCKET=your_bucket_name
R2_ENDPOINT=https://account_id.r2.cloudflarestorage.com
R2_PUBLIC_URL=https://your-domain.com
```

### Optional (Monitoring)
```env
HEARTBEAT_URL=https://uptime.betterstack.com/api/v1/heartbeat/YOUR_ID
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ENV=production
```

## 📊 Observability

**Structured Logs** (stdout):
```json
{
  "timestamp": "2025-12-23T01:42:00Z",
  "level": "INFO",
  "module": "main",
  "message": "Census completed successfully",
  "run_id": "run_20251223_0142_a3f9",
  "duration_ms": 12453,
  "game_count": 68
}
```

**Metrics** (`metrics.json`):
- Run duration trend
- Game count over time
- HTML size monitoring
- Vault success rate

## 🌐 Multi-State Architecture

Adding a new state takes ~2 hours:

1. Create provider: `providers/tx_lottery.py`
2. Implement abstract interface from `providers/base.py`
3. Add to `states.yaml`:
   ```yaml
   - code: TX
     enabled: true
     schedule: "0 */12 * * *"
   ```

## 🧪 Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=.  --cov-report=html

# Test specific module
pytest test_notary.py::test_notary_rejects_low_game_count -v
```

## 📈 Performance

| Metric | Value |
|--------|-------|
| **Run Duration** | ~12-15 seconds |
| **Data Captured** | ~250KB HTML + 2MB screenshot |
| **Games Tracked** | 68 active (as of Dec 2024) |
| **Runs per Day** | 4 (every 6 hours) |
| **Monthly Cost** | ~$2 (R2 + GitHub Actions) |

## 🛡️ Safety Mechanisms

1. **Game Count Threshold**: Aborts if <40 games detected
2. **Statistical Validation**: Flags outliers vs. 200-run history  
3. **Integrity Checksum**: Validates total prize wealth
4. **Heartbeat Monitoring**: Alerts if GitHub Actions stops

## 📚 Documentation

- **Setup Guide**: [heartbeat_setup.md](https://github.com/chasenappier/de-informer/blob/main/docs/heartbeat_setup.md)
- **OpenTelemetry Preview**: [opentelemetry_preview.md](https://github.com/chasenappier/de-informer/blob/main/docs/opentelemetry_preview.md)
- **Best Practices Evaluation**: [implementation_plan.md](https://github.com/chasenappier/de-informer/blob/main/docs/implementation_plan.md)

## 🤝 Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feature/new-state-provider`
3. Run tests: `pytest`
4. Commit changes: `git commit -m "feat: add Texas provider"`
5. Push and open PR

## 📊 System Health

**Current Grade:** A (Production-Ready)

- ✅ Evidence-based validation
- ✅ Self-healing retry logic
- ✅ Structured observability
- ✅ Multi-state architecture
- ✅ Automated testing
- ✅ <$10/month operating cost

---

**Built with:** Antigravity AI  
**License:** MIT  
**Status:** 🟢 Active Production
