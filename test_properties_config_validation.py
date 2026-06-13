"""
Property-based tests for Configuration and Validation (Task 25).

Properties tested:
  - Property 38: Configuration validation on startup   (Requirements 11.5, 11.7)

100 examples per property sub-test, implemented with random sampling
(mirrors Hypothesis style used elsewhere in the suite).
"""

from __future__ import annotations

import copy
import random
from typing import Any, Dict, List

import pytest

from src.config_loader import ConfigLoader, ConfigValidationError, ConfigError


# ─────────────────────────────────────────────────────────────
# Minimal valid config (baseline for mutation testing)
# ─────────────────────────────────────────────────────────────

def _valid_config() -> Dict[str, Any]:
    return {
        "topology": {
            "nodes": [
                {"node_id": "n1", "node_type": "sender"},
                {"node_id": "n2", "node_type": "receiver"},
            ],
            "links": [
                {
                    "source": "n1",
                    "target": "n2",
                    "bandwidth_mbps": 100.0,
                    "delay_ms": 10.0,
                    "loss_pct": 0.0,
                }
            ],
        },
        "protocol": {
            "protocol": "GBN",
            "window_size": 8,
            "timeout_ms": 200.0,
            "max_retransmissions": 5,
            "ack_mode": "cumulative",
        },
        "experiment": {
            "name": "baseline",
            "duration_s": 60.0,
            "packet_size_bytes": 1024,
            "traffic_pattern": "cbr",
            "repetitions": 3,
        },
    }


# ─────────────────────────────────────────────────────────────
# Helper: assert validation catches at least one error on a bad config
# ─────────────────────────────────────────────────────────────

def _assert_invalid(cfg: Dict[str, Any], context: str = "") -> List[ConfigError]:
    errors = ConfigLoader.validate(cfg)
    assert errors, (
        f"Expected validation errors but got none. Context: {context}\n"
        f"Config: {cfg}"
    )
    # Every error must have a non-empty field and message
    for err in errors:
        assert err.field,   f"Error field must be non-empty. Context: {context}"
        assert err.message, f"Error message must be non-empty. Context: {context}"
    return errors


def _assert_valid(cfg: Dict[str, Any], context: str = "") -> None:
    errors = ConfigLoader.validate(cfg)
    assert not errors, (
        f"Expected no errors but got:\n"
        + "\n".join(f"  - {e}" for e in errors)
        + f"\nContext: {context}"
    )


# ─────────────────────────────────────────────────────────────
# Property 38 – baseline: valid config passes
# ─────────────────────────────────────────────────────────────

