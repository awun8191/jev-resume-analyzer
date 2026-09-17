def pytest_make_parametrize_id(config, val, argname):
    if isinstance(val, bytes):
        return f"{argname}-{len(val)}-bytes"
