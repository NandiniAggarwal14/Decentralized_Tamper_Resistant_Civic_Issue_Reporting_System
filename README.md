# An AI-Driven Decentralized and Tamper-Resistant Civic Issue Reporting System for Smart Cities

A full-stack civic issue management platform that empowers citizens to report local problems, assigns them to the correct government wards and departments, and anchors every report's cryptographic fingerprint onto the **Ethereum Sepolia** testnet to prevent tampering. Media evidence (images, audio, video) is stored via a simulated **IPFS** layer and served locally.

Powered by **HuggingFace AI models** — an **EfficientNetB7** deep-learning classifier detects AI-generated / deepfake images across the complaint lifecycle, while a **Sentence Transformer (all-MiniLM-L6-v2)** provides semantic duplicate detection to prevent redundant civic complaints.

---

## Table of Contents
1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [User Roles](#user-roles)
5. [Key Features](#key-features)
6. [Project Structure](#project-structure)
7. [Environment Variables](#environment-variables)
8. [Setup & Running Locally](#setup--running-locally)
9. [Database Schema Overview](#database-schema-overview)
10. [API Reference](#api-reference)
11. [Smart Contract](#smart-contract)
12. [Blockchain Integration Details](#blockchain-integration-details)
13. [Seeding & Data Reset](#seeding--data-reset)
14. [Running Tests](#running-tests)
15. [Priority System](#priority-system)
16. [Utilities](#utilities)
17. [Collaboration Guide](#collaboration-guide)

---

## Overview

Citizens submit civic issues (potholes, power outages, water leaks, etc.) with GPS coordinates, category, description, and optional media. The system:

- **Auto-routes** the issue to the correct **Ward** (based on GPS proximity) and **Department** (based on category).
- Computes a **SHA-256 hash** of the issue data and stores it both in the database and on the **Ethereum Sepolia** blockchain.
- Allows **upvoting** by citizens; upvotes drive a **dynamic priority ranking** visible to ward members and government authorities.
- Provides **role-based dashboards** so each stakeholder sees only what they need.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.10+) |
| AI — Image Authenticity | HuggingFace Transformers — EfficientNetB7 (`dima806/deepfake_vs_real_image_detection`) |
| AI — Duplicate Detection | Sentence Transformers — all-MiniLM-L6-v2 (`sentence-transformers/all-MiniLM-L6-v2`) |
| Frontend | Vanilla HTML + CSS + JavaScript |
| Database | Neon PostgreSQL (cloud-hosted, shared) |
| Blockchain | Ethereum Sepolia via Infura + Web3.py |
| Smart Contract | Solidity (Hardhat deployment) |
| Maps | Folium + OpenStreetMap (server-side rendered interactive maps) |
| Media Storage | Local filesystem (`uploads/`) + simulated IPFS CIDs |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Testing | pytest + httpx (TestClient) |

---

## Architecture

```
+--------------------------------------------------------------+
|                     Browser (Frontend)                        |
|  index.html - citizen.html - ward.html - authority.html      |
|  admin.html - report.html - ai.html                          |
+---------------------------+----------------------------------+
                            | HTTP / REST
+---------------------------v----------------------------------+
|                FastAPI Backend (main.py)                      |
|                                                              |
|  +----------+  +------------+  +------------------------+   |
|  | Auth     |  | Routing    |  | IPFS Service           |   |
|  | (JWT)    |  | (GPS+Cat)  |  | (local simulation)     |   |
|  +----------+  +------------+  +------------------------+   |
|                                                              |
|  +---------------------------+  +------------------------+   |
|  | AI Module (EfficientNetB7)|  | NLP Module (MiniLM)    |   |
|  | Fake Image Detection      |  | Semantic Duplicate     |   |
|  | HuggingFace Pipeline      |  | Detection + Haversine  |   |
|  +---------------------------+  +------------------------+   |
|                                                              |
|  +--------------------------------------------------------+  |
|  |         Blockchain Service (Web3.py)                    |  |
|  |  store_issue_hash() / verify_issue_hash()               |  |
|  |  EIP-1559 gas + async receipt tracking                  |  |
|  +------------------------+-------------------------------+  |
+---------------------------+----------------------------------+
                            |
            +---------------v-----------------+
            |   Neon PostgreSQL (cloud)        |
            |   issues, users, wards,          |
            |   departments, votes,            |
            |   issue_status_history,          |
            |   failed_blockchain_txns         |
            +---------------------------------+
                            |
            +---------------v-----------------+
            |   Ethereum Sepolia Testnet       |
            |   CivicRegistry.sol              |
            |   (SHA-256 hash anchoring)       |
            +---------------------------------+
```

---

## User Roles

| Role | Description | Dashboard |
|---|---|---|
| **Citizen** | Registers, submits and tracks their own issues, upvotes issues | `citizen.html` |
| **Ward Member** | Manages issues routed to their ward, redirects to departments | `ward.html` |
| **Government Authority** | Manages issues in their department, marks in-progress or resolved | `authority.html` |
| **Admin** | Approves/rejects pending users, views all users, system stats, blockchain monitoring | `admin.html` |

> Ward Members and Government Authorities require **Admin approval** before they can access their dashboards.

---

## Key Features

### Issue Lifecycle
```
- Issues can be **rejected** by Ward Members with mandatory text reasons and evidence uploads (documents or images), which are stored on IPFS and anchored on the Sepolia blockchain to guarantee transparency.

### Multi-Phase AI Image Verification (HuggingFace EfficientNetB7)
Every uploaded image across the complaint lifecycle is automatically evaluated by a **HuggingFace EfficientNetB7** deep-learning classifier (`dima806/deepfake_vs_real_image_detection`) to detect synthetic or AI-generated media (`Fake`) versus authentic photography (`Real`):
- **Citizen Submission**: Evaluates primary report photos upon registration.
- **Ward Rejection Evidence**: Evaluates evidence uploaded by ward representatives during rejection.
- **Authority Resolution Proof**: Evaluates completion proof photos uploaded by department officials.
- **Visual Transparency Badges**: Real-time badges (`🟢 REAL [confidence%]` / `🔴 FAKE (AI-Generated) [confidence%]`) are rendered on issue cards and inside the Citizen Status Audit Trail timeline modal.
- **Graceful Fallback**: If the model is unavailable, returns a neutral 50% confidence score instead of blocking submissions.

### NLP Semantic Duplicate Detection (Sentence Transformer all-MiniLM-L6-v2)
Before a citizen submits a new complaint, the system checks for potential duplicate reports using a **Sentence Transformer** model (`sentence-transformers/all-MiniLM-L6-v2`, 22M parameters):
- **Spatial Filtering**: Haversine distance calculation filters candidates within 150–500 metres of the new report.
- **Semantic Similarity**: Cosine similarity between sentence embeddings of complaint titles + descriptions identifies textual duplicates.
- **Dynamic Thresholds**: Closer complaints (≤150m) use a lower similarity threshold (0.45) than distant ones (0.55).
- **Citizen Choice**: If duplicates are found, citizens can upvote the existing report or submit anyway.
- **Fallback**: If the NLP model is unavailable, falls back to token-based Jaccard similarity.


### Dynamic Priority (Upvote-Driven)
Issues are **automatically ranked by upvote count**. The priority badge on each card is assigned dynamically when fetching issues:

| Rank position | Priority Badge |
|---|---|
| Top 25% | Critical |
| Next 25% | High |
| Next 25% | Medium |
| Bottom 25% | Low |

Ward members can **no longer manually set priority** -- it is fully driven by community upvotes.

### Upvote System
- Citizens upvote issues they care about (one upvote/downvote per user per issue).
- A 5-second cooldown prevents spam voting.
- Upvote count is visible on every card across all three role dashboards.

### Interactive Maps (Folium + OpenStreetMap)
- Server-side rendered interactive maps using **Folium** with OpenStreetMap tiles.
- Status colour-coded markers (Amber/Blue/Green/Red) with clustered pins for dense areas.
- Custom HTML popups with title, status badge, category, area, upvotes, and GPS coordinates.
- Ward-filtered map views for ward member dashboards.

### Visual Timeline & Stepper Status Trail
- Every complaint has an audit timeline logged securely in both the database and the blockchain.
- Citizens can track their issue resolution lifecycle step-by-step using a visual vertical stepper timeline (Reported → Routed → In Progress → Resolved), complete with historical timestamps.
- Ward representative forwarding and department official actions are tracked automatically.

### Session-Bound Readonly Profile Details
- The report form automatically populates the reporter's name and contact information from their active login session.
- To prevent spoofing and spam, these fields are rendered `readonly` and styled to block user edits.

### Simplified Blockchain Operations Feed
- The admin dashboard features a simplified, chronological operations log that merges anchor transactions and sync status events.
- Technical transaction details are formatted as easy-to-read cards, highlighting whether an operation is synced on-chain or pending.
- Administrators can trigger batch retries for any queued sync alerts.

### Auto-Routing
- **Ward**: Determined by GPS haversine distance to the nearest ward centre.
- **Department**: Determined by issue category via the `category_department_map` table.

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app entry point, lifespan model loading, middleware
│   │   ├── config.py              # Centralised configuration constants
│   │   ├── auth.py                # JWT token creation & validation, password hashing
│   │   ├── database.py            # Neon PostgreSQL connection pool (psycopg2)
│   │   ├── schema.sql             # Full DB schema with migrations (run via init_db())
│   │   ├── models.py              # Pydantic request/response models
│   │   ├── helpers.py             # Shared utility functions (hashing, priority calc, serialization)
│   │   ├── routing.py             # GPS ward routing + category classification
│   │   ├── blockchain_service.py  # Web3.py Sepolia integration (EIP-1559, async receipts)
│   │   ├── ipfs_service.py        # Simulated IPFS JSON storage
│   │   ├── ai/                    # HuggingFace EfficientNetB7 Deepfake Classifier
│   │   │   ├── __init__.py
│   │   │   ├── model.py           # HuggingFace pipeline singleton loader
│   │   │   └── predict.py         # Image preprocessing & inference pipeline
│   │   ├── nlp/                   # Sentence Transformer Duplicate Detector
│   │   │   ├── __init__.py
│   │   │   └── duplicate_detector.py  # Semantic similarity + Haversine spatial filtering
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ai.py              # POST /api/predict, /api/ai/predict
│   │   │   ├── auth.py            # /api/auth/* endpoints
│   │   │   ├── issues.py          # /api/issues/* + /api/issues/check-duplicates
│   │   │   ├── ward.py            # /api/ward/* endpoints
│   │   │   ├── authority.py       # /api/authority/* endpoints
│   │   │   ├── admin.py           # /api/admin/* endpoints
│   │   │   ├── maps.py            # /api/maps/* Folium interactive map endpoints
│   │   │   └── pages.py           # Static page serving (FileResponse mappings)
│   │   ├── abis/                  # Compiled contract ABIs (CivicRegistry.json)
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── test_admin.py
│   │       ├── test_ai.py         # AI verification endpoints & model integration test
│   │       ├── test_auth.py
│   │       ├── test_issues.py
│   │       ├── test_rejection.py  # Ward member rejection workflow tests
│   │       ├── test_routing.py
│   │       └── test_voting.py
│   └── scripts/
│       ├── seed.py                # Truncate + re-seed (admin, wards, departments)
│       ├── refresh_reports.py     # Purge all issue data, votes, and status trails
│       ├── refresh_users.py       # Purge non-admin user accounts and reset ward links
│       ├── backfill_hashes.py     # One-time script to hash existing issues
│       ├── verify_sync_status.py  # Checks DB vs on-chain hash consistency
│       └── reset_passwords.py     # Password reset utility
├── frontend/
│   └── src/
│       ├── index.html             # Home page (Login / Register)
│       ├── citizen.html / .js     # Citizen dashboard & audit trail
│       ├── ward.html / .js        # Ward member dashboard & evidence proof
│       ├── authority.html / .js   # Government authority dashboard & resolution proof
│       ├── admin.html / .js       # Admin dashboard (users, stats, blockchain monitor)
│       ├── ai.html / .js          # Standalone AI Image Verification Sandbox
│       ├── report.html / .js      # Issue submission form (with duplicate detection)
│       ├── auth.js                # Shared auth helpers
│       ├── i18n.js                # Internationalisation engine
│       ├── styles.css             # Global dark-mode design system
│       └── lang/                  # i18n translation files
├── smart_contract/
│   ├── contracts/
│   │   └── CivicRegistry.sol      # Solidity hash registry
│   ├── scripts/
│   │   └── deploy.js              # Hardhat deploy script
│   └── hardhat.config.js
├── uploads/                       # Uploaded media files (committed to Git)
├── test_images/                   # Test images for AI model benchmarking (gitignored)
├── cleanup_huggingface_cache.py   # Utility: scan & delete HuggingFace model caches from all drives
├── .env                           # Secrets (never committed)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Environment Variables

Create a `.env` file in the project root with the following:

```env
# PostgreSQL (Neon cloud or any PostgreSQL-compatible URL)
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Ethereum Sepolia via Infura
INFURA_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
CONTRACT_ADDRESS=0xYourDeployedContractAddress
WALLET_PRIVATE_KEY=0xYourWalletPrivateKey
CHAIN_ID=11155111

# JWT Secret
SECRET_KEY=your_random_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

> **Important**: Both developers share the same `.env` values for `DATABASE_URL`, `INFURA_URL`, `CONTRACT_ADDRESS`, `WALLET_PRIVATE_KEY`, and `CHAIN_ID` since both connect to the same Neon database and the same Sepolia contract. Only share `.env` values securely and never commit the file to Git.

---

## Setup & Running Locally

### 1. Clone the Repository

```bash
git clone https://github.com/NandiniAggarwal14/Decentralized_Tamper_Resistant_Civic_Issue_Reporting_System.git
cd Decentralized_Tamper_Resistant_Civic_Issue_Reporting_System
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note on bcrypt**: `requirements.txt` pins `bcrypt==3.2.2` because `passlib 1.7.4` is incompatible with `bcrypt >= 4.0.0`. The newer bcrypt changed its API, which causes `passlib.verify()` to silently return `False` for correct passwords. Do not upgrade bcrypt without also upgrading passlib.

### 4. Configure Environment

Copy the `.env` template above into the project root and fill in the values. If you are the second developer (Nandini), request the shared `.env` values from the first developer.

### 5. Initialise Database Schema

```bash
python -m backend.app.database
```

This creates all tables and runs migration queries (e.g. adding new columns to existing tables) safely using `IF NOT EXISTS` and `ADD COLUMN IF NOT EXISTS`.

### 6. Seed the Database

```bash
python -m backend.scripts.seed
```

This will:
- Truncate all tables.
- Insert 7 departments, 30 category-department mappings, 8 Delhi wards.
- Create the **admin** account: `admin` / `123456789`.

### 7. Start the Server

```bash
python -m backend.app.main
```

Or equivalently:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 8. Open in Browser

```
http://127.0.0.1:8000
```

---

## Database Schema Overview

| Table | Purpose |
|---|---|
| `users` | All users (admin, citizen, ward_member, authority) |
| `wards` | Geographic ward boundaries with GPS centre + radius |
| `departments` | Government departments (Roads, Water, Electricity, etc.) |
| `category_department_map` | Maps issue categories to departments |
| `issues` | All civic issues with status, hash, media, location |
| `issue_votes` | Per-user upvote/downvote records |
| `issue_status_history` | Full audit trail of status changes (with ipfs_cid & blockchain_hash) |
| `failed_blockchain_txns` | Retry queue for failed Sepolia transactions |

---

## API Reference

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login and get JWT token |
| `GET` | `/api/auth/me` | Get current user profile |

### Issues (Public / Citizen)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/issues` | List all issues (sorted by upvotes) |
| `POST` | `/api/issues` | Submit a new civic issue (auto-runs AI image scan) |
| `POST` | `/api/issues/check-duplicates` | NLP semantic duplicate detection before submission |
| `POST` | `/api/issues/{id}/vote` | Cast an upvote or downvote |
| `GET` | `/api/issues/{id}/status-history` | Full chronological status audit trail |
| `GET` | `/api/verify/{id}` | Verify tamper-resistance on-chain |
| `GET` | `/api/verify-all` | Batch verify all issues against blockchain |

### Ward Member
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/ward/issues` | Issues routed to this ward |
| `POST` | `/api/ward/issues/{id}/redirect` | Redirect issue to a department |
| `POST` | `/api/ward/issues/{id}/reject` | Reject issue with justification and evidence |
| `GET` | `/api/ward/stats` | Ward-level statistics |
| `GET` | `/api/ward/profile` | Ward member's profile |
| `POST` | `/api/ward/profile` | Update ward member's profile |

### Government Authority
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/authority/issues` | Issues for this department |
| `PATCH` | `/api/authority/issues/{id}/status` | Update status (`pending`, `in_progress`, `resolved`) |
| `POST` | `/api/authority/issues/{id}/resolve` | Resolve with completion proof |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/pending-users` | Users pending approval |
| `POST` | `/api/admin/approve-user/{id}` | Approve a user |
| `POST` | `/api/admin/reject-user/{id}` | Delete a pending user |
| `GET` | `/api/admin/stats` | System-wide statistics |
| `GET` | `/api/admin/users` | List all users |
| `DELETE` | `/api/admin/users/{id}` | Delete a user |
| `GET` | `/api/admin/wards` | All wards with assigned members |
| `GET` | `/api/admin/departments` | All departments with staff |
| `GET` | `/api/admin/failed-transactions` | Failed blockchain transaction queue |
| `POST` | `/api/admin/retry-transactions` | Retry all failed transactions |

### AI Image Authenticity Verification (EfficientNetB7)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/predict` | Predict if an uploaded image is Fake (AI-Generated) or Real |
| `POST` | `/api/ai/predict` | Alias endpoint for AI prediction |

> **Response Schema:** `{"prediction": "Fake" | "Real", "confidence": 98.41, "probability": 0.9841}`

### Maps (Folium)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/maps/issues` | Interactive Folium map of all issues (optional `?ward_id=X` filter) |

### Health
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System health check (includes blockchain status) |

---

## Smart Contract

The Solidity contract `CivicRegistry.sol` provides a tamper-proof hash registry on Ethereum Sepolia.

### Contract Functions
| Function | Description |
|---|---|
| `storeIssueHash(uint256, string)` | Store an issue's SHA-256 hash on-chain |
| `getIssueHash(uint256)` | Retrieve a stored issue hash |
| `storeCompletionHash(uint256, string)` | Store a resolution proof hash |
| `getCompletionHash(uint256)` | Retrieve a completion hash |
| `storePersonnelHash(uint256, string)` | Store a personnel verification hash |
| `getPersonnelHash(uint256)` | Retrieve a personnel hash |

### Deploy

```bash
cd smart_contract
npm install
npx hardhat run scripts/deploy.js --network sepolia
```

Copy the deployed address into root `.env` as `CONTRACT_ADDRESS`.

### Current Deployment
- **Network**: Sepolia (Chain ID: 11155111)
- **Contract**: `0x569486209dF1AcF3033A8D6E7e6D745FF5e13483`
- **Wallet**: `0x91Ab709a669c8B7FD14e0972935a41bAb06fB147`

---

## Blockchain Integration Details

### EIP-1559 Gas Estimation
All blockchain transactions use EIP-1559 dynamic fee estimation:
- Fetches the latest block's `baseFeePerGas`
- Queries `eth.max_priority_fee` from the node
- Sets `maxFeePerGas = baseFee * 2 + priorityFee`
- Falls back to legacy `gasPrice` if EIP-1559 fields are unavailable

### Non-Blocking Transaction Flow
1. The API endpoint broadcasts the signed transaction and immediately returns the `tx_hash` to the user (sub-second response).
2. A background daemon thread polls for the transaction receipt (up to 180 seconds).
3. If the receipt shows `status == 0` (reverted) or the wait times out, the transaction is logged to the `failed_blockchain_txns` database table.
4. The admin can retry all failed transactions from the dashboard.

### Nonce Management
Transaction nonces are fetched with the `'pending'` block tag to account for in-flight transactions, preventing `nonce too low` and `replacement transaction underpriced` errors during rapid consecutive submissions.

---

## Seeding & Data Reset

To wipe all issues, votes, status history, and failed blockchain transaction logs (preserving users, wards, and departments):

```bash
python -m backend.scripts.refresh_reports
```

To purge all non-admin user accounts (`citizen`, `ward_member`, `authority`) and unassign members from wards:

```bash
python -m backend.scripts.refresh_users
```

To perform a complete database re-seed (recreates default Delhi wards, departments, category maps, and admin account):

```bash
python -m backend.scripts.seed
```

To backfill SHA-256 hashes for existing issues that predate blockchain integration:

```bash
python -m backend.scripts.backfill_hashes
```

To check if all DB hashes match on-chain state:

```bash
python -m backend.scripts.verify_sync_status
```

---

## Running Tests

```bash
python -m pytest backend/app/tests/ -v
```

Tests cover admin operations, authentication, issue submission, ward routing, voting, AI inference, and rejection workflows. Tests use mock database connections and do not require a live Neon database or blockchain node.

| Test File | Coverage |
|---|---|
| `test_admin.py` | Admin-only endpoints, user approval/rejection, stats |
| `test_ai.py` | AI prediction endpoint, model integration |
| `test_auth.py` | Register, login, token validation, role enforcement |
| `test_issues.py` | Issue submission, validation, public feed |
| `test_rejection.py` | Ward member rejection workflow with evidence |
| `test_routing.py` | GPS ward detection, category-to-department mapping |
| `test_voting.py` | Upvote/downvote toggle, cooldown rate limiting |

---

## Priority System

Priority is **not set manually**. It is calculated dynamically each time issues are fetched, based on the rank of each issue in the upvote-sorted list:

```
Issues sorted by upvote_count DESC --> assigned priority by percentile rank:
  Top 25%    --> Critical
  25-50%     --> High
  50-75%     --> Medium
  Bottom 25% --> Low
```

This ensures that community-driven issues always surface at the top with appropriate urgency.

---

## Utilities

### HuggingFace Cache Cleanup

The `cleanup_huggingface_cache.py` script scans all local drives (C:, D:, E:, F:, etc.) for cached HuggingFace models, reports total space usage, and deletes them on confirmation:

```bash
python cleanup_huggingface_cache.py
```

This is useful when HuggingFace model caches accumulate significant disk space (often several GB) across multiple user directories and project environments.

---

## Collaboration Guide

### For Nandini (or any collaborator pulling this branch)

1. **Pull the branch**:
   ```bash
   git pull origin main
   ```

2. **Install/update dependencies** (bcrypt version is critical):
   ```bash
   pip install -r requirements.txt
   ```

   > **Note on AI models**: The first run will automatically download the HuggingFace models (~500 MB for EfficientNetB7 + ~90 MB for all-MiniLM-L6-v2) and cache them locally. Subsequent runs load from cache.

3. **Run database migrations** (safe to re-run, uses `IF NOT EXISTS`):
   ```bash
   python -m backend.app.database
   ```

4. **Seed if needed** (only if starting fresh):
   ```bash
   python -m backend.scripts.seed
   ```

5. **Verify `.env`**: Ensure your `.env` has all the required keys listed in the [Environment Variables](#environment-variables) section. Both developers share the same Neon DB and Sepolia contract.

6. **Start the server**:
   ```bash
   python -m backend.app.main
   ```

   On first startup, you will see log messages confirming both AI models are loading:
   ```
   INFO: Loading HuggingFace EfficientNetB7 Deepfake Detector...
   INFO: EfficientNetB7 Deepfake Classifier loaded successfully.
   INFO: Loading NLP Duplicate Detector model 'sentence-transformers/all-MiniLM-L6-v2'...
   INFO: SentenceTransformer model loaded successfully.
   ```

7. **Run tests** to confirm everything works:
   ```bash
   python -m pytest backend/app/tests/ -v
   ```

> **Note**: The `ipfs_storage/` directory is gitignored and created automatically at runtime. The `uploads/` directory is tracked in Git and contains citizen complaint evidence files.

---

## Academic Journal Defense Changelog & Architectural Audit

### 1. Summary of Changes (Quick Scan)
- **HuggingFace EfficientNetB7 Integration**: Replaced PyTorch ResNet-50 with HuggingFace pipeline (`dima806/deepfake_vs_real_image_detection`) for multi-checkpoint deepfake/synthetic image classification (Submission, Rejection, Resolution).
- **Multi-Signal Semantic Duplicate Detection**: Added HuggingFace SentenceTransformer (`sentence-transformers/all-MiniLM-L6-v2`) with a 3-tier matching engine (GPS Proximity, Matching Area Name, Global Text Match) and vectorized batch matrix encoding.
- **Asynchronous Execution Architecture**: Offloaded heavy NLP model inference to background thread executors (`run_in_executor`), reducing duplicate check latency from 50s to <1.5s.
- **Ward Rejection Workflow**: Implemented mandatory justification + evidence upload for issue rejections, backed by IPFS storage, Sepolia blockchain anchoring, and AI fake detection.
- **Dynamic Community Priority Ranking**: Converted issue priority from manual ward selection to 100% upvote-driven percentile ranking (Critical: Top 25%, High: 25–50%, Medium: 50–75%, Low: Bottom 25%).
- **Interactive Geospatial Mapping**: Integrated Folium + OpenStreetMap server-side rendering for status-coded, clustered map markers and ward-scoped filtering (`/api/maps/issues`).
- **EIP-1559 Non-Blocking Blockchain Layer**: Enhanced Web3.py Sepolia anchoring with dynamic gas pricing (`baseFee * 2 + priorityFee`), `'pending'` nonce tracking, and automated failure queue retry tables.
- **Project Structure Optimization**: Cleaned 427 MB of temporary research artifacts, obsolete benchmark scripts (`hf_model_test.py`, `duplicate/`), and stale docs; enabled version control tracking for `uploads/`.

---

### 2. Detailed Breakdown by Category

#### A. Blockchain / Ethereum Smart Contract Logic
- **Changes**: Web3.py service upgraded to use EIP-1559 dynamic fee calculation ($\text{maxFeePerGas} = \text{baseFee} \times 2 + \text{priorityFee}$) and `'pending'` nonce query. Added non-blocking receipt daemon polling with automated fallback insertion into `failed_blockchain_txns`.
- **Files**: `backend/app/blockchain_service.py`, `backend/app/routes/admin.py`, `smart_contract/contracts/CivicRegistry.sol`.

#### B. IPFS Storage / Evidence Handling
- **Changes**: Extended IPFS SHA-256 CID generation to Ward Member Rejection evidence uploads. Modified `.gitignore` to track `uploads/` in Git version control.
- **Files**: `backend/app/ipfs_service.py`, `backend/app/routes/ward.py`, `.gitignore`.

#### C. SHA-256 Hashing / Integrity Verification
- **Changes**: State fingerprinting recomputed dynamically on `GET /api/verify/{id}` to compare DB state vs. Sepolia on-chain hash.
- **Files**: `backend/app/helpers.py`, `backend/app/routes/issues.py`.

#### D. Complaint Lifecycle Workflow (Submission $\rightarrow$ Routing $\rightarrow$ Resolution)
- **Changes**: Added `POST /api/ward/issues/{id}/reject` with mandatory rejection justification, evidence upload, IPFS CID generation, and Sepolia anchoring.
- **Files**: `backend/app/routes/ward.py`, `backend/app/routes/authority.py`.

#### E. Role-Based Governance (Citizen, Ward Member, Authority, Admin)
- **Changes**: Citizens submit complaints & upvote; Ward Members redirect/reject; Authorities mark in-progress/resolve with proof; Admins manage users & retry failed blockchain transactions.
- **Files**: `backend/app/routes/admin.py`, `backend/app/routes/ward.py`, `backend/app/routes/authority.py`.

#### F. Support Voting / Dynamic Priority
- **Changes**: Manual priority override removed. Issues automatically assigned `Critical`, `High`, `Medium`, or `Low` badges based on percentile rank in `upvote_count DESC` list.
- **Files**: `backend/app/helpers.py`, `backend/app/routes/issues.py`.

#### G. Location-Based Routing / Jurisdiction Logic
- **Changes**: Haversine formula auto-detects nearest Delhi ward center; category-to-department map routes to responsible agency. Folium maps render markers at `/api/maps/issues`. Browser Geolocation updated with `{ enableHighAccuracy: true }`.
- **Files**: `backend/app/routing.py`, `backend/app/routes/maps.py`, `frontend/src/report.js`.

#### H. Frontend / UI Changes
- **Changes**: Simplified to English single-locale mode (removed `hi.json`); added duplicate detection modal; updated title to "An AI-Driven Decentralized and Tamper-Resistant Civic Issue Reporting System for Smart Cities".
- **Files**: `frontend/src/report.html`, `frontend/src/report.js`, `frontend/src/lang/en.json`.

---

### 3. Impact on Existing Academic Claims

| Section in Paper/Presentation | Stated Claim / Previous Description | Required Update / Refinement |
|---|---|---|
| **Abstract & Introduction** | "Employs PyTorch ResNet-50 binary image classification for deepfake detection." | **Update**: "Utilizes HuggingFace EfficientNetB7 for multi-stage AI image authenticity verification and SentenceTransformer (all-MiniLM-L6-v2) for semantic duplicate detection." |
| **System Architecture** | "Ward members manually assign priority levels (Low, Medium, High, Critical)." | **Update**: "Priority is calculated dynamically via upvote percentile ranking, establishing a community-driven triage model." |
| **Methodology — Duplicate Prevention** | "Duplicates are flagged using a 150m Haversine distance radius check." | **Update**: "Duplicates are identified via a 3-tier Multi-Signal Matching Engine combining spatial proximity (500m), area name matching, and NLP cosine sentence embeddings." |
| **Experimental Results & Latency** | "Duplicate detection evaluation time." | **Update**: Cite batch vector inference benchmarks (<1.5s response time using `all-MiniLM-L6-v2` with thread executor offloading). |
| **Governance Workflow** | "Issues can only be moved to In-Progress or Resolved." | **Update**: "Includes formal Ward Representative Rejection workflow backed by IPFS evidence logging, Sepolia hash anchoring, and AI verification." |

---

### 4. Depth of Explanation Needed (Dual-Level)

#### A. Plain-Summary Version (For Quick Briefing)
- **AI Deepfake Detection**: Uses HuggingFace EfficientNetB7 (`dima806/deepfake_vs_real_image_detection`) at Submission, Rejection, and Resolution to verify image authenticity with real-time visual badges (`REAL` vs. `FAKE`).
- **NLP Duplicate Detection**: Uses SentenceTransformer (`all-MiniLM-L6-v2`) with a 3-tier Multi-Signal matching engine (GPS, Area Name, Global Text Match) to prevent redundant reports in <1.5s.
- **Blockchain Anchoring**: Hashes complaint data with SHA-256 and anchors on Ethereum Sepolia via Web3.py using EIP-1559 gas pricing and non-blocking background workers.

#### B. Technical-Deep-Dive Version (For In-Depth Defense Questions)
- **Image Pipeline**: Managed via singleton loader in `backend/app/ai/model.py`. `predict_image()` accepts `PIL.Image`, `bytes`, or `BytesIO`, runs `image-classification` pipeline, and normalizes output labels (`FAKE`, `SYNTHETIC`, `LABEL_1`) to `"Fake"` or `"Real"` with confidence score.
- **NLP Vectorization**: `duplicate_detector.py` batch-encodes query + candidate texts in a single tensor operation (`model.encode(all_texts, convert_to_tensor=True)`), computes cosine matrix (`util.cos_sim`), and evaluates Tier 1 (GPS $\le$ 500m & sim $\ge$ 0.45), Tier 2 (Area match & sim $\ge$ 0.55), Tier 3 (sim $\ge$ 0.85). Offloaded asynchronously via `asyncio.get_event_loop().run_in_executor()`.
- **EIP-1559 Web3.py**: Constructs transactions using $\text{maxFeePerGas} = \text{baseFee} \times 2 + \text{priorityFee}$ and `'pending'` block tag nonces in `backend/app/blockchain_service.py`. Failed receipts are routed to `failed_blockchain_txns` for batch retry.

---

### 5. New / Updated Diagrams Needed

1. **Fig 1: System Architecture** — Replace ResNet-50 block with HuggingFace EfficientNetB7 and SentenceTransformer NLP modules; show connection from FastAPI router to thread pool executor; add Folium interactive map component.
2. **Fig 2: Issue Lifecycle State Diagram** — Add `Rejected` state branching from `Pending` (Ward Representative action) with mandatory IPFS evidence CID and Sepolia hash anchor.
3. **Fig 3: Duplicate Detection Sequence Diagram** — Redraw sequence to show 3-Tier Multi-Signal evaluation flow (GPS Proximity $\rightarrow$ Area Name Check $\rightarrow$ Global Tensor Encoding).
4. **Fig 4: Dynamic Priority Pipeline** — Illustrate `upvote_count DESC` percentile sorting ($0\text{--}25\% \rightarrow \text{Critical}$, $25\text{--}50\% \rightarrow \text{High}$, $50\text{--}75\% \rightarrow \text{Medium}$, $75\text{--}100\% \rightarrow \text{Low}$).

