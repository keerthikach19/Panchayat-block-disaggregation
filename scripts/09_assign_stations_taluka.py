#!/usr/bin/env python3
"""
scripts/09_assign_stations_taluka.py

Maps all 40 physical stations in Maharashtra to their administrative taluka (sub-district).
For stations in Nashik and Pune, matches exact taluka agro-ecological regions.
For statewide coastal/plateau/vidarbha stations, assigns official taluka headquarters.
"""

from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIONS_FILE = PROJECT_ROOT / "data" / "stations" / "maharashtra_stations_metadata.csv"

# Comprehensive Ground-Truth Mapping for all 40 IMD/AWS Stations in Maharashtra
STATION_TALUKA_MAP = {
    # Konkan Coastal
    "MH_KON_01": "Mumbai City",       # Colaba_Mumbai
    "MH_KON_02": "Kurla",             # Santacruz_Mumbai (Mumbai Suburban)
    "MH_KON_03": "Ratnagiri",         # Ratnagiri
    "MH_KON_04": "Dahanu",            # Dahanu (Palghar)
    "MH_KON_05": "Alibag",            # Alibag (Raigad)
    "MH_KON_06": "Vengurla",          # Vengurla (Sindhudurg)
    "MH_KON_07": "Dapoli",            # Harnai (Ratnagiri)

    # Sahyadri Crest
    "MH_SAH_01": "Mahabaleshwar",     # Mahabaleshwar (Satara)
    "MH_SAH_02": "Igatpuri",          # Igatpuri (Nashik)
    "MH_SAH_03": "Trimbakeshwar",     # Trimbakeshwar (Nashik)
    "MH_SAH_04": "Peint",             # Peth / Peint (Nashik)
    "MH_SAH_05": "Surgana",           # Surgana (Nashik)
    "MH_SAH_06": "Mawal",             # Lonavala (Pune)
    "MH_SAH_07": "Gaganbawda",        # Gaganbawda (Kolhapur)
    "MH_SAH_08": "Ambegaon",          # Bhimashankar (Pune)

    # Deccan Plateau (Nashik Talukas)
    "MH_DEC_01": "Nashik",            # Nashik_City
    "MH_DEC_02": "Niphad",            # Niphad_Grape_Belt
    "MH_DEC_03": "Sinnar",            # Sinnar
    "MH_DEC_04": "Dindori",           # Dindori
    "MH_DEC_05": "Kalwan",            # Kalwan
    "MH_DEC_06": "Malegaon",          # Malegaon
    "MH_DEC_07": "Deola",             # Deola
    "MH_DEC_08": "Yeola",             # Yeola
    "MH_DEC_09": "Nandgaon",          # Nandgaon
    "MH_DEC_10": "Chandvad",          # Chandwad
    "MH_DEC_11": "Baglan",            # Baglan_Satana

    # Deccan Plateau (Pune & Central Maharashtra)
    "MH_DEC_12": "Haveli",            # Pune_Shivajinagar
    "MH_DEC_13": "Baramati",          # Baramati
    "MH_DEC_14": "Nagar",             # Ahmednagar
    "MH_DEC_15": "Solapur North",     # Solapur
    "MH_DEC_16": "Aurangabad",        # Chhatrapati_Sambhajinagar
    "MH_DEC_17": "Jalgaon",           # Jalgaon

    # Vidarbha East
    "MH_VID_01": "Nagpur Urban",      # Nagpur_Airport
    "MH_VID_02": "Amravati",          # Amravati
    "MH_VID_03": "Akola",             # Akola
    "MH_VID_04": "Wardha",            # Wardha
    "MH_VID_05": "Chandrapur",        # Chandrapur
    "MH_VID_06": "Gondia",            # Gondia
    "MH_VID_07": "Yavatmal",          # Yavatmal
    "MH_VID_08": "Nanded",            # Nanded
}

def assign_talukas():
    df = pd.read_csv(STATIONS_FILE)
    df["taluka"] = df["id"].map(STATION_TALUKA_MAP)
    
    # Verify no unmapped stations
    missing = df[df["taluka"].isna()]
    if not missing.empty:
        raise ValueError(f"Stations missing taluka mapping: {missing['id'].tolist()}")
        
    df.to_csv(STATIONS_FILE, index=False)
    print(f"✓ Successfully assigned talukas to all {len(df)} stations in {STATIONS_FILE}")
    print("\nSample stations with taluka mapping:")
    print(df[["id", "name", "district", "taluka"]].head(10).to_string(index=False))

if __name__ == "__main__":
    assign_talukas()