class TestProperty38ValidConfig:
    """A well-formed config must always pass validation."""

    def test_baseline_valid(self):
        _assert_valid(_valid_config(), "baseline")

    @pytest.mark.parametrize("protocol", ["GBN", "SR", "ADAPTIVE"])
    def test_valid_protocols(self, protocol):
        cfg = _valid_config()
        cfg["protocol"]["protocol"] = protocol
        if protocol == "SR":
            cfg["protocol"]["ack_mode"] = "selective"
        if protocol == "ADAPTIVE":
            cfg["protocol"]["adaptive_alpha"] = 0.1
            cfg["protocol"]["ack_mode"] = "cumulative"
        _assert_valid(cfg, f"protocol={protocol}")

    @pytest.mark.parametrize("pattern", ["cbr", "bursty", "trace"])
    def test_valid_traffic_patterns(self, pattern):
        cfg = _valid_config()
        cfg["experiment"]["traffic_pattern"] = pattern
        _assert_valid(cfg, f"traffic_pattern={pattern}")

    @pytest.mark.parametrize("node_type", ["sender", "receiver", "router"])
    def test_valid_node_types(self, node_type):
        cfg = _valid_config()
        cfg["topology"]["nodes"][0]["node_type"] = node_type
        _assert_valid(cfg, f"node_type={node_type}")

    def test_100_random_valid_configs(self):
        """Property 38 (boundary sweep): 100 random valid configs must pass."""
        rng = random.Random(42)
        protocols_with_ack = {
            "GBN":      ("cumulative", None),
            "SR":       ("selective",  None),
            "ADAPTIVE": ("cumulative", 0.125),
        }
        patterns = ["cbr", "bursty", "trace"]
        node_types = ["sender", "receiver", "router"]

        for i in range(100):
            proto_name, (ack_mode, alpha) = rng.choice(list(protocols_with_ack.items()))
            cfg = {
                "topology": {
                    "nodes": [
                        {"node_id": f"node_{j}", "node_type": rng.choice(node_types)}
                        for j in range(rng.randint(1, 5))
                    ],
                    "links": [
                        {
                            "source": "node_0",
                            "target": "node_1" if rng.randint(1, 5) > 1 else "node_0",
                            "bandwidth_mbps": rng.uniform(0.1, 1000.0),
                            "delay_ms": rng.uniform(0.0, 500.0),
                            "loss_pct": rng.uniform(0.0, 100.0),
                        }
                    ] if rng.randint(1, 5) > 1 else [],
                },
                "protocol": {
                    "protocol": proto_name,
                    "window_size": rng.randint(1, 1024),
                    "timeout_ms": rng.uniform(0.001, 10000.0),
                    "max_retransmissions": rng.randint(0, 50),
                    "ack_mode": ack_mode,
                    **({"adaptive_alpha": alpha} if alpha is not None else {}),
                },
                "experiment": {
                    "name": f"exp_{i}",
                    "duration_s": rng.uniform(0.001, 3600.0),
                    "packet_size_bytes": rng.randint(64, 65535),
                    "traffic_pattern": rng.choice(patterns),
                    "repetitions": rng.randint(1, 20),
                },
            }
            _assert_valid(cfg, f"random valid #{i}")


# ─────────────────────────────────────────────────────────────
# Property 38 – missing required sections
# ─────────────────────────────────────────────────────────────

class TestProperty38MissingRequiredFields:
    """Any config missing a required top-level section must be rejected."""

    @pytest.mark.parametrize("missing_section", ["topology", "protocol", "experiment"])
    def test_missing_top_level_section(self, missing_section):
        cfg = _valid_config()
        del cfg[missing_section]
        errors = _assert_invalid(cfg, f"missing {missing_section}")
        fields = [e.field for e in errors]
        assert any(missing_section in f for f in fields), (
            f"Expected error mentioning '{missing_section}', got: {fields}"
        )

    @pytest.mark.parametrize("missing_field,section", [
        ("window_size",        "protocol"),
        ("timeout_ms",         "protocol"),
        ("max_retransmissions","protocol"),
        ("duration_s",         "experiment"),
        ("packet_size_bytes",  "experiment"),
        ("traffic_pattern",    "experiment"),
    ])
    def test_missing_required_protocol_and_experiment_fields(self, missing_field, section):
        cfg = _valid_config()
        del cfg[section][missing_field]
        errors = _assert_invalid(cfg, f"missing {section}.{missing_field}")
        fields = [e.field for e in errors]
        assert any(missing_field in f for f in fields), (
            f"Expected error mentioning '{missing_field}', got: {fields}"
        )

    def test_100_random_missing_required_fields(self):
        """Property 38: For any randomly removed required field, validation must fail."""
        required_paths = [
            ("topology",),
            ("protocol",),
            ("experiment",),
            ("protocol",   "protocol"),
            ("protocol",   "window_size"),
            ("protocol",   "timeout_ms"),
            ("protocol",   "max_retransmissions"),
            ("experiment", "name"),
            ("experiment", "duration_s"),
            ("experiment", "packet_size_bytes"),
            ("experiment", "traffic_pattern"),
        ]
        rng = random.Random(7)
        for i in range(100):
            path = rng.choice(required_paths)
            cfg  = _valid_config()
            # Navigate to parent and delete key
            target = cfg
            for key in path[:-1]:
                target = target[key]
            del target[path[-1]]
            _assert_invalid(cfg, f"iteration {i}: removed {'.'.join(path)}")


