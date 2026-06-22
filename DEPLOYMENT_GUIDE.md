# Deployment Guide: Adaptive Network Emulator
## How to Run This Project on Any Laptop

---

## 📋 Table of Contents
1. [System Requirements](#system-requirements)
2. [Quick Start (5 Minutes)](#quick-start-5-minutes)
3. [Detailed Installation Steps](#detailed-installation-steps)
4. [Running the Project](#running-the-project)
5. [Troubleshooting](#troubleshooting)
6. [What to Show in Demo](#what-to-show-in-demo)

---

## 🖥️ System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: Version 3.8 or higher
- **RAM**: 4 GB minimum (8 GB recommended)
- **Disk Space**: 500 MB free space
- **Internet**: Required for initial setup only

### Recommended Setup
- **Python**: 3.10 or 3.11
- **RAM**: 8 GB or more
- **CPU**: Dual-core or better
- **Browser**: Chrome, Firefox, or Edge (latest version)

---

## ⚡ Quick Start (5 Minutes)

### For Windows:

```bash
# 1. Open Command Prompt or PowerShell
# Navigate to project folder
cd path\to\adaptive-network-emulator

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the demo
python live_demo.py
```

### For macOS/Linux:

```bash
# 1. Open Terminal
# Navigate to project folder
cd path/to/adaptive-network-emulator

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the demo
python live_demo.py
```

### Expected Output:
```
======================================================================
  LIVE NETWORK EMULATOR DEMO
  Real-Time Adaptive Network Simulation with Dashboard
======================================================================

✓ Dashboard started at http://127.0.0.1:5000

Starting network simulation in 3 seconds...
```

### Open Browser:
Navigate to: **http://127.0.0.1:5000**

---

## 📦 Detailed Installation Steps

### Step 1: Check Python Installation

**Windows:**
```bash
python --version
```

**macOS/Linux:**
```bash
python3 --version
```

**Expected output:** `Python 3.8.x` or higher

**If Python is not installed:**
- Windows: Download from https://www.python.org/downloads/
- macOS: `brew install python3` (requires Homebrew)
- Linux: `sudo apt-get install python3 python3-pip`

### Step 2: Download/Copy Project Files

**Option A: From USB/External Drive**
1. Copy the entire `adaptive-network-emulator` folder to your laptop
2. Note the location (e.g., `C:\Users\YourName\Documents\adaptive-network-emulator`)

**Option B: From Git Repository (if available)**
```bash
git clone <repository-url>
cd adaptive-network-emulator
```

**Option C: From ZIP File**
1. Extract the ZIP file
2. Navigate to the extracted folder

### Step 3: Create Virtual Environment

**Why?** Isolates project dependencies from system Python.

**Windows:**
```bash
cd path\to\adaptive-network-emulator
python -m venv venv
```

**macOS/Linux:**
```bash
cd path/to/adaptive-network-emulator
python3 -m venv venv
```

**Verification:** You should see a new `venv` folder created.

### Step 4: Activate Virtual Environment

**Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Verification:** Your prompt should now show `(venv)` at the beginning.

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected output:**
```
Collecting pytest>=7.0
Collecting hypothesis>=6.0
Collecting Flask>=2.0
...
Successfully installed Flask-2.3.0 hypothesis-6.92.0 pytest-7.4.3 ...
```

**Installation time:** 2-5 minutes depending on internet speed.

### Step 6: Verify Installation

```bash
python -c "import flask, hypothesis, pytest; print('✓ All dependencies installed')"
```

**Expected output:** `✓ All dependencies installed`

---

## 🚀 Running the Project

### Option 1: Live Demo (Recommended for Presentation)

**What it does:** Runs a complete 85-second simulation showing all features.

```bash
python live_demo.py
```

**What you'll see:**
1. Dashboard starts at http://127.0.0.1:5000
2. Simulation runs through 5 phases:
   - Phase 1: Normal operation (20s)
   - Phase 2: Traffic burst (15s)
   - Phase 3: Network congestion (20s)
   - Phase 4: Node failure (15s)
   - Phase 5: Recovery (15s)
3. Real-time metrics update on dashboard
4. Adaptive window size adjustments
5. Protocol state changes

**To stop:** Press `Ctrl+C`

### Option 2: Dashboard Only (For Manual Testing)

**What it does:** Starts dashboard with sample data, no automatic simulation.

```bash
python start_dashboard.py
```

**Use case:** When you want to manually control the demo or show static data.

### Option 3: Run Tests (For Technical Validation)

**Run all tests:**
```bash
pytest tests/ -v
```

**Run specific test categories:**
```bash
# Property-based tests (formal correctness)
pytest tests/test_properties_*.py -v

# Integration tests
pytest tests/test_integration_*.py -v

# Unit tests
pytest tests/test_*.py -v --ignore=tests/test_properties_* --ignore=tests/test_integration_*
```

**Expected results:**
- Total tests: 730+
- Pass rate: 99%+
- Execution time: 2-3 minutes

---

## 🌐 Accessing the Dashboard

### Local Access (Same Computer)
1. Open browser
2. Navigate to: **http://127.0.0.1:5000** or **http://localhost:5000**

### Network Access (Other Devices on Same WiFi)
1. Find your computer's IP address:
   - Windows: `ipconfig` (look for IPv4 Address)
   - macOS/Linux: `ifconfig` or `ip addr`
2. On other device, navigate to: **http://YOUR_IP:5000**
   - Example: http://192.168.1.100:5000

### Projector/Presentation Mode
1. Open browser in fullscreen (F11)
2. Navigate to dashboard
3. Zoom in if needed (Ctrl/Cmd + Plus)

---

## 📁 What Files to Copy to Other Laptops

### Essential Files (Minimum for Demo):
```
adaptive-network-emulator/
├── src/                          # All source code
├── tests/                        # All test files
├── config/                       # Configuration files
├── requirements.txt              # Dependencies
├── live_demo.py                  # Main demo script
├── start_dashboard.py            # Dashboard launcher
├── README.md                     # Basic instructions
├── DEMO_EXPLANATION.md           # Demo guide
└── DEPLOYMENT_GUIDE.md           # This file
```

### Optional Files (For Full Documentation):
```
├── TECHNICAL_REPORT.md           # Full technical details
├── LITERATURE_REVIEW.md          # Research context
├── PROJECT_STRUCTURE.md          # Code organization
├── PATENT_DISCLOSURE.md          # Innovation details
└── .kiro/specs/                  # Specification documents
```

### Files to EXCLUDE (Don't Copy):
```
├── venv/                         # Virtual environment (recreate on each machine)
├── .hypothesis/                  # Test cache (regenerates)
├── .pytest_cache/                # Test cache (regenerates)
├── __pycache__/                  # Python cache (regenerates)
├── .coverage                     # Coverage data (regenerates)
└── logs/                         # Log files (regenerates)
```

### Recommended: Create a ZIP File

**What to include:**
1. All source code (`src/`)
2. All tests (`tests/`)
3. Configuration (`config/`)
4. Demo scripts (`live_demo.py`, `start_dashboard.py`)
5. Documentation (`*.md` files)
6. Dependencies list (`requirements.txt`)

**Size:** Approximately 5-10 MB

---

## 🔧 Troubleshooting

### Problem: "Python is not recognized"

**Solution:**
1. Install Python from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Restart Command Prompt/Terminal
4. Try again

### Problem: "pip is not recognized"

**Solution:**
```bash
python -m pip install --upgrade pip
```

### Problem: "Permission denied" when activating venv (Windows PowerShell)

**Solution:**
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating again.

### Problem: "Module not found" errors

**Solution:**
```bash
# Make sure virtual environment is activated (you should see (venv) in prompt)
# Then reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Problem: Dashboard doesn't open in browser

**Solution:**
1. Check if port 5000 is already in use:
   - Windows: `netstat -ano | findstr :5000`
   - macOS/Linux: `lsof -i :5000`
2. If in use, kill the process or change port in script
3. Check firewall settings (allow Python through firewall)
4. Try http://127.0.0.1:5000 instead of localhost

### Problem: "Address already in use" error

**Solution:**
```bash
# Kill existing process on port 5000
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F

# macOS/Linux:
lsof -i :5000
kill -9 <PID_NUMBER>
```

### Problem: Tests fail with "hypothesis" errors

**Solution:**
```bash
# Clear hypothesis cache
rm -rf .hypothesis/  # macOS/Linux
rmdir /s .hypothesis  # Windows

# Reinstall hypothesis
pip install hypothesis --upgrade
```

### Problem: Slow performance during demo

**Solution:**
1. Close other applications
2. Reduce browser zoom level
3. Use Chrome or Firefox (better performance)
4. Check CPU usage (Task Manager/Activity Monitor)

### Problem: Dashboard shows no data

**Solution:**
1. Wait 3-5 seconds after starting (data loads gradually)
2. Check browser console for errors (F12)
3. Refresh page (F5)
4. Restart demo script

---

## 🎯 What to Show in Demo

### 1. Start the Demo (30 seconds)
```bash
python live_demo.py
```
- Show the terminal output
- Open browser to http://127.0.0.1:5000
- Point out the dashboard components

### 2. Explain the Dashboard (1 minute)
- **Top metrics**: Throughput, Latency, Packet Loss, Jitter
- **Charts**: Real-time graphs showing trends
- **Topology**: Network visualization with animated packets
- **Protocol State**: Adaptive window size (key innovation!)
- **Alerts**: Real-time notifications

### 3. Watch Phase 3 - Congestion (30 seconds)
- Point out nodes turning yellow
- Show packet loss increasing
- **Highlight**: Window size dropping from 48 → 8 (adaptive behavior!)
- Explain: "This is the algorithm preventing network collapse"

### 4. Watch Phase 4 - Node Failure (30 seconds)
- Point out Node C turning red
- Show traffic rerouting
- Explain: "Network continues operating despite failure"

### 5. Show the Code (Optional, 1 minute)
```bash
# Open in text editor
notepad live_demo.py  # Windows
open -a TextEdit live_demo.py  # macOS
nano live_demo.py  # Linux
```
- Show it's real Python code, not hardcoded
- Point out the simulation logic
- Show metric calculations

### 6. Run Tests (Optional, 2 minutes)
```bash
pytest tests/test_properties_dashboard.py -v
```
- Show formal correctness validation
- Explain property-based testing
- Point out 100+ test iterations per property

---

## 📊 Demo Checklist

Before presenting, verify:

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip list` shows Flask, hypothesis, pytest)
- [ ] Demo runs without errors (`python live_demo.py`)
- [ ] Dashboard opens in browser (http://127.0.0.1:5000)
- [ ] Metrics update in real-time
- [ ] Topology shows animated packets
- [ ] Window size changes during congestion
- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Browser is in fullscreen mode (F11)
- [ ] Zoom level is appropriate for audience
- [ ] Backup: Screenshots of dashboard in case of technical issues

---

## 🎓 Presentation Tips

### For Technical Audience:
1. Start with architecture overview
2. Show the code (`live_demo.py`)
3. Run tests to prove correctness
4. Explain adaptive algorithm
5. Show property-based testing methodology

### For Non-Technical Audience:
1. Start with the problem (network congestion)
2. Show the dashboard (visual, easy to understand)
3. Point out adaptive behavior (window size changes)
4. Use analogies (highway traffic management)
5. Emphasize real-world applications

### For Investors/Business:
1. Market size and problem statement
2. Show the working demo (proof of concept)
3. Highlight innovations (4 patents pending)
4. Show test results (99%+ pass rate)
5. Discuss commercialization path

---

## 📞 Support & Resources

### Documentation Files:
- **DEMO_EXPLANATION.md**: Detailed explanation of what's happening
- **TECHNICAL_REPORT.md**: Full implementation details
- **LITERATURE_REVIEW.md**: Research context and related work
- **PROJECT_STRUCTURE.md**: Code organization

### Quick Reference Commands:

```bash
# Start demo
python live_demo.py

# Start dashboard only
python start_dashboard.py

# Run all tests
pytest tests/ -v

# Run specific tests
pytest tests/test_properties_*.py -v

# Check dependencies
pip list

# Update dependencies
pip install -r requirements.txt --upgrade

# Deactivate virtual environment
deactivate
```

---

## 🔄 Updating the Project

If you make changes and need to update on other laptops:

1. **Copy changed files only** (faster than full copy)
2. **No need to reinstall dependencies** (unless requirements.txt changed)
3. **Clear Python cache** if behavior seems wrong:
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} +  # macOS/Linux
   ```

---

## 💾 Backup & Recovery

### Create Backup:
```bash
# Create ZIP of entire project
# Windows: Right-click folder → Send to → Compressed folder
# macOS: Right-click folder → Compress
# Linux: tar -czf adaptive-network-emulator.tar.gz adaptive-network-emulator/
```

### Restore from Backup:
1. Extract ZIP file
2. Follow installation steps above
3. No need to copy venv/ folder (recreate it)

---

## 🌟 Success Criteria

You know the setup is successful when:

✅ `python live_demo.py` runs without errors  
✅ Dashboard opens at http://127.0.0.1:5000  
✅ Metrics update in real-time  
✅ Topology shows animated packets  
✅ Window size changes during congestion phase  
✅ Tests pass with 99%+ success rate  
✅ No error messages in terminal  
✅ Browser shows all dashboard components  

---

## 📝 Pre-Demo Setup (Day Before)

1. **Test on presentation laptop:**
   - Install and run demo
   - Verify browser compatibility
   - Check projector resolution
   - Test with projector connected

2. **Prepare backup plan:**
   - Take screenshots of dashboard
   - Record video of demo (optional)
   - Print key slides/diagrams
   - Have USB backup of project files

3. **Practice timing:**
   - Full demo: 85 seconds
   - Your explanation: 2-3 minutes
   - Q&A buffer: 5 minutes
   - Total: ~10 minutes

4. **Prepare talking points:**
   - Review DEMO_EXPLANATION.md
   - Prepare answers to common questions
   - Have technical report ready for deep dives

---

## 🎬 Day-of-Demo Checklist

**30 minutes before:**
- [ ] Laptop charged and plugged in
- [ ] Close unnecessary applications
- [ ] Disable notifications
- [ ] Test internet connection (if needed)
- [ ] Open terminal and navigate to project folder
- [ ] Activate virtual environment
- [ ] Test run: `python live_demo.py`
- [ ] Open browser to dashboard
- [ ] Set browser to fullscreen (F11)
- [ ] Adjust zoom for visibility

**5 minutes before:**
- [ ] Close test run (Ctrl+C)
- [ ] Clear terminal
- [ ] Position terminal and browser windows
- [ ] Have backup screenshots ready
- [ ] Take a deep breath 😊

**During demo:**
- [ ] Start with clear explanation
- [ ] Run `python live_demo.py`
- [ ] Switch to browser
- [ ] Point out key features as they happen
- [ ] Highlight adaptive behavior
- [ ] Answer questions confidently

---

## 🚀 Advanced: Running on Multiple Machines

### Scenario: Dashboard on one laptop, simulation on another

**Machine 1 (Dashboard Server):**
```bash
# Modify start_dashboard.py to accept external connections
# Change host from "127.0.0.1" to "0.0.0.0"
python start_dashboard.py
```

**Machine 2 (Simulation Client):**
```bash
# Modify live_demo.py to connect to remote dashboard
# Change dashboard host to Machine 1's IP address
python live_demo.py
```

**Use case:** Large screen for dashboard, separate control laptop.

---

## 📧 Contact & Support

If you encounter issues not covered here:

1. Check error message carefully
2. Search error message online
3. Review documentation files
4. Check Python version compatibility
5. Verify all dependencies installed

---

**Last Updated:** March 4, 2026  
**Version:** 1.0  
**Tested On:** Windows 10/11, macOS 12+, Ubuntu 20.04+

---

## 🎉 You're Ready!

Follow this guide step-by-step, and you'll have the Adaptive Network Emulator running on any laptop in under 10 minutes. Good luck with your demo! 🚀
