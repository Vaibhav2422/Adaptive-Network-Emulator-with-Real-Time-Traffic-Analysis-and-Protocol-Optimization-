# Adaptive Network Emulator

A software-based network simulation system demonstrating end-to-end communication across multiple layers of the TCP/IP and OSI models with real-time traffic analysis and adaptive optimization.

## Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
.
├── src/           # Source code
├── tests/         # Test files
├── config/        # Configuration files
├── logs/          # Log files
├── docs/          # Documentation
└── .kiro/specs/   # Specification documents
```

## Running Tests

```bash
pytest
```

## Documentation

See the `docs/` directory and `.kiro/specs/adaptive-network-emulator/` for detailed documentation.