# ─────────────────────────────────────────────────────────────
# Property 38 – out-of-range values
# ─────────────────────────────────────────────────────────────

class TestProperty38OutOfRangeValues:
    """Any config with an out-of-range value must be rejected."""

    # -- window_size --

    @pytest.mark.parametrize("bad_window", [0, -1, -100, 1025, 9999])
    def test_bad_window_size(self, bad_window):
        cfg = _valid_config()
        cfg["protocol"]["window_size"] = bad_window
        errors = _assert_invalid(cfg, f"window_size={bad_window}")
        assert any("window_size" in e.field for e in errors)

    # -- timeout_ms --

    @pytest.mark.parametrize("bad_timeout", [0, -1, -0.001])
    def test_bad_timeout_ms(self, bad_timeout):
        cfg = _valid_config()
        cfg["protocol"]["timeout_ms"] = bad_timeout
        errors = _assert_invalid(cfg, f"timeout_ms={bad_timeout}")
        assert any("timeout_ms" in e.field for e in errors)

    # -- loss_pct --

    @pytest.mark.parametrize("bad_loss", [-0.001, -50.0, 100.001, 200.0])
    def test_bad_loss_pct(self, bad_loss):
        cfg = _valid_config()
        cfg["topology"]["links"][0]["loss_pct"] = bad_loss
        errors = _assert_invalid(cfg, f"loss_pct={bad_loss}")
        assert any("loss_pct" in e.field for e in errors)

    # -- delay_ms --

    @pytest.mark.parametrize("bad_delay", [-1.0, -0.001])
    def test_negative_delay(self, bad_delay):
        cfg = _valid_config()
        cfg["topology"]["links"][0]["delay_ms"] = bad_delay
        errors = _assert_invalid(cfg, f"delay_ms={bad_delay}")
        assert any("delay_ms" in e.field for e in errors)

    # -- bandwidth_mbps --

    @pytest.mark.parametrize("bad_bw", [0, -1.0, -100.0])
    def test_bad_bandwidth(self, bad_bw):
        cfg = _valid_config()
        cfg["topology"]["links"][0]["bandwidth_mbps"] = bad_bw
        errors = _assert_invalid(cfg, f"bandwidth_mbps={bad_bw}")
        assert any("bandwidth_mbps" in e.field for e in errors)

    # -- packet_size_bytes --

    @pytest.mark.parametrize("bad_psize", [0, 63, -1, 65536, 100000])
    def test_bad_packet_size(self, bad_psize):
        cfg = _valid_config()
        cfg["experiment"]["packet_size_bytes"] = bad_psize
        errors = _assert_invalid(cfg, f"packet_size_bytes={bad_psize}")
        assert any("packet_size_bytes" in e.field for e in errors)

    # -- duration_s --

    @pytest.mark.parametrize("bad_dur", [0, -1.0, -0.001])
    def test_bad_duration(self, bad_dur):
        cfg = _valid_config()
        cfg["experiment"]["duration_s"] = bad_dur
        errors = _assert_invalid(cfg, f"duration_s={bad_dur}")
        assert any("duration_s" in e.field for e in errors)

    # -- repetitions --

    @pytest.mark.parametrize("bad_reps", [0, -1, -10])
    def test_bad_repetitions(self, bad_reps):
        cfg = _valid_config()
        cfg["experiment"]["repetitions"] = bad_reps
        errors = _assert_invalid(cfg, f"repetitions={bad_reps}")
        assert any("repetitions" in e.field for e in errors)

    def test_100_random_out_of_range(self):
        """
        Property 38 (random sweep): Inject random out-of-range values into
        valid configs and confirm each one is rejected.
        """
        rng = random.Random(99)

        def bad_value(rng, field):
            if field in ("window_size",):
                return rng.choice([0, -rng.randint(1, 500), 1025 + rng.randint(0, 500)])
            if field in ("timeout_ms", "duration_s", "bandwidth_mbps"):
                return rng.choice([0, -rng.uniform(0.001, 100)])
            if field in ("delay_ms",):
                return -rng.uniform(0.001, 100)
            if field in ("loss_pct",):
                return rng.choice([-rng.uniform(0.001, 50), 100.001 + rng.uniform(0, 100)])
            if field in ("packet_size_bytes",):
                return rng.choice([rng.randint(-100, 63), rng.randint(65536, 100000)])
            if field in ("repetitions",):
                return rng.choice([0, -rng.randint(1, 10)])
            if field in ("max_retransmissions",):
                return -rng.randint(1, 10)
            return None

        mutations = [
            ("protocol",   "window_size"),
            ("protocol",   "timeout_ms"),
            ("protocol",   "max_retransmissions"),
            ("experiment", "duration_s"),
            ("experiment", "packet_size_bytes"),
            ("experiment", "repetitions"),
            ("topology_link", "bandwidth_mbps"),
            ("topology_link", "delay_ms"),
            ("topology_link", "loss_pct"),
        ]

        for i in range(100):
            section, field = rng.choice(mutations)
            cfg = _valid_config()
            bv  = bad_value(rng, field)
            if bv is None:
                continue
            if section == "topology_link":
                cfg["topology"]["links"][0][field] = bv
            else:
                cfg[section][field] = bv
            _assert_invalid(cfg, f"iteration {i}: {section}.{field}={bv}")


