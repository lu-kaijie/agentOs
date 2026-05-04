def test_package_imports():
    import agentos
    import agentos.cli
    import agentos.config
    import agentos.harness
    import agentos.runtime.app

    assert agentos.__version__ == "0.1.0"
