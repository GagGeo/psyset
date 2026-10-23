from psyset.i18n import DOMAINS, STRINGS, t


def test_i18n_same_keys():
    assert STRINGS["fr"].keys() == STRINGS["en"].keys()


def test_domains_exact():
    assert DOMAINS["en"] == ["Executive functioning", "Memory", "Instrumental functioning",
                             "Attention", "Social cognition", "Autonomy", "Mood"]
    assert DOMAINS["fr"] == ["Fonctions exécutives", "Mémoire", "Fonctions instrumentales",
                             "Attention", "Cognition sociale", "Autonomie", "Thymie"]


def test_t_formats():
    assert "TMT" in t("en", "warn_no_sheet", names="TMT")
    assert "TMT" in t("fr", "warn_no_crf", names="TMT")


def test_t_never_raises():
    assert t("en", "no_such_key") == "no_such_key"
    assert t("xx", "tagline") == STRINGS["en"]["tagline"]  # unknown language -> English
    assert t("en", "warn_no_sheet") == STRINGS["en"]["warn_no_sheet"]  # missing field -> raw string


def test_placeholders_match_between_languages():
    import string
    def fields(s):
        return {f for _, f, _, _ in string.Formatter().parse(s) if f}
    for key in STRINGS["en"]:
        assert fields(STRINGS["fr"][key]) == fields(STRINGS["en"][key]), key


def test_duplicate_reason_does_not_claim_a_pdf():
    assert "PDF" not in t("en", "reason_duplicate") and "PDF" not in t("fr", "reason_duplicate")