# ─────────────────────────────────────────────────────────────
# Property 38 – invalid enum / string values
# ─────────────────────────────────────────────────────────────

class TestProperty38InvalidEnumValues:

    @pytest.mark.parametrize("bad_protocol", ["", "tcp", "gbn", "sr", "UDP", "none", None])
    def test_invalid_protocol_name(self, bad_protocol):
        cfg = _valid_config()
        cfg["protocol"]["protocol"] = bad_protocol
        errors = _assert_invalid(cfg, f"protocol={bad_protocol}")
        assert any("protocol" in e.field for e in errors)

    @pytest.mark.parametrize("bad_ack", ["", "all", "none", "CUMULATIVE", None])
    def test_invalid_ack_mode(self, bad_ack):
        cfg = _valid_config()
        cfg["protocol"]["ack_mode"] = bad_ack
        errors = _assert_invalid(cfg, f"ack_mode={bad_ack}")
        assert any("ack_mode" in e.field for e in errors)

    @pytest.mark.parametrize("bad_pattern", ["", "random", "CBR", "BURST", None])
    def test_invalid_traffic_pattern(self, bad_pattern):
        cfg = _valid_config()
        cfg["experiment"]["traffic_pattern"] = bad_pattern
        errors = _assert_invalid(cfg, f"traffic_pattern={bad_pattern}")
        assert any("traffic_pattern" in e.field for e in errors)

    @pytest.mark.parametrize("bad_ntype", ["", "switch", "SENDER", "host", None])
    def test_invalid_node_type(self, bad_ntype):
        cfg = _valid_config()
        cfg["topology"]["nodes"][0]["node_type"] = bad_ntype
        errors = _assert_invalid(cfg, f"node_type={bad_ntype}")
        assert any("node_type" in e.field for e in errors)

    def test_empty_experiment_name(self):
        for bad_name in ("", "   ", None):
            cfg = _valid_config()
            cfg["experiment"]["name"] = bad_name
            errors = _assert_invalid(cfg, f"name={bad_name!r}")
            assert any("name" in e.field for e in errors)


# ─────────────────────────────────────────────────────────────
# Property 38 – conflicting settings
# ─────────────────────────────────────────────────────────────

