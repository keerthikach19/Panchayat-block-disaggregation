"""Validated, versioned offline adjustment artifacts. No training during serving."""
from functools import lru_cache
from src.ingestion.forecast_schema import ROOT, read_json, digest, safe_id
from src.geography.registry import Registry

def load_terrain_model(root=ROOT, model_version=None):
    directory=root/"data/models/terrain_proxy"
    if model_version is None:
        model_version=read_json(directory/"active.json")["model_version"]
    return _load_version(root, model_version)

@lru_cache(maxsize=8)
def _load_version(root, model_version):
    directory=root/"data/models/terrain_proxy"
    folder=directory/safe_id(model_version)
    meta=read_json(folder/"metadata.json")
    adjustments=read_json(folder/"local_adjustments.json")
    report=read_json(folder/"validation_report.json")
    if (meta["model_version"]!=model_version or meta["registry_version"]!=Registry(root).version
        or digest(adjustments)!=meta["adjustments_checksum"] or digest(report)!=meta["report_checksum"]):
        raise ValueError("Terrain model checksum/registry/version mismatch")
    return meta,{p["panchayat_id"]:p for p in adjustments},report
