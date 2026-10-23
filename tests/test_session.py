from datetime import date
from pathlib import Path

from psyset.library import Instrument
from psyset.session import (crfs_for, default_filename, default_versions,
                            missing, plan_outputs, sheets_for)


def P(name):
    return Path("/fake") / name


def inst(name, sheets=(), crfs=()):
    return Instrument(folder=P(name), domain="d", name=name,
                      sheets={k: P(f"{name}-s{k}") for k in sheets},
                      crfs={k: P(f"{name}-c{k}") for k in crfs})


def test_unlabelled_shared_sheet_once():
    i = inst("T", sheets=[""], crfs=["A", "B"])
    assert sheets_for(i, ["A", "B"]) == [P("T-s")]
    assert crfs_for(i, ["A", "B"]) == [P("T-cA"), P("T-cB")]


def test_versions_follow_natural_order_not_click_order():
    i = inst("T", sheets=["A", "B"], crfs=["A", "B"])
    assert sheets_for(i, ["B", "A"]) == [P("T-sA"), P("T-sB")]
    assert crfs_for(i, ["B", "A"]) == [P("T-cA"), P("T-cB")]


def test_unknown_label_skipped_and_unlabelled_first():
    i = inst("T", sheets=["", "A"])
    assert sheets_for(i, ["Z", "A"]) == [P("T-s"), P("T-sA")]
    assert crfs_for(i, ["A"]) == []


def test_by_test_order():
    tmt = inst("TMT", sheets=[""], crfs=[""])
    hay = inst("Hayling", crfs=[""])
    cvlt = inst("CVLT", crfs=["A", "B"])
    out = plan_outputs([(tmt, []), (hay, []), (cvlt, ["A", "B"])], "by_test")
    assert out["merged"] == [P("TMT-s"), P("TMT-c"), P("Hayling-c"),
                             P("CVLT-cA"), P("CVLT-cB")]
    assert out["sheets"] == [P("TMT-s")]
    assert out["crfs"] == [P("TMT-c"), P("Hayling-c"), P("CVLT-cA"), P("CVLT-cB")]


def test_sheets_first_order():
    tmt = inst("TMT", sheets=[""], crfs=[""])
    stroop = inst("Stroop", sheets=[""], crfs=[""])
    s = [(tmt, []), (stroop, [])]
    assert plan_outputs(s, "sheets_first")["merged"] == [
        P("TMT-s"), P("Stroop-s"), P("TMT-c"), P("Stroop-c")]
    assert plan_outputs(s, "by_test")["merged"] == [
        P("TMT-s"), P("TMT-c"), P("Stroop-s"), P("Stroop-c")]


def test_by_test_multiple_versions_sheets_then_crfs():
    i = inst("T", sheets=["A", "B"], crfs=["A", "B"])
    assert plan_outputs([(i, ["A", "B"])], "by_test")["merged"] == [
        P("T-sA"), P("T-sB"), P("T-cA"), P("T-cB")]


def test_plan_outputs_empty_session_has_all_keys():
    assert plan_outputs([], "by_test") == {"sheets": [], "crfs": [], "merged": []}


def test_missing_report():
    tmt = inst("TMT", sheets=[""], crfs=[""])
    hay = inst("Hayling", crfs=[""])
    assert missing([(tmt, []), (hay, [])]) == {"no_sheet": ["Hayling"], "no_crf": []}


def test_missing_depends_on_chosen_versions():
    i = inst("T", sheets=["A"], crfs=["A", "B"])
    assert missing([(i, ["B"])]) == {"no_sheet": ["T"], "no_crf": []}


def test_default_filename():
    d = date(2026, 10, 23)
    assert default_filename("sheets", "en", d) == "2026-10-23_patient-sheets.pdf"
    assert default_filename("crfs", "en", d) == "2026-10-23_crfs.pdf"
    assert default_filename("merged", "en", d) == "2026-10-23_complete.pdf"
    assert default_filename("sheets", "fr", d) == "2026-10-23_feuilles-patient.pdf"
    assert default_filename("crfs", "fr", d) == "2026-10-23_crf.pdf"
    assert default_filename("merged", "fr", d) == "2026-10-23_complet.pdf"


def test_default_versions():
    assert default_versions(inst("T", sheets=[""]), ["A"]) == []
    i = inst("T", sheets=["A", "B"])
    assert default_versions(i, ["B"]) == ["B"]
    assert default_versions(i, ["Z"]) == ["A"]
    assert default_versions(i, None) == ["A"]
    assert default_versions(i, ["B", "Z", "A"]) == ["A", "B"]
