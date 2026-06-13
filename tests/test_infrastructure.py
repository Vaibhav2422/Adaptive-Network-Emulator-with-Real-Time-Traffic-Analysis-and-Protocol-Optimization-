"""
Basic tests for core infrastructure components.
"""
import pytest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import ConfigLoader, EmulatorConfig, ConfigValidator
from logging_config import LoggerManager, initialize_logging
from event_queue import EventQueue, EventType, SimulationClock


class TestConfigSystem:
    """Tests for configuration system."""
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        loader = ConfigLoader()
        config = loader.load("default")
        assert isinstance(config, EmulatorConfig)
        assert config.num_nodes == 3
        assert config.topology_type == "mesh"
    
    def test_config_validation_valid(self):
        """Test validation with valid config."""
        validator = ConfigValidator()
        config_dict = {
            "num_nodes": 3,
            "topology_type": "mesh"
        }
        is_valid, error = validator.validate(config_dict)
        assert is_valid
        assert error is None
    
    def test_config_validation_invalid_nodes(self):
        """Test validation with invalid num_nodes."""
        validator = ConfigValidator()
        config_dict = {
            "num_nodes": 1,  # Too few
            "topology_type": "mesh"
        }
        is_valid, error = validator.validate(config_dict)
        assert not is_valid
        assert "num_nodes" in error
    
    def test_config_validation_missing_field(self):
        """Test validation with missing required field."""
        validator = ConfigValidator()
        config_dict = {
            "topology_type": "mesh"
            # Missing num_nodes
        }
        is_valid, error = validator.validate(config_dict)
        assert not is_valid
        assert "num_nodes" in error


class TestLoggingSystem:
    """Tests for logging infrastructure."""
    
    def test_logger_manager_initialization(self):
        """Test logger manager initialization."""
        manager = LoggerManager(log_dir="logs", log_level="INFO", log_to_file=False)
        assert manager is not None
        assert manager.log_level == 20  # INFO level
    
    def test_get_system_logger(self):
        """Test getting system logger."""
        manager = LoggerManager(log_to_file=False)
        logger = manager.get_system_logger()
        assert logger is not None
        assert "system" in logger.name
    
    def test_get_layer_logger(self):
        """Test getting layer-specific logger."""
        manager = LoggerManager(log_to_file=False)
        logger = manager.get_layer_logger("physical")
        assert logger is not None
        assert "physical_layer" in logger.name
    
    def test_get_node_logger(self):
        """Test getting node-specific logger."""
        manager = LoggerManager(log_to_file=False)
        logger = manager.get_node_logger("node1")
        assert logger is not None
        assert "node.node1" in logger.name


class TestEventQueue:
    """Tests for event queue system."""
    
    def test_event_queue_initialization(self):
        """Test event queue initialization."""
        queue = EventQueue()
        assert queue is not None
        assert queue.is_empty()
    
    def test_schedule_event(self):
        """Test scheduling an event."""
        queue = EventQueue()
        
        def handler():
            pass
        
        event_id = queue.schedule(1.0, EventType.PACKET_ARRIVAL, handler)
        assert event_id == 0
        assert not queue.is_empty()
        assert queue.size() == 1
    
    def test_process_event(self):
        """Test processing an event."""
        queue = EventQueue()
        executed = []
        
        def handler():
            executed.append(True)
        
        queue.schedule(0.0, EventType.PACKET_ARRIVAL, handler)
        result = queue.process_next()
        
        assert result
        assert len(executed) == 1
        assert queue.is_empty()
    
    def test_event_ordering(self):
        """Test that events are processed in time order."""
        queue = EventQueue()
        order = []
        
        def handler1():
            order.append(1)
        
        def handler2():
            order.append(2)
        
        def handler3():
            order.append(3)
        
        # Schedule out of order
        queue.schedule(2.0, EventType.PACKET_ARRIVAL, handler2)
        queue.schedule(3.0, EventType.PACKET_ARRIVAL, handler3)
        queue.schedule(1.0, EventType.PACKET_ARRIVAL, handler1)
        
        # Process all
        while not queue.is_empty():
            queue.process_next()
        
        # Should be processed in time order
        assert order == [1, 2, 3]
    
    def test_simulation_clock(self):
        """Test simulation clock."""
        clock = SimulationClock(speed=1.0)
        assert clock.get_time() == 0.0
        
        clock.advance(1.5)
        assert clock.get_time() == 1.5
        
        clock.set_time(5.0)
        assert clock.get_time() == 5.0
    
    def test_cancel_event(self):
        """Test cancelling a scheduled event."""
        queue = EventQueue()
        
        def handler():
            pass
        
        event_id = queue.schedule(1.0, EventType.PACKET_ARRIVAL, handler)
        assert queue.size() == 1
        
        result = queue.cancel(event_id)
        assert result
        assert queue.is_empty()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
