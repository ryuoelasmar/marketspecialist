from shared.data.news import _classify


def test_classify_politics():
    assert _classify("Fed rate decision holds steady at 5.25%") == "politics"
    assert _classify("MAS announces new crypto regulation") == "politics"


def test_classify_sector():
    assert _classify("TSMC earnings beat on AI chip demand") == "sector"
    assert _classify("Semiconductor sector rallies") == "sector"


def test_classify_market():
    assert _classify("Stocks rally after CPI print") == "market"


def test_classify_general():
    # Sports/lifestyle content with no market keywords
    assert _classify("Singapore opens new art museum exhibit") == "general"
