# 🌐 Distributed Network Setup Guide

## Run Your Network Across Multiple Laptops!

This guide shows you how to run Node A on one laptop, Node B on another, and see them communicate in real-time on the dashboard.

---

## 📋 Prerequisites

### **What You Need:**
- 2-4 laptops
- All connected to the **same WiFi network**
- Python 3.8+ installed on each laptop
- Project files copied to each laptop

### **Required Python Packages:**
```bash
pip install flask flask-cors requests
```

---

## 🚀 Quick Setup (2 Laptops)

### **Laptop 1 (Dashboard + Node A)**

**Step 1: Find your IP address**

Windows:
```bash
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter (e.g., `192.168.1.100`)

Mac/Linux:
```bash
ifconfig
```
Look for "inet" under your WiFi interface (e.g., `192.168.1.100`)

**Step 2: Start Node A with Dashboard**
```bash
python distributed_node.py --node A --dashboard --peer 192.168.1.101
```

Replace `192.168.1.101` with Laptop 2's IP address.

**Step 3: Open Dashboard**
```
http://192.168.1.100:5000
```
(Use your actual IP address)

---

### **Laptop 2 (Node B)**

**Step 1: Find Laptop 1's IP**
Ask your teammate or check Laptop 1's IP (e.g., `192.168.1.100`)

**Step 2: Start Node B**
```bash
python distributed_node.py --node B --peer 192.168.1.100 --dashboard-host 192.168.1.100
```

Replace `192.168.1.100` with Laptop 1's actual IP address.

---

## 🎯 What You'll See

### **On Laptop 1 (Dashboard):**
- Web dashboard showing real-time metrics
- Network topology with Node A and Node B
- Packets flowing between nodes
- Live metrics updating

### **On Laptop 2 (Terminal):**
```
Node B started on port 5001
Added peer A at 192.168.1.100:5001
Sent packet to A: Hello from B at 2026-03-04...
Received packet from A: Hello from A at 2026-03-04...
```

### **On Both Laptops:**
You'll see packets being sent and received in real-time!

---

## 🏗️ Full Setup (4 Laptops)

### **Network Topology:**
```
Laptop 1 (Node A + Dashboard) ←→ Laptop 2 (Node B)
        ↕                              ↕
Laptop 4 (Node D)             ←→ Laptop 3 (Node C)
```

### **Step-by-Step:**

**1. Find all IP addresses:**
- Laptop 1: `192.168.1.100` (example)
- Laptop 2: `192.168.1.101`
- Laptop 3: `192.168.1.102`
- Laptop 4: `192.168.1.103`

**2. Start Laptop 1 (Dashboard + Node A):**
```bash
python distributed_node.py --node A --dashboard \
    --peer 192.168.1.101 \
    --peer 192.168.1.102 \
    --peer 192.168.1.103
```

**3. Start Laptop 2 (Node B):**
```bash
python distributed_node.py --node B \
    --peer 192.168.1.100 \
    --dashboard-host 192.168.1.100
```

**4. Start Laptop 3 (Node C):**
```bash
python distributed_node.py --node C \
    --peer 192.168.1.100 \
    --dashboard-host 192.168.1.100
```

**5. Start Laptop 4 (Node D):**
```bash
python distributed_node.py --node D \
    --peer 192.168.1.100 \
    --dashboard-host 192.168.1.100
```

**6. Open Dashboard:**
On any laptop, open browser to:
```
http://192.168.1.100:5000
```

---

## 🔧 Troubleshooting

### **Problem: "Connection refused"**

**Solution:** Check firewall settings

**Windows:**
```powershell
# Allow Python through firewall
netsh advfirewall firewall add rule name="Python" dir=in action=allow program="C:\Python\python.exe" enable=yes
```

**Mac:**
```bash
# System Preferences → Security & Privacy → Firewall → Firewall Options
# Allow Python
```

**Linux:**
```bash
sudo ufw allow 5000
sudo ufw allow 5001
```

---

### **Problem: "Cannot find peer"**

**Solution:** Verify IP addresses

1. On each laptop, run:
   ```bash
   ipconfig  # Windows
   ifconfig  # Mac/Linux
   ```

2. Make sure all laptops are on the **same WiFi network**

3. Test connectivity:
   ```bash
   ping 192.168.1.100  # Replace with actual IP
   ```

---

### **Problem: "Dashboard not loading"**

**Solution:** Check dashboard host

1. Make sure Laptop 1 started with `--dashboard` flag
2. Use Laptop 1's IP address (not 127.0.0.1)
3. Try accessing from Laptop 1 first:
   ```
   http://localhost:5000
   ```
4. Then try from other laptops:
   ```
   http://192.168.1.100:5000
   ```

---

## 📊 Command Reference

### **Basic Commands:**

**Start node with dashboard:**
```bash
python distributed_node.py --node A --dashboard --peer <PEER_IP>
```

**Start node without dashboard:**
```bash
python distributed_node.py --node B --peer <DASHBOARD_IP> --dashboard-host <DASHBOARD_IP>
```

**Custom port:**
```bash
python distributed_node.py --node A --port 6000 --dashboard
```

### **Arguments:**

| Argument | Description | Example |
|----------|-------------|---------|
| `--node` | Node ID (A, B, C, or D) | `--node A` |
| `--port` | Port to listen on | `--port 5001` |
| `--peer` | Peer IP address (can use multiple times) | `--peer 192.168.1.100` |
| `--dashboard` | Run dashboard on this machine | `--dashboard` |
| `--dashboard-host` | Dashboard IP for metrics | `--dashboard-host 192.168.1.100` |

---

## 🎬 Demo Workflow

### **For Presentation:**

**Setup (5 minutes before):**
1. Connect all laptops to same WiFi
2. Find all IP addresses
3. Start nodes on each laptop
4. Verify connectivity

**During Presentation:**
1. Show dashboard on projector (Laptop 1)
2. Point to each laptop: "This is Node A, B, C, D"
3. Show terminal output on one laptop
4. Explain: "These laptops are communicating over real network"
5. Point to dashboard: "See the packets flowing in real-time"

**Impressive Points:**
- "This is running on actual hardware, not simulation"
- "Each laptop is an independent node"
- "They're communicating over WiFi"
- "Dashboard shows real network traffic"

---

## 🔍 Verification Steps

### **1. Check Node Started:**
```
Node A started on port 5001
✓ Node A is ready!
```

### **2. Check Peers Added:**
```
Added peer B at 192.168.1.101:5001
Added peer C at 192.168.1.102:5001
```

### **3. Check Packets Flowing:**
```
Sent packet to B: Hello from A at 2026-03-04...
Received packet from B: Hello from B at 2026-03-04...
```

### **4. Check Dashboard:**
- Open `http://<DASHBOARD_IP>:5000`
- See nodes in topology
- See metrics updating
- See packet counts increasing

