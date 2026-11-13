# Sarvatra AI (सर्वत्र)
### College of Military Engineering, Dapodi, Pune
**Air-Gapped Sovereign AI Assistant & Military Document Formulation Engine**

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Django 3.2+](https://img.shields.io/badge/Django-3.2%2B-green.svg)](https://www.djangoproject.com/)
[![License: Air-Gapped / CME Restricted](https://img.shields.io/badge/License-Corps%20of%20Engineers%20%2F%20Restricted-red.svg)](#)
[![Security: AES-256 Agile & Air-Gap PKI](https://img.shields.io/badge/Security-AES--256%20Agile-orange.svg)](#)

---

## 1. Overview

**Sarvatra AI** is a sovereign, self-contained AI assistant and military document formulation system developed specifically for the **College of Military Engineering (CME), Dapodi, Pune (Corps of Engineers, Indian Army)**.

Engineered to operate in strict **air-gapped and offline military networks**, Sarvatra AI delivers zero-telemetry conversational intelligence and automated formulation of military-standard correspondence, strictly adhering to **Indian Army Staff Duties (SD)** conventions.

```
       ┌────────────────────────────────────────────────────────┐
       │               SARVATRA AI CORE PLATFORM                │
       └───────────────────────────┬────────────────────────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
┌──────────────┐         ┌────────────────────┐       ┌──────────────────┐
│  OLLAMA LLM  │         │  OFFLINE MILITARY  │       │ DOCUMENT ENGINE  │
│  Llama-3 8B  │◄───────►│    RULE ENGINE     │◄─────►│   DOCX & PDF     │
│  Phi-3 3.8B  │         │ (Zero-LLM Fallback)│       │  PyMuPDF Vector  │
└──────────────┘         └────────────────────┘       └──────────────────┘
```

---

## 2. Key Capabilities

### A. 7 Military Document Archetypes
Fully structured, formatted, and validated against official military standards:
1. **Formal Military Letter**: Reference numbers, sender/recipient staff blocks, numbered paragraphs, sign-off authorities, and distribution lists.
2. **Office Memorandum (Memo)**: Inter-departmental and inter-wing administrative communications.
3. **Minutes of Meeting (MoM)**: Training/admin committees, attendee rosters, action points, and designated officer assignments.
4. **Office Note (Note Sheet)**: Formal internal noting, decision recommendations, and approval tracks.
5. **Office Order**: Station and wing administrative orders, duty rosters, and routine orders.
6. **Technical Report**: Engineering evaluations, trials, technical specifications, and obstacle crossing doctrines.
7. **Leave Application**: Standard military leave applications (Casual, Annual, Sick) with station leave records, train journey details, and address during leave.

### B. Dynamic Station Letterheads & Formations
Selectable via Studio dropdown or modified dynamically via natural language chat queries:
- **Headquarters CME** (`COLLEGE OF MILITARY ENGINEERING, Dapodi, Pune`)
- **Faculty of Combat Engineering (FCE)**
- **Cadets Training Wing (CTW)**
- **Faculty of Electrical & Mechanical Engineering (FEME)**
- **Faculty of Information Technology (CME-IT)**
- **Custom / Tactical Formations**

### C. Chat-Driven Live Document Reflection
Officers can dynamically modify any document metadata or content in natural language:
- *"Change letterhead to CTW and update date to 25 Nov 2026"*
- *"Add an operational clearance clause from Southern Command"*
- *"Set classification to CONFIDENTIAL and add Lt Col Verma as recipient"*
Modifications immediately update metadata, the live A4 canvas preview, and both export formats.

### D. Dual Model Architecture
- **Standard Deployment (`main` branch)**: Defaulted to `llama3:latest` (8B) for high-end workstations and dedicated GPU servers.
- **Workstation Deployment (`feature/phi3-integration` branch)**: Prioritized for `phi3:mini` (3.8B), optimized for 8GB and 16GB RAM workstations (~10s generation speed on CPU).

### E. 100% Offline Rule Engine (Zero-LLM Fallback)
Even if Ollama is stopped or unavailable, Sarvatra AI’s deterministic rule engine guarantees continuous formulation, parameter updates, and document generation without downtime.

### F. Dual High-Resolution Export
- **Microsoft Word (`.docx`)**: Fully styled, editable OpenXML document using authentic Indian Army typographical hierarchies.
- **Vector PDF (`.pdf`)**: Compiled via PyMuPDF vector engine with crisp typography, official margins, headers/footers, and clean page breaks.
- **Direct Tab Printing**: Dedicated print handler rendering the vector military document directly without browser UI chrome.

### G. Official Digital Signature Bank & DSC Stamps
- **Multi-Signature Bank**: Upload and manage high-resolution scanned signatures.
- **Classic Staff Duties Format**: Standard military sign-off block with designated name, rank, appointment, and authority.
- **e-Office DSC Stamp**: High-visibility digital certificate block with IST timestamp, location, and SHA-256 air-gap digest.

### H. Multi-Tier Security & Classification
- **Classification Banners**: Top and bottom bounding boxes for `RESTRICTED`, `CONFIDENTIAL`, `SECRET`, and `UNCLASSIFIED`.
- **PIN Brute-Force Lockout**: 5 failed PIN attempts trigger a mandatory 5-minute security lockout (HTTP 429).
- **AES-256 Agile Encryption**: Exported DOCX and PDF files can be locked with a 4-digit passcode, opening natively in MS Word and Adobe Acrobat only upon password entry.

---

## 3. System Requirements

| Component | Minimum Requirement | Recommended (Optimal) |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11 (64-bit) / Linux | Windows 11 (64-bit) |
| **Processor** | Intel Core i5 / AMD Ryzen 5 (4 Cores) | Intel Core i7 / i9 / Ryzen 7 (8+ Cores) |
| **RAM** | 8 GB RAM (runs `phi3:mini`) | 16 GB - 32 GB RAM |
| **Storage** | 10 GB free space | 20 GB SSD storage |
| **Python** | Python 3.8 to 3.12 | Python 3.10 / 3.11 |
| **Network** | **100% Offline / Air-Gapped** | Local CME Intranet / LAN |

---

## 4. Quick Start Guide

### Step 1: Clone or Pull Repository
```bash
git clone https://github.com/krishnamallawat1/CME-Sarvatra-AI.git
cd CME-Sarvatra-AI
```

Select the appropriate branch:
- **For standard workstations / servers**:
  ```bash
  git checkout main
  ```
- **For 8GB / 16GB RAM workstations (`phi3:mini`)**:
  ```bash
  git checkout feature/phi3-integration
  ```

---

### Step 2: Install Python Dependencies
Install the 8 lightweight, air-gapped packages:
```bash
pip install -r requirements.txt
```
*(Dependencies: `Django`, `requests`, `PyPDF2`, `python-docx`, `PyMuPDF`, `Pillow`, `msoffcrypto-tool`, `waitress`).*

---

### Step 3: Setup Ollama (One-Time Setup)

1. **Start Ollama**: Ensure Ollama is running (check the llama icon in your Windows system tray, or run `ollama serve`).
2. **Download Model**:
   - **For 8GB / 16GB RAM Workstations**:
     ```bash
     ollama pull phi3:mini
     ```
   - **For 16GB+ RAM / GPU Workstations**:
     ```bash
     ollama pull llama3:latest
     ```
3. **Verify**:
   ```bash
   ollama list
   ```

---

### Step 4: Launch Sarvatra AI

#### Method A: One-Click Startup (Recommended)
Double-click:
```
start_server.bat
```
*(or run `python run_desktop.py` in terminal).*

This automatically applies migrations, checks static assets, and launches `http://127.0.0.1:8000` in your default browser. It also binds to `0.0.0.0:8000` so other workstation PCs on the CME LAN can access it via your PC's IP address.

#### Method B: Manual Django Server
```bash
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```
Open **`http://127.0.0.1:8000`** in Google Chrome or Microsoft Edge.

---

## 5. Keyboard Shortcuts

| Shortcut | Context | Action |
| :--- | :--- | :--- |
| **`Ctrl + Enter`** | Chat Input / Studio Revision Bar | Submit message or regenerate document with revision instructions |
| **`Ctrl + D`** | Global (Anywhere in App) | Open / Close Document Formulation Studio |
| **`Esc`** | Modals / Previewer | Close highest active dialog (Security, PIN, or PDF preview modal) |

---

## 6. Verification & Test Suites

The codebase includes comprehensive automated test suites to ensure 100% offline stability:

### Run Full 7-Archetype Pipeline Audit
```bash
python scratch/full_archetype_audit.py
```
*Validates document creation, default finalized state, DOCX integrity on disk, vector PDF generation, iframe preview headers, direct download endpoints, in-place content editing, and revision parameter extraction across all 7 archetypes.*

### Run Complete Regression Suite
```bash
python scratch/test_v38_features.py
```
*Validates IST timezone configuration, SQLite WAL mode, PIN brute-force lockout, Indian Army staff duties prompting, offline revision engine, leave application generation, digital signature bank, draft watermark lifecycle, and automated database backups.*

---

## 7. Air-Gap & Military Security Architecture

- **Zero Cloud Leakage**: No telemetry, analytics, or external API calls are made.
- **Embedded Static Assets**: All fonts, icons, CSS, and JS libraries are bundled locally without third-party CDNs.
- **SQLite WAL Mode**: Provides fast, crash-resilient concurrent reads and writes for multi-officer access.
- **Encrypted Local Storage**: Passcode-locked documents utilize ECMA-376 Agile AES-256 standard encryption compatible with official MS Office and Adobe Acrobat viewers.

---

## 8. Maintainers

- **Project Lead**: College of Military Engineering (CME), Dapodi, Pune
- **Mentorship & Direction**: Nehul Patel, CME Pune
- **Engineering & Implementation**: Krishna Mallawat (`internshipfem`)
