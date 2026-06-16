def test_smoke():
    assert True


def test_new_live_modules_import():
    import oraculo.live.client  # noqa: F401
    import oraculo.live.fixtures  # noqa: F401
    import oraculo.live.names  # noqa: F401
    import oraculo.live.schedule  # noqa: F401
    import oraculo.report.match_report  # noqa: F401
    import oraculo.verify.predictor  # noqa: F401
    import oraculo.verify.scoring  # noqa: F401
    import oraculo.verify.log  # noqa: F401
    import app.charts  # noqa: F401
    import app.live_view  # noqa: F401
