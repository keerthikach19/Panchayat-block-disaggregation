"""Single explicit administrative registry and conservative village joins."""
import csv
from collections import Counter
from shapely.geometry import shape
from src.ingestion.forecast_schema import ROOT, read_json, digest

class Registry:
    def __init__(self, root=ROOT):
        self.root = root
        self.config = read_json(root / "config/administrative_units.json")
        self.aliases = read_json(root / "config/block_aliases.json")

    def district(self, name):
        for item in self.config["districts"]:
            if item["enabled"] and name.casefold() in (item["name"].casefold(), item["id"].casefold()):
                return item
        raise ValueError(f"Unsupported district: {name}")

    def block(self, district, name):
        d = self.district(district)
        clean = name.strip().casefold()
        aliases = {k.casefold(): v.casefold() for k, v in self.aliases.get(d["name"], {}).items()}
        clean = aliases.get(clean, clean)
        for b in d["blocks"]:
            if clean in (b["name"].casefold(), b["id"].casefold()):
                return b
        raise ValueError(f"Unresolved block: {d['name']}/{name}")

    def geography(self, district="Nashik"):
        d = self.district(district)
        raw = read_json(self.root / f"data/boundaries/{d['name'].lower()}_panchayats_covariates.geojson")
        with (self.root / "data/panchayat_covariates.csv").open(encoding="utf-8-sig") as f:
            cov = [r for r in csv.DictReader(f) if r["district_name"] == d["name"]]
        counts = Counter(r["panchayat_id"] for r in cov)
        geo_counts = Counter(f["properties"]["panchayat_id"] for f in raw["features"])
        by_id = {r["panchayat_id"]: r for r in cov}
        features, linked, rejected = [], [], []
        for index, feat in enumerate(raw["features"]):
            p = feat["properties"]
            pid = p["panchayat_id"]
            reasons = []
            b = None
            try:
                b = self.block(d["name"], p["block_name"])
            except ValueError as exc:
                reasons.append(str(exc))
            row = by_id.get(pid)
            if not row:
                reasons.append("Missing covariate record")
            if counts[pid] != 1 or geo_counts[pid] != 1:
                reasons.append("Duplicate/placeholder geographic ID")
            if row and b:
                try:
                    if self.block(d["name"], row["block_name"]) != b:
                        reasons.append("Boundary/covariate parent disagreement")
                except ValueError as exc:
                    reasons.append(str(exc))
            try:
                geometry = shape(feat["geometry"])
                if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in ("Polygon", "MultiPolygon"):
                    reasons.append("Invalid polygon geometry")
            except Exception:
                reasons.append("Missing/invalid geometry")
            props = {"panchayat_id": pid, "panchayat_name": p.get("village") or p.get("panchayat_name"),
                     "geographic_level": "village", "district_name": d["name"],
                     "source_block_name": p.get("block_name"), "block_name": b["name"] if b else None,
                     "block_id": b["id"] if b else None, "available": not reasons,
                     "unavailable_reason": "; ".join(reasons) or None}
            features.append({"type": "Feature", "geometry": feat["geometry"], "properties": props})
            if reasons:
                rejected.append({"feature_index": index, **props})
            else:
                linked.append(props)
        linked_ids = {r["panchayat_id"] for r in linked}
        report = {"total_features": len(features), "linked_villages": len(linked),
                  "unmatched_covariate_ids": sorted(set(by_id) - linked_ids),
                  "excluded_features": len(rejected), "rejected": rejected,
                  "duplicate_ids": sorted(k for k, v in geo_counts.items() if v > 1),
                  "by_block": {b["name"]: sum(r["block_id"] == b["id"] for r in linked) for b in d["blocks"]},
                  "geographic_level": "village",
                  "limitation": "Village polygons; no verified village-to-gram-panchayat crosswalk. Parent associations use matching source labels, not verified development-block boundary containment."}
        return {"type": "FeatureCollection", "features": features}, linked, report

    @property
    def version(self):
        return digest([self.config, self.aliases])[:16]