---

## 📈 Expected Output

### **Terminal (Each Node):**
```
======================================================================
  DISTRIBUTED NETWORK NODE A
======================================================================

Starting dashboard...
✓ Dashboard started at http://0.0.0.0:5000

Node A started on port 5001
Added peer B at 192.168.1.101:5001
Added peer C at 192.168.1.102:5001

Node A Configuration:
  - Listening on: 0.0.0.0:5001
  - Peers: ['B', 'C']
  - Dashboard: http://0.0.0.0:5000

Press Ctrl+C to stop
======================================================================

2026-03-04 10:30:15 - INFO - Sent packet to B: Hello from A...
2026-03-04 10:30:15 - INFO - Sent packet to C: Hello from A...
2026-03-04 10:30:16 - INFO - Received packet from B: Hello from B...
2026-03-04 10:30:17 - INFO - Received packet from C: Hello from C...
```

---

## 🎯 Minimal 2-Laptop Setup

If you only have 2 laptops:

**Laptop 1:**
```bash
python distributed_node.py --node A --dashboard --peer 192.168.1.101
```

**Laptop 2:**
```bash
python distributed_node.py --node B --peer 192.168.1.100 --dashboard-host 192.168.1.100
```

**Dashboard:**
```
http://192.168.1.100:5000
```

This is enough to demonstrate distributed networking!

---

## 💡 Tips for Success

### **Before Demo:**
1. ✅ Test on same WiFi network
2. ✅ Write down all IP addresses
3. ✅ Test connectivity with ping
4. ✅ Disable firewalls or add exceptions
5. ✅ Have backup: run simulation if network fails

### **During Demo:**
1. ✅ Start dashboard laptop first
2. ✅ Wait for "Dashboard started" message
3. ✅ Start other laptops one by one
4. ✅ Verify each node connects
5. ✅ Open dashboard last

### **If Something Fails:**
1. ✅ Have `live_demo.py` ready as backup
2. ✅ Explain: "This is simulation mode, but same algorithms"
3. ✅ Show the code to prove it's real

---

## 🎓 What to Tell Your Professor

> "We've implemented a distributed version where each node runs on a separate laptop. They communicate over WiFi using UDP sockets. The dashboard aggregates metrics from all nodes in real-time. This demonstrates that our protocol stack works on actual hardware, not just in simulation."

**Key Points:**
- Real network communication (UDP sockets)
- Distributed architecture (multiple machines)
- Real-time metrics aggregation
- Same algorithms as simulation
- Production-ready code

---

## 📚 Technical Details

### **Communication Protocol:**
- **Transport**: UDP (User Datagram Protocol)
- **Port**: 5001 (configurable)
- **Format**: JSON messages
- **Packet Structure**:
  ```json
  {
    "from": "A",
    "to": "B",
    "data": "Hello from A",
    "timestamp": 1234567890.123
  }
  ```

### **Metrics Reporting:**
- **Protocol**: HTTP POST
- **Endpoint**: `/api/node_metrics`
- **Frequency**: Every 1 second
- **Format**: JSON

---

## 🚀 You're Ready!

You now have:
- ✅ Distributed node implementation
- ✅ Complete setup guide
- ✅ Troubleshooting steps
- ✅ Demo workflow
- ✅ Backup plan

Go impress your professor with real distributed networking! 🎉

---

**Quick Start Command (Copy-Paste):**

**Laptop 1 (Dashboard):**
```bash
python distributed_node.py --node A --dashboard --peer <LAPTOP2_IP>
```

**Laptop 2:**
```bash
python distributed_node.py --node B --peer <LAPTOP1_IP> --dashboard-host <LAPTOP1_IP>
```

**Dashboard URL:**
```
http://<LAPTOP1_IP>:5000
```

Replace `<LAPTOP1_IP>` and `<LAPTOP2_IP>` with actual IP addresses!