class TestProperty38ConflictingSettings:

    def test_sr_requires_selective_ack(self):
        """SR protocol must use selective acknowledgement."""
        cfg = _valid_config()
        cfg["protocol"]["protocol"] = "SR"
        cfg["protocol"]["ack_mode"] = "cumulative"   # conflict
        errors = _assert_invalid(cfg, "SR with cumulative ack")
        fields = [e.field for e in errors]
        assert any("ack_mode" in f for f in fields), (
            f"Expected ack_mode conflict error, got: {fields}"
        )

    def test_adaptive_requires_alpha(self):
        """ADAPTIVE protocol must provide adaptive_alpha."""
        cfg = _valid_config()
        cfg["protocol"]["protocol"]     = "ADAPTIVE"
        cfg["protocol"]["ack_mode"]     = "cumulative"
        # adaptive_alpha deliberately absent
        errors = _assert_invalid(cfg, "ADAPTIVE without alpha")
        fields = [e.field for e in errors]
        assert any("adaptive_alpha" in f for f in fields), (
            f"Expected adaptive_alpha error, got: {fields}"
        )

    def test_adaptive_alpha_out_of_range(self):
        """ADAPTIVE alpha must be strictly between 0 and 1."""
        for bad_alpha in (0.0, 1.0, -0.1, 1.5):
            cfg = _valid_config()
            cfg["protocol"]["protocol"]      = "ADAPTIVE"
            cfg["protocol"]["ack_mode"]      = "cumulative"
            cfg["protocol"]["adaptive_alpha"] = bad_alpha
            errors = _assert_invalid(cfg, f"adaptive_alpha={bad_alpha}")
            assert any("adaptive_alpha" in e.field for e in errors)

    def test_100_random_conflicting_injections(self):
        """Property 38 (conflicts): random conflict injections must all be caught."""
        rng = random.Random(17)
        conflict_factories = [
            # SR + cumulative
            lambda cfg: cfg["protocol"].update({"protocol": "SR", "ack_mode": "cumulative"}),
            # ADAPTIVE without alpha
            lambda cfg: (
                cfg["protocol"].update({"protocol": "ADAPTIVE", "ack_mode": "cumulative"}),
                cfg["protocol"].pop("adaptive_alpha", None),
            ),
            # ADAPTIVE with bad alpha = 0
            lambda cfg: cfg["protocol"].update(
                {"protocol": "ADAPTIVE", "ack_mode": "cumulative", "adaptive_alpha": 0.0}
            ),
            # ADAPTIVE with bad alpha = 1
            lambda cfg: cfg["protocol"].update(
                {"protocol": "ADAPTIVE", "ack_mode": "cumulative", "adaptive_alpha": 1.0}
            ),
        ]
        for i in range(100):
            factory = rng.choice(conflict_factories)
            cfg = _valid_config()
            factory(cfg)
            _assert_invalid(cfg, f"conflict iteration {i}")


# ─────────────────────────────────────────────────────────────
# Property 38 – topology-specific checks
# ─────────────────────────────────────────────────────────────

