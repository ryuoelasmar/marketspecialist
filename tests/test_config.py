from shared.config import (
    all_rss_feeds,
    all_tracked_symbols,
    classification_keywords,
    load_regions,
    region,
    region_codes,
)


def test_regions_parse():
    regions = load_regions()
    assert "regions" in regions
    assert set(region_codes()) >= {"US", "APAC", "ASEAN", "GLOBAL"}


def test_region_has_indices():
    for code in ["US", "APAC", "ASEAN"]:
        r = region(code)
        assert r["indices"], f"{code} must have indices"
        for idx in r["indices"]:
            assert "symbol" in idx and "name" in idx


def test_tracked_symbols_nonempty():
    symbols = all_tracked_symbols()
    assert len(symbols) > 20
    # Spot check
    all_syms = {s[0] for s in symbols}
    assert "^GSPC" in all_syms
    assert "^STI" in all_syms


def test_rss_feeds_are_urls():
    feeds = all_rss_feeds()
    assert feeds
    for url, code in feeds:
        assert url.startswith("http"), url


def test_classification_keywords_present():
    kws = classification_keywords()
    assert "politics_and_regulation" in kws
    assert "sector_trends" in kws
    assert kws["politics_and_regulation"]
