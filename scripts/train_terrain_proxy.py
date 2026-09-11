"""Offline terrain extraction and proxy-climatology model comparison.

The targets are NASA POWER gridded series in the legacy CSV, NOT station ground
truth. Evaluation is spatial/temporal proxy reconstruction, not forecast accuracy.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from shapely.geometry import shape, box, mapping
from pyproj import Geod
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.base import clone
from src.ingestion.forecast_schema import ROOT, digest, file_hash, immutable_json, atomic_json
from src.geography.registry import Registry

def candidate(name):
    if name == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    if name == "random_forest":
        return RandomForestRegressor(n_estimators=200,min_samples_leaf=3,max_depth=4,random_state=42,n_jobs=1)
    if name == "distance_weighted":
        return make_pipeline(StandardScaler(),KNeighborsRegressor(n_neighbors=5,weights="distance"))
    raise ValueError(name)

def train(dem_dir,root=ROOT):
    registry=Registry(root)
    geo,places,coverage=registry.geography()
    wanted={p["panchayat_id"] for p in places}
    features=[f for f in geo["features"] if f["properties"]["panchayat_id"] in wanted]
    tiles=[]
    for path in sorted(Path(dem_dir).glob("*.tif")):
        # Only Nashik tiles are required for local extraction.
        if any(f"_N{n}_00_E{e:03d}_00_" in path.name for n in (19,20,21) for e in (73,74,75)):
            ds=rasterio.open(path)
            tiles.append((path,ds,box(*ds.bounds)))
    if not tiles:
        raise ValueError("Nashik Copernicus DEM tiles missing")
    print(f"Extracting {len(features)} village elevations from {len(tiles)} local tiles",flush=True)
    geod=Geod(ellps="WGS84")
    terrain=[]
    used=set()
    for index,f in enumerate(features):
        geometry=shape(f["geometry"])
        total,count=0.0,0
        for path,ds,bounds in tiles:
            if not geometry.intersects(bounds):
                continue
            values,_=mask(ds,[mapping(geometry)],crop=True,filled=False,indexes=1)
            vals=values.compressed()
            vals=vals[np.isfinite(vals)&(vals>-500)&(vals<9000)]
            if vals.size:
                total+=float(vals.sum()); count+=int(vals.size);used.add(path)
        if not count:
            raise ValueError(f"No DEM pixels for {f['properties']['panchayat_id']}")
        centroid=geometry.centroid
        area=abs(geod.geometry_area_perimeter(geometry)[0])
        if area<=0:
            raise ValueError("Invalid geodesic area")
        terrain.append({**f["properties"],"elevation_m":round(total/count,3),"area_m2":area,
                        "lat":centroid.y,"lon":centroid.x,"dem_pixel_count":count})
        if (index+1)%400==0:
            print(f"  {index+1} villages",flush=True)
    for _,ds,_ in tiles:
        ds.close()
    obs=pd.read_csv(root/"data/stations/maharashtra_station_observations.csv")
    if set(obs["source"]) != {"IMD_AWS_NASA_POWER_Blended"}:
        raise ValueError("Unexpected/simulated source labels: review training provenance before use")
    # Deduplicate entire daily profiles so repeated samples of the same grid cannot
    # appear on opposite sides of spatial validation folds.
    fingerprints=obs.sort_values("date").groupby("station_id").apply(
        lambda x:digest(x[["date","rainfall_mm","temp_max_c","temp_min_c","rh_pct"]].to_dict("records")),
        include_groups=False)
    stations=obs.groupby("station_id").first().reset_index()
    stations["grid_group"]=stations.station_id.map(fingerprints)
    groups=[]
    for group,st in stations.groupby("grid_group"):
        series=obs[obs.station_id==st.iloc[0].station_id].sort_values("date")
        def mean_period(start,end):
            return float(series[(series.date>=start)&(series.date<=end)].rainfall_mm.mean())
        groups.append({"group":group,"lat":float(st.lat.mean()),"lon":float(st.lon.mean()),
                       "elevation_m":float(st.elevation_m.mean()),
                       "train_mean":mean_period("2023-06-01","2023-07-31"),
                       "validation_mean":mean_period("2023-08-01","2023-08-31"),
                       "test_mean":mean_period("2023-09-01","2023-10-31"),
                       "fit_mean":mean_period("2023-06-01","2023-08-31"),
                       "station_ids":st.station_id.tolist()})
    frame=pd.DataFrame(groups)
    X=frame[["lat","lon","elevation_m"]].to_numpy()
    y=np.log1p(frame.train_mean.to_numpy())
    candidates=["unchanged_parent","ridge","random_forest","distance_weighted"]
    scores={}
    for name in candidates:
        predictions=[]
        for i in range(len(X)):
            keep=np.arange(len(X))!=i
            if name=="unchanged_parent":
                pred=float(frame.loc[keep,"train_mean"].mean())
            else:
                m=candidate(name).fit(X[keep],y[keep])
                pred=max(0,float(np.expm1(m.predict(X[i:i+1])[0])))
            predictions.append(pred)
        errors=np.array(predictions)-frame.validation_mean.to_numpy()
        scores[name]={"validation_rmse_mm_per_day":float(np.sqrt(np.mean(errors**2))),
                      "validation_mae_mm_per_day":float(np.mean(abs(errors)))}
    winner=min(candidates,key=lambda n:scores[n]["validation_rmse_mm_per_day"])
    # Test the frozen model choice on an untouched later temporal window, also
    # withholding the target spatial group. No parameter tuning on these scores.
    test_preds=[]
    for i in range(len(X)):
        keep=np.arange(len(X))!=i
        if winner=="unchanged_parent":
            pred=float(frame.loc[keep,"fit_mean"].mean())
        else:
            m=candidate(winner).fit(X[keep],np.log1p(frame.loc[keep,"fit_mean"].to_numpy()))
            pred=max(0,float(np.expm1(m.predict(X[i:i+1])[0])))
        test_preds.append(pred)
    truth=frame.test_mean.to_numpy()
    errors=np.array(test_preds)-truth
    baseline_test=np.array([frame.loc[np.arange(len(X))!=i,"fit_mean"].mean() for i in range(len(X))])
    baseline_rmse=float(np.sqrt(np.mean((baseline_test-truth)**2)))
    test_rmse=float(np.sqrt(np.mean(errors**2)))
    # Only use a non-constant proxy spatial field if it improves both windows.
    deploy_proxy=winner!="unchanged_parent" and test_rmse<baseline_rmse
    if deploy_proxy:
        model=candidate(winner).fit(X,np.log1p(frame.fit_mean.to_numpy()))
        points=np.array([[p["lat"],p["lon"],p["elevation_m"]] for p in terrain])
        climate=np.maximum(0,np.expm1(model.predict(points)))
    else:
        climate=np.ones(len(terrain))
    for p,v in zip(terrain,climate):
        p["proxy_climatology_mm"]=float(v)
    for group in sorted({p["block_id"] for p in terrain}):
        rows=[p for p in terrain if p["block_id"]==group]
        weights=np.array([p["area_m2"] for p in rows])
        ref_elev=float(np.average([p["elevation_m"] for p in rows],weights=weights))
        ref_rain=float(np.average([p["proxy_climatology_mm"] for p in rows],weights=weights))
        for p in rows:
            p["block_reference_elevation_m"]=ref_elev
            p["rainfall_factor"]=p["proxy_climatology_mm"]/ref_rain if ref_rain>0 else 1.0
            p["temperature_adjustment_c"]=-0.0065*(p["elevation_m"]-ref_elev)
    # Separate district references; district and block conservation are not mixed.
    weights=np.array([p["area_m2"] for p in terrain])
    dist_elev=float(np.average([p["elevation_m"] for p in terrain],weights=weights))
    dist_rain=float(np.average([p["proxy_climatology_mm"] for p in terrain],weights=weights))
    for p in terrain:
        p["district_rainfall_factor"]=p["proxy_climatology_mm"]/dist_rain if dist_rain>0 else 1.0
        p["district_temperature_adjustment_c"]=-0.0065*(p["elevation_m"]-dist_elev)
    training_hash=file_hash(root/"data/stations/maharashtra_station_observations.csv")
    report={"evaluation_kind":"Experimental proxy-climatology reconstruction; NOT forecast accuracy",
            "source_audit":{"legacy_label":"IMD_AWS_NASA_POWER_Blended","actual_acquisition":"NASA POWER gridded meteorology per scripts/07_assemble_stations.py; no AWS join in that code path",
                            "rows":len(obs),"station_labels":len(stations),"independent_profile_groups":len(groups),
                            "nashik_profile_groups":int(stations[stations.district=="Nashik"].grid_group.nunique())},
            "protocol":"Candidate choice: leave-one-profile-group-out using June–July targets and August validation. Frozen winner tested with June–August training and September–October held out, still leaving out each spatial group.",
            "candidate_scores":scores,"selected_candidate":winner,"rainfall_transfer_enabled":deploy_proxy,
            "test":{"selected_rmse_mm_per_day":test_rmse,"unchanged_regional_mean_rmse_mm_per_day":baseline_rmse,
                    "selected_mae_mm_per_day":float(np.mean(abs(errors)))},
            "limitations":["Targets are gridded proxies, not independent station observations.",
                           "Predicts seasonal spatial climatology, not daily forecast skill or within-block accuracy.",
                           "Training location elevations are station-catalog values; local elevations use Copernicus DSM.",
                           "Only June–October 2023 is available. No lead-time forecast/observation pairs.",
                           "Local rainfall factors transfer a coarse climatology into smaller polygons; experimental and unvalidated."],
            "training_sha256":training_hash}
    config={"algorithm_version":"terrain-proxy-v2", "lapse_rate_c_per_km":-6.5,"reference":"Area-weighted elevation of linked village footprints in each parent",
            "rainfall_method":winner if deploy_proxy else "unchanged_parent",
            "rainfall_reference_assumption":"For experimental redistribution only, assume the official parent input is an area mean over linked village footprints. This spatial interpretation is NOT verified by IMD.",
            "temperature_reference_assumption":"Assume the source temperature refers to the linked-footprint area-weighted elevation, because IMD reference elevation is unavailable. Constant lapse rate may fail under inversions."}
    terrain_sources=[{"filename":p.name,"sha256":file_hash(p)} for p in sorted(used)]
    version="terrain-"+digest([training_hash,terrain_sources,config,report,terrain,registry.version])[:20]
    metadata={"model_version":version,"training_input_level":"regional_gridded_proxy",
              "compatible_input_levels":["block","district"],"target_definition":"seasonal rainfall climatology with parent-normalized experimental transfer; DEM lapse-rate temperature adjustment",
              "feature_schema_version":"lat-lon-elevation-v1","training_data_version":training_hash,
              "training_period":"2023-06-01/2023-08-31","validation_report_id":version,
              "status":"Experimental local estimates. Proxy benchmark only; village forecast accuracy is unverified.",
              "uncertainty":"omitted; not calibrated","config":config,"terrain_sources":terrain_sources,
              "adjustments_checksum":digest(terrain),"report_checksum":digest(report),"registry_version":registry.version}
    if deploy_proxy and winner == "ridge":
        scaler = model.named_steps["standardscaler"]
        fitted = model.named_steps["ridge"]
        metadata["fitted_estimator"] = {"type":"ridge", "features":["lat","lon","elevation_m"],
            "feature_mean":scaler.mean_.tolist(), "feature_scale":scaler.scale_.tolist(),
            "coefficients":fitted.coef_.tolist(), "intercept":float(fitted.intercept_),
            "target_transform":"log1p seasonal rainfall", "alpha":10.0}
    out=root/"data/models/terrain_proxy"/version
    for name,value in [("local_adjustments.json",terrain),("validation_report.json",report),("metadata.json",metadata)]:
        immutable_json(out/name,value)
    atomic_json(root/"data/models/terrain_proxy/active.json",{"model_version":version})
    print(json.dumps({"model_version":version,"report":report,"village_count":len(terrain),
                      "rain_factor_range":[min(p["rainfall_factor"] for p in terrain),max(p["rainfall_factor"] for p in terrain)],
                      "temperature_adjustment_range":[min(p["temperature_adjustment_c"] for p in terrain),max(p["temperature_adjustment_c"] for p in terrain)]},indent=2),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dem-dir",type=Path,required=True)
    a=p.parse_args()
    train(a.dem_dir)
