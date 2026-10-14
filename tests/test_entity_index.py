"""The typeahead index: buyers and suppliers, never people."""

from __future__ import annotations

import json

import duckdb

from achizitii.entitati import FILE, is_natural_person, write_index


def _bundle(tmp_path, autoritati, furnizori):
    con = duckdb.connect()
    con.execute("CREATE TABLE a(an SMALLINT, autoritate_cui VARCHAR, autoritate VARCHAR,"
                " valoare_totala_ron DOUBLE)")
    con.executemany("INSERT INTO a VALUES (?, ?, ?, ?)", autoritati)
    con.execute("CREATE TABLE f(an SMALLINT, furnizor_cui VARCHAR, furnizor VARCHAR,"
                " valoare_totala_ron DOUBLE)")
    con.executemany("INSERT INTO f VALUES (?, ?, ?, ?)", furnizori)
    con.execute(f"COPY a TO '{tmp_path / 'autoritati_an.parquet'}' (FORMAT parquet)")
    con.execute(f"COPY f TO '{tmp_path / 'furnizori_an.parquet'}' (FORMAT parquet)")
    con.close()


def test_natural_persons_are_recognised():
    assert is_natural_person("II Cimpoies Mariana", "123")
    assert is_natural_person("CREANGA V. GABRIEL II", "123")
    assert is_natural_person("Popescu Ion PFA", "123")
    assert is_natural_person("P.F.A. Popescu Ion", "123")
    assert is_natural_person("BICHEA FLOREA PERSOANA FIZICA", "456")
    assert is_natural_person("Cabinet Individual Avocat Sabou Corina", "789")
    assert is_natural_person("Macaveiu Eugen", "1510513010036")      # CNP-shaped
    assert not is_natural_person("DEDEMAN S.R.L.", "2816464")
    assert not is_natural_person("VODAFONE ROMANIA", "8971726")
    assert not is_natural_person("SPITALUL CLINIC FUNDENI", "4316422")


def test_index_ranks_merges_and_drops_people(tmp_path):
    _bundle(
        tmp_path,
        [(2020, "4316422", "SPITALUL FUNDENI", 10.0),
         (2021, "4316422", "SPITALUL CLINIC FUNDENI", 30.0),
         (2021, "999", "PRIMARIA MICA", 1.0),
         (2021, "998", "COLEGIUL NATIONAL CAROL II", 0.5)],
        [(2021, "2816464", "DEDEMAN S.R.L.", 50.0),
         (2021, "1510513010036", "Macaveiu Eugen", 900.0),
         (2021, "111", "II Cimpoies Mariana", 800.0),
         (2021, "", "FARA CUI SRL", 700.0)],
    )
    meta = write_index(tmp_path)
    rows = json.loads((tmp_path / FILE).read_text(encoding="utf-8"))["entitati"]
    assert rows == [
        ["DEDEMAN S.R.L.", "2816464", "f"],
        ["SPITALUL CLINIC FUNDENI", "4316422", "a"],   # newest name, one row per CUI
        ["PRIMARIA MICA", "999", "a"],
        ["COLEGIUL NATIONAL CAROL II", "998", "a"],   # buyers are public bodies
    ]
    assert meta == {"file": FILE, "bytes": (tmp_path / FILE).stat().st_size, "n": 4}


def test_index_is_capped(tmp_path):
    _bundle(tmp_path,
            [(2021, str(i), f"AUTORITATE {i}", float(i)) for i in range(1, 30)],
            [(2021, str(100 + i), f"FIRMA {i} SRL", float(i)) for i in range(1, 30)])
    write_index(tmp_path, per_kind=5)
    rows = json.loads((tmp_path / FILE).read_text(encoding="utf-8"))["entitati"]
    assert len(rows) == 10
    assert ["AUTORITATE 29", "29", "a"] in rows
    assert ["AUTORITATE 24", "24", "a"] not in rows


def test_missing_bundle_writes_nothing(tmp_path):
    assert write_index(tmp_path) is None
    assert not (tmp_path / FILE).exists()
