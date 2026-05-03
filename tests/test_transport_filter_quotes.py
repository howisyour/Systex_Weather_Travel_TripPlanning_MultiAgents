"""
Unit tests for Problem 2 fix:
  agent_tool/util/transport.py

Bug: DepartureTime and ArrivalTime filter values were wrapped in single quotes:
       f"ScheduleDepartureTime le '{request.DepartureTime}'"
     TDX OData API treats ScheduleDepartureTime / ScheduleArrivalTime as
     Edm.TimeOfDay fields; OData4 time-of-day literals MUST NOT be quoted.
     The quotes caused the API to return HTTP 400 Bad Request.

Fix: Remove the quotes so the generated filter looks like:
       ScheduleDepartureTime le 09:30
       ScheduleArrivalTime ge 14:00
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Stubs for dependencies not needed by transport.py itself
# ---------------------------------------------------------------------------

def _ensure_stub(name):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)


for _m in ["dotenv"]:
    _ensure_stub(_m)

# dotenv.load_dotenv is a no-op in tests
sys.modules["dotenv"].load_dotenv = lambda **kw: None  # type: ignore


# ---------------------------------------------------------------------------
# Import the module under test using an absolute path so it works regardless
# of the current working directory.
# ---------------------------------------------------------------------------

import importlib.util
import pathlib

_transport_path = (
    pathlib.Path(__file__).resolve().parents[1]
    / "agent_tool" / "utill" / "transport.py"
)

_spec = importlib.util.spec_from_file_location("transport", _transport_path)
_transport_mod = importlib.util.module_from_spec(_spec)

# Patch out requests and model imports before exec
sys.modules["requests"] = MagicMock()

_model_pkg = types.ModuleType("model")
# The source file is misspelled as "requset"; the stub module must match that name.
_flight_request_stub_mod = types.ModuleType("model.requset")

class _FlightRequestStub:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        # defaults for optional fields
        for field in [
            "AirlineID", "FlightNumber", "DepartureTime", "ArrivalTime",
            "DepartureAirportID", "ArrivalAirportID",
            "ScheduleStartDate", "ScheduleEndDate",
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]:
            if not hasattr(self, field):
                setattr(self, field, None)

_flight_request_stub_mod.FlightRequest = _FlightRequestStub
sys.modules["model"] = _model_pkg
sys.modules["model.requset"] = _flight_request_stub_mod

_spec.loader.exec_module(_transport_mod)
TDXInternationalFlight = _transport_mod.TDXInternationalFlight


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service():
    svc = TDXInternationalFlight.__new__(TDXInternationalFlight)
    svc.client_id = "test_id"
    svc.client_secret = "test_secret"
    svc.token_url = "https://fake-token-url"
    svc.api_url = "https://fake-api-url"
    return svc


def _build_filter(svc, **req_fields) -> str:
    """Invoke get_international_schedule with a fake HTTP layer and return the filter string."""
    req = _FlightRequestStub(**req_fields)
    captured = {}

    def _fake_get(url, headers, params, timeout):
        captured["params"] = params
        resp = MagicMock()
        resp.raise_for_status = lambda: None
        resp.content = b"[]"
        return resp

    with (
        patch.object(svc, "get_access_token", return_value="fake_token"),
        patch("requests.get", side_effect=_fake_get),
    ):
        svc.get_international_schedule(req)

    return captured["params"].get("$filter", "")


# ---------------------------------------------------------------------------
# Tests for Problem 2
# ---------------------------------------------------------------------------

class TestTDXFilterDateTimeQuotes:
    """DepartureTime and ArrivalTime must appear WITHOUT quotes in the OData filter."""

    def setup_method(self):
        self.svc = _make_service()

    def test_departure_time_no_quotes(self):
        """
        ScheduleDepartureTime filter value must NOT be wrapped in single quotes.
        Correct:   ScheduleDepartureTime le 09:30
        Incorrect: ScheduleDepartureTime le '09:30'
        """
        filt = _build_filter(self.svc, DepartureTime="09:30",
                             DepartureAirportID="TPE", ArrivalAirportID="NRT")
        assert "ScheduleDepartureTime le 09:30" in filt, (
            f"Expected unquoted time literal in filter, got: {filt!r}"
        )
        assert "ScheduleDepartureTime le '09:30'" not in filt, (
            f"Found quoted time literal in filter (causes 400): {filt!r}"
        )

    def test_arrival_time_no_quotes(self):
        """
        ScheduleArrivalTime filter value must NOT be wrapped in single quotes.
        Correct:   ScheduleArrivalTime ge 14:00
        Incorrect: ScheduleArrivalTime ge '14:00'
        """
        filt = _build_filter(self.svc, ArrivalTime="14:00",
                             DepartureAirportID="TPE", ArrivalAirportID="NRT")
        assert "ScheduleArrivalTime ge 14:00" in filt, (
            f"Expected unquoted time literal in filter, got: {filt!r}"
        )
        assert "ScheduleArrivalTime ge '14:00'" not in filt, (
            f"Found quoted time literal in filter (causes 400): {filt!r}"
        )

    def test_schedule_start_date_no_quotes(self):
        """
        ScheduleStartDate is an Edm.Date field – must also be unquoted.
        (This was the original bug report example.)
        """
        filt = _build_filter(self.svc, ScheduleStartDate="2026-05-03")
        assert "ScheduleStartDate le 2026-05-03" in filt, (
            f"Expected unquoted date literal, got: {filt!r}"
        )
        assert "ScheduleStartDate le '2026-05-03'" not in filt

    def test_schedule_end_date_no_quotes(self):
        """ScheduleEndDate must also be unquoted."""
        filt = _build_filter(self.svc, ScheduleEndDate="2026-05-10")
        assert "ScheduleEndDate ge 2026-05-10" in filt
        assert "ScheduleEndDate ge '2026-05-10'" not in filt

    def test_string_fields_retain_quotes(self):
        """
        AirlineID, FlightNumber, DepartureAirportID, ArrivalAirportID are
        Edm.String fields and MUST keep single quotes in OData filter.
        """
        filt = _build_filter(
            self.svc,
            AirlineID="BR",
            FlightNumber="001",
            DepartureAirportID="TPE",
            ArrivalAirportID="NRT",
        )
        assert "AirlineID eq 'BR'" in filt
        assert "FlightNumber eq '001'" in filt
        assert "DepartureAirportID eq 'TPE'" in filt
        assert "ArrivalAirportID eq 'NRT'" in filt

    def test_combined_filter_no_time_quotes(self):
        """Full realistic filter should contain no quoted time values."""
        filt = _build_filter(
            self.svc,
            DepartureAirportID="TPE",
            ArrivalAirportID="NRT",
            ScheduleStartDate="2026-05-03",
            ScheduleEndDate="2026-05-03",
            DepartureTime="09:30",
            ArrivalTime="14:00",
        )
        # time literals unquoted
        assert "'09:30'" not in filt, f"DepartureTime should be unquoted in: {filt!r}"
        assert "'14:00'" not in filt, f"ArrivalTime should be unquoted in: {filt!r}"
        # date literals unquoted
        assert "'2026-05-03'" not in filt, f"Dates should be unquoted in: {filt!r}"

    def test_none_values_omitted_from_filter(self):
        """Fields with None values must not appear in the filter at all."""
        filt = _build_filter(self.svc, DepartureAirportID="TPE", ArrivalAirportID="NRT")
        assert "ScheduleDepartureTime" not in filt
        assert "ScheduleArrivalTime" not in filt

    def test_empty_filter_when_no_fields(self):
        """A request with all-None fields should produce an empty filter string."""
        filt = _build_filter(self.svc)
        assert filt == ""
