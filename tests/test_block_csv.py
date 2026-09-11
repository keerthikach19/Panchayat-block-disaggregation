import csv
import io
import shutil
from pathlib import Path
import pytest
from src.ingestion.block_csv import parse_file, import_collection
from src.ingestion.forecast_schema import ROOT
from src.geography.registry import Registry

SAMPLE = ROOT / "Block-level data/Nashik_Igatpuri_2026-09-10.csv"

@pytest.fixture
def source(tmp_path):
    path = tmp_path / SAMPLE.name
    path.write_bytes(SAMPLE.read_bytes())
    return path

def edit(path, row, col, value):
    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
    rows[row][col] = value
    out = io.StringIO()
    csv.writer(out, lineterminator="\r\n").writerows(rows)
    path.write_text(out.getvalue(), encoding="utf-8-sig")

def test_exact_values(source):
    rows, _ = parse_file(source)
    assert len(rows) == 5
    assert [r["rainfall_mm"] for r in rows] == [3.3, 1.6, 38.2, 33.1, 16.8]
    assert [r["temp_max_c"] for r in rows] == [27.1, 27.1, 25.7, 23.1, 24]
    assert [r["relative_humidity_max_pct"] for r in rows] == [98]*5
    assert rows[-1]["valid_date"] == "2026-09-15"

@pytest.mark.parametrize("suffix", [".csv", " - Sheet1.csv", ".CSV"])
def test_filename_bom_crlf_degrees(source, suffix):
    content = source.read_text(encoding="utf-8-sig").replace("℃", "°C")
    target = source.with_name("Nashik_Igatpuri_2026-09-10" + suffix)
    target.write_text(content, encoding="utf-8-sig", newline="\r\n")
    assert len(parse_file(target)[0]) == 5

@pytest.mark.parametrize("row,col,value", [
    (0,0,"NIPHAD : Block Forecast issued on 10-09-2026"),
    (0,0,"IGATPURI : Block Forecast issued on 09-09-2026"),
    (1,2,"11-09-2026"), (1,1,""), (2,1,""), (2,1,"NaN"), (2,1,"-1"),
    (3,1,"5"), (4,1,"50"), (5,1,"9"), (6,1,"101"), (7,1,"99"),
    (8,1,"-1"), (9,1,"361"), (2,0,"Unknown rain")
])
def test_rejects_malformed(source, row, col, value):
    edit(source, row, col, value)
    with pytest.raises(ValueError):
        parse_file(source)

def test_bad_filename_and_unknown_block(source):
    for name in ["Nashik_Igatpuri_2026-09-10 - Sheet2.csv", "Nashik_Central_2026-09-10.csv"]:
        target = source.with_name(name)
        target.write_bytes(source.read_bytes())
        with pytest.raises(ValueError):
            parse_file(target)

def test_duplicate_variable(source):
    with source.open("a", encoding="utf-8") as f:
        f.write("\nRainfall (mm),1,2,3,4,5,15\n")
    with pytest.raises(ValueError):
        parse_file(source)

def setup_root(path):
    shutil.copytree(ROOT / "config", path / "config")
    folder = path / "inputs"
    folder.mkdir()
    return folder

def test_duplicates_and_conflicts(tmp_path):
    folder = setup_root(tmp_path)
    a = folder / SAMPLE.name
    a.write_bytes(SAMPLE.read_bytes())
    b = folder / "Nashik_Igatpuri_2026-09-10 - Sheet1.csv"
    b.write_bytes(a.read_bytes())
    m,r = import_collection(folder, tmp_path)
    assert m["valid"] and m["record_count"] == 5
    assert r["duplicate_files"] == [b.name] or r["duplicate_files"] == [a.name]
    edit(b,2,1,"99")
    m,r = import_collection(folder,tmp_path)
    assert not m["valid"] and r["conflicts"]
    assert not (tmp_path / "data/imported/block_forecasts/nashik/active.json").exists()

def test_summary_is_warning(source):
    edit(source,2,6,"999")
    assert any("summary" in w for w in parse_file(source)[1])

@pytest.mark.parametrize("alias,canonical",[("Chandvad","Chandwad"),("Peint","Peth"),("Yevla","Yeola"),("Trimbakeshwar","Trimbak")])
def test_shared_aliases(alias,canonical):
    assert Registry().block("Nashik",alias)["name"] == canonical
    with pytest.raises(ValueError):
        Registry().block("Pune",alias)

