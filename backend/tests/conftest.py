import os

# The suite drives the real middleware. Disable the limit by default so test
# volume never depends on the per-IP policy; the rate limit tests opt back in.
os.environ["RATE_LIMIT_ENABLED"] = "false"


def pytest_make_parametrize_id(config, val, argname):
    if isinstance(val, bytes):
        return f"{argname}-{len(val)}-bytes"
