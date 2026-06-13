"""
Pytest configuration and shared fixtures for the Adaptive Network Emulator test suite.
"""
import pytest
from hypothesis import settings, Verbosity

# Configure hypothesis profiles
settings.register_profile("default", max_examples=100, deadline=None)
settings.register_profile("ci", max_examples=200, deadline=None)
settings.register_profile("dev", max_examples=10, deadline=None, verbosity=Verbosity.verbose)

# Load the default profile
settings.load_profile("default")


@pytest.fixture
def sample_config():
    """Provides a sample configuration for testing."""
    return {
        "num_nodes": 3,
        "topology_type": "mesh",
        "routing_algorithm": "dijkstra",
        "transport_protocol": "gbn",
        "window_size": 4,
        "timeout_ms": 100,
        "error_rate": 0.01,
        "loss_rate": 0.05,
        "enable_optimization": True,
        "capture_packets": False
    }
