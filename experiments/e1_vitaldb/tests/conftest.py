def pytest_configure(config):
    config.addinivalue_line("markers", "slow: calibration test that takes about a minute")
