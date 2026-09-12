"""Printable, source-pinned GKMS-style academic draft; no automatic dissemination."""
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

FIELDS = [("rainfall_mm", "Rainfall", "mm"), ("temp_max_c", "Maximum temperature", "°C"),
          ("temp_min_c", "Minimum temperature", "°C"),
          ("relative_humidity_max_pct", "Maximum humidity", "%"),
          ("relative_humidity_min_pct", "Minimum humidity", "%"),
          ("wind_speed_kmph", "Wind speed", "km/h")]
SOP = "https://mausam.imd.gov.in/imd_latest/contents/pdf/gkms_sop.pdf"


def render_bulletin(service, village_id, mode="block", run_id=None):
    first = service.explanation(village_id, mode=mode, run_id=run_id)
    forecast = service.forecast(mode=mode, run_id=first["run_id"])
    days = [service.explanation(village_id, mode=mode, run_id=first["run_id"], valid_date=day)
            for day in forecast["valid_dates"]]
    e = lambda value: escape(str(value), quote=True)
    def value(v):
        return "Unavailable" if v is None else e(f"{v:.2f}" if isinstance(v, (float, int)) else v)
    def cell(day, key):
        if key.startswith("relative_humidity_") or key == "wind_speed_kmph":
            return f"<td>{value(day['source'].get(key))}<small>Source forecast; no local adjustment</small></td>"
        return f"<td>{value(day.get(key))}<small>Source: {value(day['source'].get(key))}</small></td>"
    headers = "".join(f"<th>{e(d['valid_date'])}</th>" for d in days)
    table = "".join(f"<tr><th>{e(label)} ({unit})</th>" + "".join(
        cell(d, key) for d in days) + "</tr>"
        for key, label, unit in FIELDS)
    guidance = "".join(f"<tr><th>{e(d['valid_date'])}</th><td>{e(d['advisory']['text'])}</td></tr>" for d in days)
    names = first["source"].get("sources", [])
    provenance = "".join(f"<li>{e(s['filename'])} · SHA-256 {e(s['sha256'])}</li>" for s in names)
    source_url = first["source"].get("source_url")
    if source_url and source_url.startswith("https://"):
        provenance += f'<li><a href="{e(source_url)}">Official district source bulletin</a></li>'
    period = f"{days[0]['valid_date']} to {days[-1]['valid_date']}"
    total = sum(d["rainfall_mm"] for d in days)
    sms = f"{first['panchayat_name'][:50]}: {period}. Forecast rain total {total:.1f} mm. Check drainage and soil moisture; review local weather before field work. Academic draft; consult local agromet advice."
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weather bulletin — {e(first['panchayat_name'])}</title><style>
body{{font:14px/1.5 system-ui,sans-serif;color:#183044;max-width:1100px;margin:30px auto;padding:0 22px}}h1{{font-size:27px}}h2{{font-size:19px;margin-top:26px}}.notice{{background:#fff3d6;border-left:4px solid #c38308;padding:12px}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{border:1px solid #c5d4df;padding:8px;text-align:left}}th{{background:#edf4f8}}small{{display:block;color:#586c79}}.wrap{{overflow-wrap:anywhere}}button{{padding:10px 18px;cursor:pointer}}@media print{{body{{margin:0;padding:0;font-size:11px}}button{{display:none}}table{{font-size:9px}}th,td{{padding:5px}}tr{{break-inside:avoid}}h2{{break-after:avoid}}}}
</style><body><button onclick="window.print()">Print / Save as PDF</button>
<h1>GKMS-style agrometeorological bulletin</h1><p class="notice"><strong>Academic draft — not an official IMD/GKMS advisory.</strong> Local estimates are experimental. Crop-specific decisions require verified crop stage, field observations and local agronomic review.</p>
<p><strong>{e(first['panchayat_name'])}, {e(first['block_name'])} block, Nashik</strong><br>Village ID: {e(village_id)} · Source: {e(mode)} · Issued: {e(first['issue_date'])}<br>Valid: {e(period)} (Asia/Kolkata) · Status: {e(forecast['freshness'])}<br>Generated: {e(datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(timespec='seconds'))}</p>
<h2>Five-day weather forecast</h2><p>Rainfall and temperature show local estimates beside their parent source. Humidity and wind speed show unchanged source forecasts. Missing measurements remain unavailable.</p><table><thead><tr><th>Parameter</th>{headers}</tr></thead><tbody>{table}</tbody></table>
<p>Total predicted rain across this source period: <strong>{total:.2f} mm</strong>. This is a forecast sum, not observed rainfall. Different source issues may disagree.</p>
<h2>Weather-based general guidance</h2><table><tr><th>Date</th><th>Draft guidance</th></tr>{guidance}</table>
<h2>Field information and official products</h2><table><tr><th>Past five-day observed weather</th><td>Not supplied as a verified local series; forecasts above must not be used as observations.</td></tr><tr><th>Crop, stage, soil moisture, pests</th><td>Not supplied. Crop-specific treatments, doses and pest predictions are not generated.</td></tr><tr><th>Official weather warnings</th><td>Not parsed. Check the current IMD bulletin and district warnings; absence here does not mean no warning.</td></tr><tr><th>Days 6–12 outlook</th><td>Not available in the five-day input. No extrapolated outlook is generated.</td></tr><tr><th>Local review / feedback</th><td>Reviewer: __________ Date: __________<br>Crop / stage / observed conditions / actions: ____________________</td></tr></table>
<h2>Short-message preview</h2><p>{e(sms[:262])}</p><small>Preview only; no message has been sent.</small>
<h2>Method and provenance</h2><p>Rainfall uses parent-normalized terrain factors. Temperature uses an assumed −6.5°C/km elevation adjustment. Humidity and wind speed inherit the parent source without local adjustment. Village polygons are not verified gram-panchayat boundaries.</p>
<p class="wrap">Model: {e(first['model_version'])}<br>Dataset: {e(first['dataset_version'])}<br>Run: {e(first['run_id'])}</p><ul class="wrap">{provenance}</ul>
<p>Bulletin organization follows the weather, field-context and advisory themes of <a href="{SOP}">IMD GKMS SOP, section 6</a>. This draft lacks the observational and expert inputs needed for an official bulletin.</p></body></html>'''
