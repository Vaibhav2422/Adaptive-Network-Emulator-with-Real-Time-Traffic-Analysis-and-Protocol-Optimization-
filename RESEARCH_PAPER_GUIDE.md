# Research Paper Writing Guide
### Adaptive Network Emulator — Course Project

---

## Is Your Structure Correct?

Yes, your structure is on the right track. Here is the **corrected and complete standard structure** for a research/conference paper:

```
Title
Authors & Affiliations
Abstract
Keywords
1. Introduction
2. Literature Review (Related Work)
3. System Design & Architecture
4. Methodology / Implementation
5. Results & Discussion
6. Conclusion
7. Future Work
8. References
   Appendix (optional)
```

Your sections 6, 7, 8 were blank — those are **Conclusion**, **Future Work**, and **References**. These are mandatory. Never skip References in a research paper.

---

## Full Paper Structure with Guidance

---

### TITLE

**Format:** Bold, centered, 14–16pt font
**What to write:** Should be specific and descriptive. Avoid vague titles.

**Bad title:** "Network Project"
**Good title:** "Adaptive Network Protocol Emulator with Property-Based Correctness Validation and Dynamic Congestion Optimization"

**Tips:**
- Keep it under 15 words if possible
- Include the key innovation (adaptive, property-based, dynamic)
- No abbreviations in the title

---

### AUTHORS & AFFILIATIONS

**Format:**
```
Vaibhav Hade¹, Omkar Ghanure¹, Satyajeet Ghadge¹, Aaryan Giri¹, Onkar Gawde¹

¹Department of [Your Department], [Your College Name], [City], India
Corresponding Author: [email]
```

---

### ABSTRACT

**Length:** 150–250 words (strictly one paragraph, no bullet points)
**What to cover (in order):**
1. What problem does this paper address?
2. What did you build/propose?
3. What method/approach did you use?
4. What are the key results (numbers)?
5. What is the conclusion/significance?

**Example structure for your project:**
> Network protocol development is error-prone and difficult to validate formally. This paper presents an Adaptive Network Protocol Emulator — a software-based simulation system implementing the complete 7-layer OSI protocol stack in Python. The system introduces a novel adaptive congestion control algorithm that dynamically adjusts transmission window size based on real-time packet loss and latency metrics. Correctness is formally validated using property-based testing with 38 executable properties verified over 100+ random iterations each. Experimental results demonstrate an average throughput improvement of 18.3% over static protocols, with 78.8% improvement under 10% packet loss conditions. The system achieves a 99.5% test pass rate across 734 automated tests. Compared to existing tools such as NS-3 and OMNeT++, the proposed emulator offers unique advantages in formal validation, adaptive optimization, and ease of use, making it suitable for both educational and research applications.

**Keywords (5–7 words):**
Network Emulation, Adaptive Congestion Control, Property-Based Testing, Protocol Stack, Go-Back-N, Selective Repeat, Dijkstra Routing

---

### 1. INTRODUCTION

**Length:** 1–1.5 pages
**What to cover:**
- Background: What is network emulation? Why is it important?
- Problem statement: What gap exists in current tools?
- Motivation: Why did you build this?
- Contributions: List 3–5 bullet points of what this paper contributes
- Paper organization: "The rest of this paper is organized as follows..."

**Subsections (optional but good):**
```
1.1 Background
1.2 Problem Statement
1.3 Motivation
1.4 Contributions
1.5 Paper Organization
```

**Contributions box example:**
> The main contributions of this paper are:
> - A complete 7-layer protocol stack emulator implemented in Python
> - A novel adaptive congestion control algorithm achieving 18.3% throughput improvement
> - A property-based testing framework with 38 formal correctness properties
> - A real-time web dashboard with Server-Sent Events for live monitoring
> - A reproducible experimentation framework with deterministic simulation

---

### 2. LITERATURE REVIEW (Related Work)

**Length:** 1–2 pages
**What to cover:** What existing work exists? How is yours different?

**Subsections:**
```
2.1 Network Simulation Tools (NS-3, OMNeT++, Mininet)
2.2 Transport Layer Protocols (GBN, SR, TCP variants)
2.3 Routing Algorithms (Dijkstra, Distance Vector, OSPF)
2.4 Error Detection and Correction (CRC, Hamming)
2.5 Property-Based Testing (QuickCheck, Hypothesis)
2.6 Adaptive Network Optimization
2.7 Research Gap
```

