"""
Configuration management system for the Adaptive Network Emulator.
Supports YAML-based configuration with schema validation and environment-specific configs.
"""
import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class EmulatorConfig:
    """Main configuration dataclass for the emulator."""
    # Network topology
    num_nodes: int = 3
    topology_type: str = "mesh"  # mesh, star, ring, custom
    
    # Routing
    routing_algorithm: str = "dijkstra"  # dijkstra, distance_vector
    
    # Transport layer
    transport_protocol: str = "gbn"  # gbn, sr
    window_size: int = 4
    timeout_ms: int = 100
    
    # Error simulation
    error_rate: float = 0.01
    loss_rate: float = 0.05
    
    # Features
    enable_optimization: bool = True
    capture_packets: bool = False
    
    # Simulation
    random_seed: Optional[int] = None
    simulation_speed: float = 1.0  # 1.0 = real-time, >1.0 = fast-forward
    
    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    
    # Dashboard
    dashboard_enabled: bool = False
    dashboard_port: int = 5000
    
    # Physical layer
    bit_rate_mbps: float = 100.0
    propagation_delay_ms: float = 10.0


class ConfigValidator:
    """Validates configuration parameters."""
    
    @staticmethod
    def validate(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate configuration dictionary.
        
        Returns:
            (is_valid, error_message)
        """
        # Required fields
        required_fields = ["num_nodes", "topology_type"]
        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"
        
        # Validate num_nodes
        if not isinstance(config["num_nodes"], int) or config["num_nodes"] < 2:
            return False, "num_nodes must be an integer >= 2"
        
        # Validate topology_type
        valid_topologies = ["mesh", "star", "ring", "custom"]
        if config["topology_type"] not in valid_topologies:
            return False, f"topology_type must be one of {valid_topologies}"
        
        # Validate routing_algorithm
        if "routing_algorithm" in config:
            valid_algorithms = ["dijkstra", "distance_vector"]
            if config["routing_algorithm"] not in valid_algorithms:
                return False, f"routing_algorithm must be one of {valid_algorithms}"
        
        # Validate transport_protocol
        if "transport_protocol" in config:
            valid_protocols = ["gbn", "sr"]
            if config["transport_protocol"] not in valid_protocols:
                return False, f"transport_protocol must be one of {valid_protocols}"
        
        # Validate window_size
        if "window_size" in config:
            if not isinstance(config["window_size"], int) or config["window_size"] < 1:
                return False, "window_size must be an integer >= 1"
        
        # Validate timeout_ms
        if "timeout_ms" in config:
            if not isinstance(config["timeout_ms"], (int, float)) or config["timeout_ms"] <= 0:
                return False, "timeout_ms must be a positive number"
        
        # Validate error_rate
        if "error_rate" in config:
            if not isinstance(config["error_rate"], (int, float)) or not (0 <= config["error_rate"] <= 1):
                return False, "error_rate must be between 0 and 1"
        
        # Validate loss_rate
        if "loss_rate" in config:
            if not isinstance(config["loss_rate"], (int, float)) or not (0 <= config["loss_rate"] <= 1):
                return False, "loss_rate must be between 0 and 1"
        
        # Validate log_level
        if "log_level" in config:
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
            if config["log_level"] not in valid_levels:
                return False, f"log_level must be one of {valid_levels}"
        
        return True, None


class ConfigLoader:
    """Loads and manages configuration from YAML files."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.validator = ConfigValidator()
    
    def load(self, environment: str = "default") -> EmulatorConfig:
        """
        Load configuration for the specified environment.
        
        Args:
            environment: Environment name (default, dev, test, prod)
        
        Returns:
            EmulatorConfig instance
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config validation fails
        """
        config_file = os.path.join(self.config_dir, f"{environment}.yaml")
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_file, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Validate configuration
        is_valid, error_msg = self.validator.validate(config_dict)
        if not is_valid:
            raise ValueError(f"Configuration validation failed: {error_msg}")
        
        # Create EmulatorConfig instance
        return EmulatorConfig(**config_dict)
    
    def load_from_dict(self, config_dict: Dict[str, Any]) -> EmulatorConfig:
        """
        Load configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
        
        Returns:
            EmulatorConfig instance
        
        Raises:
            ValueError: If config validation fails
        """
        # Validate configuration
        is_valid, error_msg = self.validator.validate(config_dict)
        if not is_valid:
            raise ValueError(f"Configuration validation failed: {error_msg}")
        
        return EmulatorConfig(**config_dict)
    
    def save(self, config: EmulatorConfig, environment: str = "default") -> None:
        """
        Save configuration to a YAML file.
        
        Args:
            config: EmulatorConfig instance
            environment: Environment name
        """
        config_file = os.path.join(self.config_dir, f"{environment}.yaml")
        
        # Convert dataclass to dict
        config_dict = {
            "num_nodes": config.num_nodes,
            "topology_type": config.topology_type,
            "routing_algorithm": config.routing_algorithm,
            "transport_protocol": config.transport_protocol,
            "window_size": config.window_size,
            "timeout_ms": config.timeout_ms,
            "error_rate": config.error_rate,
            "loss_rate": config.loss_rate,
            "enable_optimization": config.enable_optimization,
            "capture_packets": config.capture_packets,
            "random_seed": config.random_seed,
            "simulation_speed": config.simulation_speed,
            "log_level": config.log_level,
            "log_to_file": config.log_to_file,
            "dashboard_enabled": config.dashboard_enabled,
            "dashboard_port": config.dashboard_port,
            "bit_rate_mbps": config.bit_rate_mbps,
            "propagation_delay_ms": config.propagation_delay_ms,
        }
        
        os.makedirs(self.config_dir, exist_ok=True)
        
        with open(config_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
