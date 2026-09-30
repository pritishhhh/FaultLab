from faultlab.scoring import score


def test_score_zero_baseline_errors_and_recovery():
    baseline = {"requests": 100, "p95_ms": 80, "error_rate": 0, "timeout_rate": 0, "rps": 10}
    fault = {"requests": 100, "p95_ms": 640, "error_rate": .1, "timeout_rate": .1, "rps": 8}
    recovery = {"requests": 100, "p95_ms": 90, "error_rate": 0, "rps": 10}
    result = score(baseline, fault, recovery)
    assert result["latency_amplification"] == 8
    assert result["error_amplification"] is None
    assert result["recovered"]
    assert "LATENCY_DEGRADATION" in result["classifications"]


def test_empty_recovery_is_failure():
    empty = {"requests": 0, "p95_ms": 0, "error_rate": 0, "rps": 0}
    assert score(empty, empty, empty)["recovered"] is False