**How to write each paragraph:**
- Cite the paper: "[Author, Year] proposed..."
- Describe what they did in 1–2 sentences
- State the limitation: "However, this approach does not..."
- End the section with a gap analysis paragraph explaining what is missing and how your work fills it

**Table you can add here:**

| Tool | Protocol Stack | Property Testing | Adaptive Optimization | Python API |
|------|---------------|-----------------|----------------------|------------|
| NS-3 | ✅ | ❌ | ❌ | ✅ |
| OMNeT++ | ✅ | ❌ | ❌ | ❌ |
| Mininet | ❌ | ❌ | ❌ | ✅ |
| **This Work** | **✅** | **✅** | **✅** | **✅** |

---

### 3. SYSTEM DESIGN & ARCHITECTURE

**Length:** 1.5–2 pages
**What to cover:** How is the system designed? What are the components?

**Subsections:**
```
3.1 High-Level Architecture
3.2 Protocol Stack Design (7 Layers)
3.3 Adaptive Optimization Module
3.4 Monitoring Dashboard
3.5 Data Models
```

**Figures to include:**
- Figure 1: High-level architecture block diagram (4 layers: UI → Monitoring → Protocol Stack → Nodes)
- Figure 2: 7-layer protocol stack diagram
- Figure 3: Packet flow diagram (encapsulation top-down, decapsulation bottom-up)
- Figure 4: Adaptive algorithm flowchart

**Table for layer overview:**

| Layer | Module | Key Feature |
|-------|--------|-------------|
| Physical (L1) | physical_layer.py | Latency, loss, jitter simulation |
| Data Link (L2) | data_link_layer.py | CRC-32, Hamming code |
| MAC (L2) | mac_layer.py | CSMA/CD, exponential backoff |
| Network (L3) | network_layer.py | Dijkstra, Distance Vector routing |
| Transport (L4) | transport_layer.py | GBN, SR, adaptive window |
| Application (L7) | application_layer.py | HTTP, DNS, FTP, file transfer |

**Algorithm box (for adaptive congestion control):**
```
Algorithm 1: Adaptive Window Adjustment
Input: current_window, packet_loss, latency, threshold
Output: adjusted_window

if packet_loss > loss_threshold then
    window ← max(MIN_WINDOW, window / 2)
else if latency < latency_target then
    window ← min(MAX_WINDOW, window + 1)
return window
```

---

### 4. METHODOLOGY / IMPLEMENTATION

**Length:** 1–1.5 pages
**What to cover:** How did you implement it? What tools, languages, testing approach?

**Subsections:**
```
4.1 Implementation Environment
4.2 Protocol Implementation Details
4.3 Property-Based Testing Methodology
4.4 Experiment Setup
```

**Table — Implementation environment:**

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12.7 |
| Web Framework | Flask 3.0+ |
| Testing Framework | pytest 9.0.2 |
| Property Testing | Hypothesis 6.151.5 |
| Frontend Charts | Chart.js 4.4 |
| Real-time Updates | Server-Sent Events (SSE) |
| Configuration | YAML |

**Table — Experiment parameters:**

| Parameter | Value |
|-----------|-------|
| Number of nodes | 4 (A, B, C, D) |
| Link bandwidth | 100 Mbps |
| Base latency | 10–50 ms |
| Packet loss range | 0–20% |
| Window size range | 8–48 packets |
| Simulation duration | 60 seconds |
| Random seed | 42 (reproducible) |
| Property test iterations | 100+ per property |

**How to explain property-based testing:**
> Unlike example-based testing where specific inputs are manually chosen, property-based testing defines universal invariants that must hold for all valid inputs. The Hypothesis library automatically generates random test cases to falsify each property. If a counterexample is found, it is automatically shrunk to the minimal failing case.

---

### 5. RESULTS & DISCUSSION

**Length:** 1.5–2 pages
**What to cover:** What did you measure? What do the numbers show? What do they mean?

**Subsections:**
```
5.1 Correctness Validation Results
5.2 Throughput Performance
5.3 Latency Analysis
5.4 Routing Algorithm Performance
5.5 Optimization Effectiveness
5.6 Scalability Analysis
```

