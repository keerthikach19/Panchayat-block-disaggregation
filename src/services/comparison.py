"""Paired forecast disagreement, never observational accuracy."""
import math
from datetime import date
from functools import lru_cache
from src.ingestion.forecast_schema import digest, WEATHER_FIELDS


def statistics(rows):
    if not rows:
        return {"count": 0}
    n = len(rows)
    weights = [r["area_m2"] for r in rows]
    area = sum(weights)
    def mean(key):
        return sum(r[key] for r in rows) / n
    def weighted(key):
        return sum(r[key] * w for r, w in zip(rows, weights)) / area
    absolute = sorted(abs(r["difference_mm"]) for r in rows)
    def quantile(q):
        i = q * (n - 1)
        lo = int(i)
        return absolute[lo] + (absolute[min(lo + 1, n - 1)] - absolute[lo]) * (i - lo)
    return {"count": n, "block_mean_mm": mean("block_local_mm"),
            "district_mean_mm": mean("district_local_mm"), "mean_difference_mm": mean("difference_mm"),
            "mean_absolute_difference_mm": sum(absolute) / n,
            "root_mean_square_difference_mm": math.sqrt(sum(r["difference_mm"]**2 for r in rows) / n),
            "median_absolute_difference_mm": quantile(.5), "p90_absolute_difference_mm": quantile(.9),
            "max_absolute_difference_mm": absolute[-1],
            "area_weighted_block_mm": weighted("block_local_mm"),
            "area_weighted_district_mm": weighted("district_local_mm"),
            "area_weighted_difference_mm": weighted("difference_mm"),
            "area_weighted_absolute_difference_mm": sum(abs(r["difference_mm"]) * w for r,w in zip(rows,weights))/area,
            "mean_source_component_mm": mean("source_component_mm"),
            "mean_reference_component_mm": mean("reference_component_mm"),
            "mean_absolute_source_component_mm": sum(abs(r["source_component_mm"]) for r in rows)/n,
            "mean_absolute_reference_component_mm": sum(abs(r["reference_component_mm"]) for r in rows)/n,
            "block_higher": sum(r["difference_mm"] > .0001 for r in rows),
            "district_higher": sum(r["difference_mm"] < -.0001 for r in rows),
            "equal_within_rounding": sum(abs(r["difference_mm"]) <= .0001 for r in rows),
            "above_1mm": sum(abs(r["difference_mm"]) > 1 for r in rows),
            "above_5mm": sum(abs(r["difference_mm"]) > 5 for r in rows),
            "above_10mm": sum(abs(r["difference_mm"]) > 10 for r in rows),
            "different_20mm_trigger": sum((r["block_local_mm"] >= 20) != (r["district_local_mm"] >= 20) for r in rows)}


def pair_rows(block_rows, district_rows):
    def index(rows):
        result = {r["panchayat_id"]: r for r in rows}
        if len(result) != len(rows):
            raise ValueError("Duplicate village IDs in comparison")
        return result
    left, right = index(block_rows), index(district_rows)
    result = []
    for pid in sorted(left.keys() & right.keys()):
        b, d = left[pid], right[pid]
        if b["valid_date"] != d["valid_date"] or b["block_id"] != d["block_id"]:
            raise ValueError("Village/date/parent alignment mismatch")
        bt, dt = b.get("adjustment_details"), d.get("adjustment_details")
        if not bt or not dt or not math.isclose(bt["area_m2"], dt["area_m2"], rel_tol=1e-10):
            raise ValueError("Comparison requires matched terrain-model footprints")
        sb, sd = b["source_rainfall_mm"], d["source_rainfall_mm"]
        fb, fd = bt["rainfall_factor"], dt["rainfall_factor"]
        delta = b["local_rainfall_mm"] - d["local_rainfall_mm"]
        source = (sb-sd)*(fb+fd)/2
        reference = (sb+sd)*(fb-fd)/2
        result.append({"panchayat_id": pid, "name": b["panchayat_name"], "block": b["block_name"],
            "valid_date": b["valid_date"], "area_m2": bt["area_m2"],
            "elevation_m": bt["village_elevation_m"],
            "block_source_mm": sb, "district_source_mm": sd,
            "block_factor": fb, "district_factor": fd,
            "block_local_mm": b["local_rainfall_mm"], "district_local_mm": d["local_rainfall_mm"],
            "difference_mm": delta, "percent_vs_district": 100*delta/d["local_rainfall_mm"] if d["local_rainfall_mm"] else None,
            "source_component_mm": source, "reference_component_mm": reference,
            "weather": {k: {"block": b.get(k), "district": d.get(k),
                "difference": b[k] - d[k] if b.get(k) is not None and d.get(k) is not None else None}
                for k in WEATHER_FIELDS if k != "wind_direction_deg"},
            "rounding_residual_mm": delta-source-reference})
    return result, {"block_only_ids": sorted(left.keys()-right.keys()),
                    "district_only_ids": sorted(right.keys()-left.keys())}


