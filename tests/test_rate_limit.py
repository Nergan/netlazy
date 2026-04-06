import pytest

@pytest.mark.skip(reason="Rate limit is disabled in test environment (RATE_LIMIT_PER_MINUTE=1000)")
def test_rate_limit():
    pass