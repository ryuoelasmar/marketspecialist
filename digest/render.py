"""Render the structured digest into HTML + plain text."""

from __future__ import annotations

from jinja2 import Environment, BaseLoader, select_autoescape


HTML_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Market Specialist Digest — {{ digest.date }}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; max-width: 640px; margin: 0 auto; padding: 24px; color: #111;">

<p style="color:#666; font-size:12px; margin:0 0 4px 0;">MARKET SPECIALIST &middot; {{ digest.date }}</p>
<h1 style="font-size:22px; margin:0 0 16px 0; line-height:1.3;">{{ digest.headline }}</h1>

<h2 style="font-size:14px; text-transform:uppercase; letter-spacing:.08em; color:#444; border-bottom:1px solid #eee; padding-bottom:6px;">Top Market Movers (1–5d)</h2>
<ul style="padding-left:18px;">
{% for m in digest.top_movers %}
  <li style="margin-bottom:10px;">
    <strong>{{ m.name }}</strong> <span style="color:#666;">({{ m.region }})</span>
    {% if m.change_1d_pct is not none %}<span style="color:{{ '#0a7d2a' if m.change_1d_pct >= 0 else '#b10e1e' }};"> {{ '%+.2f' % m.change_1d_pct }}%</span> 1d{% endif %}
    {% if m.change_5d_pct is not none %}<span style="color:#666;"> / {{ '%+.2f' % m.change_5d_pct }}% 5d</span>{% endif %}
    <div>{{ m.why }}</div>
    <div style="font-size:12px; color:#666;">{% for s in m.sources %}<a href="{{ s }}" style="color:#2a5bd7;">source{{ loop.index }}</a>{% if not loop.last %} &middot; {% endif %}{% endfor %}</div>
  </li>
{% endfor %}
</ul>

<h2 style="font-size:14px; text-transform:uppercase; letter-spacing:.08em; color:#444; border-bottom:1px solid #eee; padding-bottom:6px;">Regional Politics &amp; Regulations</h2>
<ul style="padding-left:18px;">
{% for p in digest.regional_politics %}
  <li style="margin-bottom:10px;">
    <strong>{{ p.region }}:</strong> {{ p.headline }}
    <div>{{ p.impact }}</div>
    <div style="font-size:12px; color:#666;">{% for s in p.sources %}<a href="{{ s }}" style="color:#2a5bd7;">source{{ loop.index }}</a>{% if not loop.last %} &middot; {% endif %}{% endfor %}</div>
  </li>
{% endfor %}
</ul>

<h2 style="font-size:14px; text-transform:uppercase; letter-spacing:.08em; color:#444; border-bottom:1px solid #eee; padding-bottom:6px;">Sector Trends</h2>
<ul style="padding-left:18px;">
{% for s in digest.sector_trends %}
  <li style="margin-bottom:10px;">
    <strong>{{ s.sector }}</strong> <span style="color:{{ '#0a7d2a' if s.direction == 'up' else ('#b10e1e' if s.direction == 'down' else '#666') }};">{{ s.direction }}</span>
    <div>{{ s.key_driver }}</div>
    <div style="font-size:12px; color:#666;">{% for u in s.sources %}<a href="{{ u }}" style="color:#2a5bd7;">source{{ loop.index }}</a>{% if not loop.last %} &middot; {% endif %}{% endfor %}</div>
  </li>
{% endfor %}
</ul>

<p style="font-size:11px; color:#999; margin-top:24px;">Generated automatically. Numbers from Yahoo Finance (via yfinance). News synthesized from RSS + NewsAPI + Finnhub.</p>

</body>
</html>
"""


TEXT_TEMPLATE = """MARKET SPECIALIST — {{ digest.date }}
{{ digest.headline }}

TOP MARKET MOVERS (1-5d)
{% for m in digest.top_movers %}* {{ m.name }} ({{ m.region }}){% if m.change_1d_pct is not none %}  {{ '%+.2f' % m.change_1d_pct }}% 1d{% endif %}{% if m.change_5d_pct is not none %} / {{ '%+.2f' % m.change_5d_pct }}% 5d{% endif %}
  {{ m.why }}
  Sources: {% for s in m.sources %}{{ s }}{% if not loop.last %} | {% endif %}{% endfor %}

{% endfor %}
REGIONAL POLITICS & REGULATIONS
{% for p in digest.regional_politics %}* [{{ p.region }}] {{ p.headline }}
  {{ p.impact }}
  Sources: {% for s in p.sources %}{{ s }}{% if not loop.last %} | {% endif %}{% endfor %}

{% endfor %}
SECTOR TRENDS
{% for s in digest.sector_trends %}* {{ s.sector }} — {{ s.direction }}
  {{ s.key_driver }}
  Sources: {% for u in s.sources %}{{ u }}{% if not loop.last %} | {% endif %}{% endfor %}

{% endfor %}
--
Generated automatically.
"""


def _env() -> Environment:
    return Environment(loader=BaseLoader(), autoescape=select_autoescape(["html", "xml"]))


def render_html(digest: dict) -> str:
    tpl = _env().from_string(HTML_TEMPLATE)
    return tpl.render(digest=digest)


def render_text(digest: dict) -> str:
    tpl = Environment(loader=BaseLoader()).from_string(TEXT_TEMPLATE)
    return tpl.render(digest=digest)