class TestProperty38TopologyChecks:

    def test_empty_nodes_rejected(self):
        cfg = _valid_config()
        cfg["topology"]["nodes"] = []
        _assert_invalid(cfg, "empty nodes list")

    def test_duplicate_node_ids_rejected(self):
        cfg = _valid_config()
        cfg["topology"]["nodes"] = [
            {"node_id": "dup", "node_type": "sender"},
            {"node_id": "dup", "node_type": "receiver"},
        ]
        errors = _assert_invalid(cfg, "duplicate node_id")
        assert any("node_id" in e.field for e in errors)

    def test_empty_node_id_rejected(self):
        for bad_id in ("", "   ", None):
            cfg = _valid_config()
            cfg["topology"]["nodes"][0]["node_id"] = bad_id
            errors = _assert_invalid(cfg, f"node_id={bad_id!r}")
            assert any("node_id" in e.field for e in errors)

    def test_100_random_topology_mutations(self):
        """Property 38 (topology): random topology mutations must be caught."""
        rng = random.Random(55)

        def apply_bad_topology(cfg, rng):
            choice = rng.randint(0, 4)
            if choice == 0:
                # Empty nodes
                cfg["topology"]["nodes"] = []
            elif choice == 1:
                # Duplicate ids
                cfg["topology"]["nodes"] = [
                    {"node_id": "same", "node_type": "sender"},
                    {"node_id": "same", "node_type": "receiver"},
                ]
            elif choice == 2:
                # Bad node type
                cfg["topology"]["nodes"][0]["node_type"] = "invalid_type"
            elif choice == 3:
                # Negative bandwidth on a link
                if cfg["topology"]["links"]:
                    cfg["topology"]["links"][0]["bandwidth_mbps"] = -1.0
                else:
                    cfg["topology"]["nodes"] = []  # fallback
            else:
                # Bad loss_pct
                if cfg["topology"]["links"]:
                    cfg["topology"]["links"][0]["loss_pct"] = rng.choice([-1.0, 101.0, 200.0])
                else:
                    cfg["topology"]["nodes"][0]["node_type"] = "bad"

        for i in range(100):
            cfg = _valid_config()
            apply_bad_topology(cfg, rng)
            _assert_invalid(cfg, f"topology mutation #{i}")


# ─────────────────────────────────────────────────────────────
# Property 38 – error message quality (Requirement 11.7)
# ─────────────────────────────────────────────────────────────

class TestProperty38ErrorMessageQuality:
    """Every error message must be actionable: name the field and describe the issue."""

    def test_error_messages_mention_field_name(self):
        """Each ConfigError.field must be non-empty and dot-separated path."""
        bad_configs = [
            (_valid_config(), "window_size",   "protocol",   0),
            (_valid_config(), "loss_pct",       None,         -5.0),
            (_valid_config(), "traffic_pattern",None,         "unknown"),
        ]
        for base, field, section, bad_val in bad_configs:
            cfg = copy.deepcopy(base)
            if section:
                cfg[section][field] = bad_val
            else:
                # find it anywhere
                for sec in ("protocol", "experiment"):
                    if field in cfg[sec]:
                        cfg[sec][field] = bad_val
                        break
                else:
                    cfg["topology"]["links"][0][field] = bad_val

            errors = ConfigLoader.validate(cfg)
            assert errors, f"Expected errors for {field}={bad_val}"
            for err in errors:
                assert err.field,   "field must be non-empty"
                assert err.message, "message must be non-empty"
                assert len(err.message) >= 5, "message must be descriptive"

    def test_exception_message_lists_all_errors(self):
        """ConfigValidationError message must contain info about every error found."""
        cfg = _valid_config()
        cfg["protocol"]["window_size"]      = 0
        cfg["protocol"]["timeout_ms"]       = -1
        cfg["experiment"]["packet_size_bytes"] = 0

        try:
            ConfigLoader.from_dict(cfg)
            pytest.fail("Should have raised ConfigValidationError")
        except ConfigValidationError as exc:
            assert len(exc.errors) >= 3, (
                f"Expected >=3 errors, got {len(exc.errors)}: {exc.errors}"
            )
            msg = str(exc)
            assert "window_size" in msg
            assert "timeout_ms"  in msg
            assert "packet_size_bytes" in msg

    def test_from_dict_raises_on_invalid(self):
        """from_dict must raise ConfigValidationError, not return None."""
        cfg = _valid_config()
        cfg["protocol"]["protocol"] = "INVALID"
        with pytest.raises(ConfigValidationError):
            ConfigLoader.from_dict(cfg)

    def test_validate_returns_list_not_raises(self):
        """validate() must return errors without raising."""
        cfg = _valid_config()
        del cfg["topology"]
        result = ConfigLoader.validate(cfg)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_100_random_error_message_quality(self):
        """
        Property 38 (message quality): for any invalid config, every returned
        ConfigError must have a non-empty field and a descriptive message.
        """
        rng = random.Random(3)
        all_bad = [
            lambda c: c["protocol"].update({"window_size": 0}),
            lambda c: c["protocol"].update({"timeout_ms": 0}),
            lambda c: c["protocol"].update({"protocol": "bad"}),
            lambda c: c["experiment"].update({"traffic_pattern": "wrong"}),
            lambda c: c["experiment"].update({"duration_s": -1}),
            lambda c: c["experiment"].update({"packet_size_bytes": 10}),
            lambda c: c["topology"].update({"nodes": []}),
            lambda c: c["topology"]["links"][0].update({"bandwidth_mbps": -1}),
            lambda c: c["topology"]["links"][0].update({"loss_pct": 999}),
            lambda c: (c["protocol"].update({"protocol": "SR", "ack_mode": "cumulative"})),
        ]

        for i in range(100):
            cfg   = _valid_config()
            mutator = rng.choice(all_bad)
            mutator(cfg)
            errors = ConfigLoader.validate(cfg)
            assert errors, f"Iteration {i}: expected errors"
            for err in errors:
                assert isinstance(err, ConfigError), \
                    f"Iteration {i}: must return ConfigError instances"
                assert err.field,   f"Iteration {i}: field must be non-empty"
                assert err.message, f"Iteration {i}: message must be non-empty"
                assert len(err.message) >= 5, \
                    f"Iteration {i}: message too short: {err.message!r}"


