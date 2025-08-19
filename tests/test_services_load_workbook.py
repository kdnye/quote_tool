import pandas as pd
import pytest

from services import quote as quote_service


def test_load_workbook_missing(monkeypatch):
    monkeypatch.setattr(quote_service, "_WORKBOOK_CACHE", None)

    def fake_read_excel(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)
    with pytest.raises(RuntimeError, match="Failed to load workbook"):
        quote_service._load_workbook()


def test_load_workbook_corrupted(monkeypatch):
    monkeypatch.setattr(quote_service, "_WORKBOOK_CACHE", None)

    def fake_read_excel(*args, **kwargs):
        raise ValueError("corrupted")

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)
    with pytest.raises(RuntimeError, match="Failed to load workbook"):
        quote_service._load_workbook()
