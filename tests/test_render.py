from digest.render import render_html, render_text


CANNED_DIGEST = {
    "date": "2026-04-21",
    "headline": "ASEAN banks rally on softer inflation prints while US tech cools.",
    "top_movers": [
        {
            "name": "Nikkei 225",
            "region": "APAC",
            "change_1d_pct": 1.42,
            "change_5d_pct": 3.10,
            "why": "Weak yen and robust Q1 earnings from SoftBank lifted the index.",
            "sources": ["https://asia.nikkei.com/fake-article"],
        },
        {
            "name": "Straits Times Index",
            "region": "ASEAN",
            "change_1d_pct": 0.85,
            "change_5d_pct": 2.40,
            "why": "DBS and OCBC led after MAS kept policy unchanged.",
            "sources": ["https://www.businesstimes.com.sg/fake-article"],
        },
        {
            "name": "XLK",
            "region": "US",
            "change_1d_pct": -1.10,
            "change_5d_pct": -2.35,
            "why": "Semis dragged on softer guidance from a major supplier.",
            "sources": ["https://example.com/news"],
        },
    ],
    "regional_politics": [
        {
            "region": "ASEAN",
            "headline": "Indonesia's BI holds rate at 6.00% citing rupiah stability.",
            "impact": "Supportive of IDX banks; rate-sensitives outperform.",
            "sources": ["https://jakartaglobe.id/fake"],
        }
    ],
    "sector_trends": [
        {
            "sector": "Semiconductors",
            "direction": "down",
            "key_driver": "Cuts to capex outlook from a Tier-1 foundry rippled through the supply chain.",
            "sources": ["https://example.com/semi"],
        }
    ],
}


def test_render_html_contains_sections():
    html = render_html(CANNED_DIGEST)
    assert "Top Market Movers" in html
    assert "Regional Politics" in html
    assert "Sector Trends" in html
    assert "Nikkei 225" in html
    assert "https://example.com/semi" in html


def test_render_text_has_all_items():
    text = render_text(CANNED_DIGEST)
    for m in CANNED_DIGEST["top_movers"]:
        assert m["name"] in text
    for p in CANNED_DIGEST["regional_politics"]:
        assert p["headline"] in text
    for s in CANNED_DIGEST["sector_trends"]:
        assert s["sector"] in text


def test_render_handles_missing_pct():
    d = dict(CANNED_DIGEST)
    d["top_movers"] = [dict(d["top_movers"][0], change_1d_pct=None, change_5d_pct=None)]
    html = render_html(d)
    text = render_text(d)
    assert "Nikkei 225" in html
    assert "Nikkei 225" in text
