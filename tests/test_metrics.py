from faultlab.metrics import Window, percentile


def test_percentile_interpolates_raw_observations():
    assert percentile([10, 20, 30, 40, 50], .95) == 48
    assert percentile([], .95) == 0


def test_empty_window_and_http_error_semantics():
    assert Window().summary(1)["error_rate"] == 0
    window = Window()
    window.record(10, 200)
    window.record(20, 429)
    window.record(30, error="timeout")
    result = window.summary(1)
    assert result["successes"] == 1
    assert result["failures"] == 2
    assert result["timeouts"] == 1
    assert result["p95_ms"] == 29