**Tables to include:**

**Table — Test results:**

| Category | Total Tests | Passed | Failed | Pass Rate |
|----------|------------|--------|--------|-----------|
| Unit Tests | 308 | 308 | 0 | 100% |
| Property Tests | 218 | 218 | 0 | 100% |
| Integration Tests | 75 | 71 | 4 | 94.7% |
| E2E Tests | 59 | 59 | 0 | 100% |
| **Total** | **660** | **656** | **4** | **99.4%** |

**Table — Throughput comparison (GBN vs SR vs Adaptive):**

| Loss Rate | GBN (Mbps) | SR (Mbps) | Adaptive (Mbps) | Improvement |
|-----------|-----------|----------|----------------|-------------|
| 0% | 95.2 | 95.3 | 95.3 | 0% |
| 1% | 87.4 | 91.2 | 92.1 | +5.4% |
| 5% | 62.3 | 78.9 | 81.4 | +30.6% |
| 10% | 38.2 | 61.7 | 68.3 | +78.8% |
| 20% | 15.6 | 38.4 | 45.2 | +189.7% |

**Table — Routing algorithm performance:**

| Nodes | Dijkstra Time | Distance Vector Time | DV Iterations |
|-------|--------------|---------------------|---------------|
| 3 | 0.12ms | 0.18ms | 2 |
| 5 | 0.24ms | 0.45ms | 3 |
| 10 | 0.68ms | 1.82ms | 5 |

**Table — Latency overhead:**

| Network Delay | Measured | Overhead |
|--------------|----------|----------|
| 10ms | 10.2ms | 2.0% |
| 50ms | 50.8ms | 1.6% |
| 100ms | 101.3ms | 1.3% |
| 200ms | 202.1ms | 1.05% |

**Figures to include:**
- Figure 5: Line graph — Throughput vs Packet Loss Rate (3 lines: GBN, SR, Adaptive)
- Figure 6: Bar chart — Routing algorithm computation time
- Figure 7: Dashboard screenshot
- Figure 8: Window size adaptation over time (shows the adaptive behavior)

**Discussion tips:**
- Don't just repeat the numbers — explain what they mean
- "The results show that adaptive optimization is most effective under high loss conditions, achieving 78.8% improvement at 10% loss. This is because..."
- Mention the 4 failing integration tests honestly: "Four integration tests related to node ID to IP address mapping remain unresolved and are planned for future work."

---

### 6. CONCLUSION

**Length:** Half a page (3–5 short paragraphs)
**What to cover:**
- Restate what you built (1 sentence)
- Summarize key results (2–3 sentences with numbers)
- State the significance (1 sentence)
- Do NOT introduce new information here

**Example:**
> This paper presented an Adaptive Network Protocol Emulator implementing a complete 7-layer protocol stack with formal correctness validation and dynamic optimization. The system achieved 91.1% requirements coverage, 99.5% test pass rate across 734 automated tests, and 18.3% average throughput improvement through adaptive congestion control. Thirty-eight correctness properties were formally validated using property-based testing, discovering 12 bugs not found by manual testing. The emulator outperforms existing tools such as NS-3 in simulation speed and is the only tool offering integrated property-based testing and adaptive optimization. These results demonstrate the viability of formal validation and adaptive algorithms in network protocol development.

---

### 7. FUTURE WORK

**Length:** Half a page
**What to cover:** What can be improved or extended?

Suggested points for your project:
- Fix 4 remaining integration test failures (node ID ↔ IP mapping)
- PyShark integration for real packet capture and Wireshark analysis
- TCP variants: Reno, Cubic, BBR congestion control
- OSPF and BGP routing protocol support
- Machine learning-based congestion prediction (reinforcement learning)
- Distributed simulation supporting 100+ nodes
- Hardware-in-the-loop testing with real network devices
- Web dashboard with interactive topology editor

---

### 8. REFERENCES

**Format:** Use IEEE citation style for technical papers.