class ComparisonService:
    def __init__(self, service):
        self.service = service

    def compare(self, valid_date=None, block=None, block_run_id=None, district_run_id=None):
        s = self.service
        b = s.forecast(mode="block", run_id=block_run_id)
        d = s.forecast(mode="district", run_id=district_run_id)
        snapshot = self._snapshot(b["run_id"], d["run_id"])
        dates = snapshot["overlap_dates"]
        selected = valid_date or dates[0]
        if selected not in dates:
            raise ValueError("Date is not shared by both sources: " + ", ".join(dates))
        canonical = s.registry.block("Nashik", block)["name"] if block else None
        rows = [r for r in snapshot["rows"] if r["valid_date"] == selected and (not canonical or r["block"] == canonical)]
        if not rows:
            raise ValueError("No paired villages for this selection")
        by_date = []
        for day in dates:
            daily = [r for r in snapshot["rows"] if r["valid_date"] == day and (not canonical or r["block"] == canonical)]
            by_date.append({"valid_date": day, **statistics(daily)})
        blocks = [{"block": name, **statistics([r for r in rows if r["block"] == name])}
                  for name in sorted({r["block"] for r in rows})]
        return {**{k:v for k,v in snapshot.items() if k != "rows"}, "valid_date": selected,
                "weather_summary": {k: weather_statistics(rows, k) for k in WEATHER_FIELDS if k != "wind_direction_deg"},
                "selected_block": canonical, "summary": statistics(rows), "by_date": by_date,
                "by_block": blocks, "rows": rows,
                "top_disagreements": sorted(rows, key=lambda r: abs(r["difference_mm"]), reverse=True)[:10]}

    @lru_cache(maxsize=6)
    def _snapshot(self, block_run_id, district_run_id):
        s = self.service
        b = s.forecast(mode="block", run_id=block_run_id)
        d = s.forecast(mode="district", run_id=district_run_id)
        if b["model_version"] != d["model_version"]:
            raise ValueError("Models differ; activate the same terrain model before isolating source/reference effects")
        dates = sorted(set(b["valid_dates"]) & set(d["valid_dates"]))
        if not dates:
            raise ValueError("No overlapping forecast dates. Import a block issue overlapping the district bulletin.")
        rows, coverage = [], {}
        variables = set(WEATHER_FIELDS)
        for day in dates:
            br = s.forecast(mode="block", run_id=block_run_id, valid_date=day)["data"]
            dr = s.forecast(mode="district", run_id=district_run_id, valid_date=day)["data"]
            paired, missing = pair_rows(br, dr)
            rows.extend(paired)
            coverage[day] = {"paired":len(paired), **missing}
            for r in br + dr:
                variables &= {k for k in WEATHER_FIELDS if r.get(k) is not None}
        def provenance(f):
            return {k:f.get(k) for k in ("run_id","dataset_version","model_version","issue_date","valid_dates","source_url","downloaded_at","cache_status","last_retrieval_error","freshness")}
        delta_issue = (date.fromisoformat(d["issue_date"])-date.fromisoformat(b["issue_date"])).days if b["issue_date"] and d["issue_date"] else None
        return {"comparison_id": "comparison-"+digest([block_run_id,district_run_id,rows])[:20],
                "block_source":provenance(b), "district_source":provenance(d), "overlap_dates":dates,
                "block_only_dates":sorted(set(b["valid_dates"])-set(dates)),
                "district_only_dates":sorted(set(d["valid_dates"])-set(dates)),
                "district_issue_days_later":delta_issue, "comparable_variables":sorted(variables),
                "unavailable_variables": sorted(set(WEATHER_FIELDS)-variables),
                "coverage":coverage, "rows":rows,
                "interpretation":"Positive difference means block-derived rainfall is higher. This measures disagreement, not accuracy.",
                "decomposition":"Symmetric algebra: source=(Sb-Sd)*(fb+fd)/2; reference=(Sb+Sd)*(fb-fd)/2; sum equals B-D before output rounding. Not causal attribution.",
                "limitation":"Same validity date does not prove identical accumulation hours, issue time or forecast lead time. Village polygons are not verified gram-panchayat boundaries."}


def weather_statistics(rows, key):
    pairs = [r["weather"][key] for r in rows if r["weather"][key]["difference"] is not None]
    if not pairs:
        return {"count": 0}
    n = len(pairs)
    return {"count": n, "block_mean": sum(p["block"] for p in pairs)/n,
            "district_mean": sum(p["district"] for p in pairs)/n,
            "mean_absolute_difference": sum(abs(p["difference"]) for p in pairs)/n,
            "max_absolute_difference": max(abs(p["difference"]) for p in pairs)}
