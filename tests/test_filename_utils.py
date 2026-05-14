from app.services.filename_utils import display_filename, make_upload_filename


def test_display_filename_removes_internal_upload_prefix():
    assert display_filename("20260513_221728_375175_prefeitura.xlsx") == "prefeitura.xlsx"


def test_display_filename_keeps_normal_filename():
    assert display_filename("folha_prefeitura.csv") == "folha_prefeitura.csv"


def test_make_upload_filename_keeps_original_name_after_prefix():
    filename = make_upload_filename("folha prefeitura.csv")

    assert filename.endswith("_folha_prefeitura.csv")
    assert display_filename(filename) == "folha_prefeitura.csv"