**IEEE format:**
```
[1] J. F. Kurose and K. W. Ross, Computer Networking: A Top-Down Approach, 
    8th ed. Pearson, 2021.

[2] A. S. Tanenbaum and D. J. Wetherall, Computer Networks, 5th ed. 
    Prentice Hall, 2011.

[3] E. W. Dijkstra, "A note on two problems in connexion with graphs," 
    Numerische Mathematik, vol. 1, no. 1, pp. 269–271, 1959.

[4] V. Jacobson, "Congestion avoidance and control," ACM SIGCOMM 
    Computer Communication Review, vol. 18, no. 4, pp. 314–329, 1988.

[5] K. Claessen and J. Hughes, "QuickCheck: A lightweight tool for random 
    testing of Haskell programs," ACM SIGPLAN Notices, vol. 35, no. 9, 
    pp. 268–279, 2000.

[6] D. R. MacIver, "Hypothesis: A new approach to property-based testing," 
    Journal of Open Source Software, vol. 4, no. 43, p. 1891, 2019.

[7] G. F. Riley and T. R. Henderson, "The ns-3 network simulator," in 
    Modeling and Tools for Network Simulation. Springer, 2010, pp. 15–34.

[8] A. Varga, "The OMNeT++ discrete event simulation system," in Proc. 
    European Simulation Multiconference, 2001, p. 65.

[9] B. Lantz, B. Heller, and N. McKeown, "A network in a laptop," in 
    Proc. 9th ACM SIGCOMM Workshop on Hot Topics in Networks, 2010.

[10] M. Allman, V. Paxson, and W. Stevens, "TCP Congestion Control," 
     RFC 2581, IETF, 1999.

[11] J. Moy, "OSPF Version 2," RFC 2328, IETF, 1998.

[12] R. W. Hamming, "Error detecting and error correcting codes," 
     Bell System Technical Journal, vol. 29, no. 2, pp. 147–160, 1950.
```

---

### APPENDIX (Optional)

Include here:
- Full configuration file example (YAML)
- Complete list of 38 correctness properties
- Test execution commands
- Dashboard screenshots (if not in Results)

---

## Formatting Rules for the Actual Paper

### Page Layout
- Paper size: A4
- Margins: 1 inch all sides (or follow your college template)
- Columns: 2-column format (standard for IEEE/conference papers)
- Font: Times New Roman 10pt (body), 12pt (section headings)
- Line spacing: Single

### Figures
- Every figure must have a caption below: `Figure 1: System Architecture`
- Every figure must be referenced in the text: "as shown in Figure 1..."
- Use clear, high-contrast diagrams
- Minimum resolution: 300 DPI for print

### Tables
- Every table must have a caption above: `Table 1: Throughput Comparison`
- Every table must be referenced in the text: "Table 2 shows..."
- Use borders, align numbers to the right
- Bold the header row

### Equations
- Number every equation: `(1)`, `(2)`
- Reference them in text: "as defined in Equation (1)..."
- Example: `Throughput = (Bytes Delivered / Time) × 8   ...(1)`

### Citations
- Use numbered IEEE style: [1], [2], [1]–[3]
- Cite in order of first appearance
- Every claim needs a citation unless it's your own result

### Section Numbering
- Use: 1, 1.1, 1.2, 2, 2.1 etc.
- Do NOT number Abstract or References

---

## Quick Checklist Before Submitting

- [ ] Title is specific and includes key innovation
- [ ] Abstract is 150–250 words, one paragraph, has numbers
- [ ] Keywords listed (5–7)
- [ ] Every section has subsections
- [ ] Every figure has a caption and is referenced in text
- [ ] Every table has a caption and is referenced in text
- [ ] Every claim is cited
- [ ] Results section has actual numbers, not just "good performance"
- [ ] Conclusion does not introduce new information
- [ ] Future work section present
- [ ] References in IEEE format
- [ ] Spell-checked (especially: literature, methodology, discussion, conclusion)
- [ ] Page limit respected (typically 6–8 pages for course papers)

---

## Word Count Target per Section

| Section | Target Words |
|---------|-------------|
| Abstract | 150–250 |
| Introduction | 400–600 |
| Literature Review | 500–800 |
| System Design | 600–800 |
| Methodology | 400–600 |
| Results & Discussion | 600–900 |
| Conclusion | 150–250 |
| Future Work | 150–200 |
| **Total (excl. references)** | **~3000–4400** |

---

*Follow this guide section by section. Fill in your actual data, results, and figures as you go.*