# ─────────────────────────────────────────────────────────────
# Property 38 – round-trip: valid config survives load→validate→build
# ─────────────────────────────────────────────────────────────

class TestProperty38RoundTrip:

    def test_from_dict_returns_emulator_config(self):
        cfg    = _valid_config()
        result = ConfigLoader.from_dict(cfg)
        assert result.topology  is not None
        assert result.protocol  is not None
        assert result.experiment is not None

    def test_fields_preserved_after_load(self):
        cfg    = _valid_config()
        result = ConfigLoader.from_dict(cfg)
        assert result.protocol.window_size      == 8
        assert result.protocol.timeout_ms       == 200.0
        assert result.experiment.name           == "baseline"
        assert result.experiment.duration_s     == 60.0
        assert result.experiment.packet_size_bytes == 1024

    def test_100_random_valid_round_trips(self):
        """Property 38 (round-trip): from_dict must never raise for valid configs."""
        rng = random.Random(66)
        protocols_ack = {
            "GBN":      ("cumulative", None),
            "SR":       ("selective",  None),
            "ADAPTIVE": ("cumulative", 0.05),
        }
        for i in range(100):
            pname, (ack, alpha) = rng.choice(list(protocols_ack.items()))
            cfg = {
                "topology": {
                    "nodes": [{"node_id": f"n{j}", "node_type": "sender"}
                              for j in range(rng.randint(1, 4))],
                    "links": [],
                },
                "protocol": {
                    "protocol": pname,
                    "window_size": rng.randint(1, 1024),
                    "timeout_ms": rng.uniform(1.0, 5000.0),
                    "max_retransmissions": rng.randint(0, 20),
                    "ack_mode": ack,
                    **({"adaptive_alpha": alpha} if alpha else {}),
                },
                "experiment": {
                    "name": f"run_{i}",
                    "duration_s": rng.uniform(1.0, 100.0),
                    "packet_size_bytes": rng.randint(64, 65535),
                    "traffic_pattern": rng.choice(["cbr", "bursty", "trace"]),
                    "repetitions": rng.randint(1, 10),
                },
            }
            try:
                result = ConfigLoader.from_dict(cfg)
                assert result is not None
            except ConfigValidationError as exc:
                pytest.fail(f"Round-trip #{i} raised unexpectedly: {exc}")
