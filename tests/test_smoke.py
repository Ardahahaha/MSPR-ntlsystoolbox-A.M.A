from __future__ import annotations

import os
from pathlib import Path

import pytest

import ntlsystoolbox.main as mainmod
from ntlsystoolbox.core.reporting import save_json_report
from ntlsystoolbox.core.result import ModuleResult, status_to_exit_code
from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule, EOLMeta


def _prep_tmp_workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    os.makedirs("reports/json", exist_ok=True)
    os.makedirs("reports/audit", exist_ok=True)


def test_exit_codes_mapping():
    assert status_to_exit_code("SUCCESS") == 0
    assert status_to_exit_code("WARNING") == 1
    assert status_to_exit_code("ERROR") == 2
    assert status_to_exit_code("UNKNOWN") == 3
    assert status_to_exit_code("random") == 3


def test_save_json_report_creates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _prep_tmp_workdir(tmp_path, monkeypatch)

    r = ModuleResult(module="diagnostic", status="SUCCESS", summary="ok").finish()
    out = save_json_report(r, out_dir="reports/json")

    p = Path(out)
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert '"module": "diagnostic"' in content
    assert '"exit_code": 0' in content


def test_audit_run_action_scan_range(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _prep_tmp_workdir(tmp_path, monkeypatch)

    mod = AuditObsolescenceModule(config={})

    def fake_scan(cidr: str):
        inv = [{"ip": "192.168.10.21", "open_ports": [22, 3306], "os_guess": "linux"}]
        stats = {"cidr": cidr, "found_hosts": 1, "ports_checked": [22], "timeout_s": 0.1, "workers": 1}
        return inv, stats

    monkeypatch.setattr(mod, "_scan_range", fake_scan)

    r = mod.run_action("scan_range", cidr="192.168.10.0/24")
    assert r.status in ("SUCCESS", "WARNING")
    assert "inventory_json" in (r.artifacts or {})
    assert Path(r.artifacts["inventory_json"]).exists()


def test_audit_run_action_list_versions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _prep_tmp_workdir(tmp_path, monkeypatch)

    mod = AuditObsolescenceModule(config={})

    def fake_list(product: str):
        rows = [
            {"cycle": "3.8", "latest": "3.8.18", "eol": "2024-10-01"},
            {"cycle": "3.12", "latest": "3.12.1", "eol": "2030-10-01"},
        ]
        meta = EOLMeta(source="endoflife.date", fetched_at_iso="2026-02-12T12:00:00", api_mode="v0")
        return rows, meta

    monkeypatch.setattr(mod, "_list_versions_eol", fake_list)

    r = mod.run_action("list_versions_eol", product="python")
    assert r.status in ("SUCCESS", "WARNING")
    assert r.details["product"] == "python"
    assert isinstance(r.details.get("rows", []), list)


def test_audit_run_action_csv_to_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _prep_tmp_workdir(tmp_path, monkeypatch)

    os.makedirs("inputs", exist_ok=True)
    Path("inputs/components.csv").write_text(
        "name,product,version\nWMS-DB,mysql,5.7\nWMS-APP,python,3.8\n",
        encoding="utf-8",
    )

    mod = AuditObsolescenceModule(config={})

    def fake_list(product: str):
        if product == "mysql":
            rows = [{"cycle": "5.7", "latest": "5.7.44", "eol": "2023-10-21"}]
        else:
            rows = [{"cycle": "3.8", "latest": "3.8.18", "eol": "2024-10-01"}]
        meta = EOLMeta(source="endoflife.date", fetched_at_iso="2026-02-12T12:00:00", api_mode="v0")
        return rows, meta

    monkeypatch.setattr(mod, "_list_versions_eol", fake_list)

    r = mod.run_action("csv_to_report", csv_path="inputs/components.csv", do_scan=False, cidr=None)
    assert r.status in ("SUCCESS", "WARNING")
    assert "audit_report_html" in (r.artifacts or {})
    assert Path(r.artifacts["audit_report_html"]).exists()


def test_cli_main_exit_codes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _prep_tmp_workdir(tmp_path, monkeypatch)

    class FakeDiag:
        def __init__(self, config):
            pass

        def run(self):
            return ModuleResult(module="diagnostic", status="SUCCESS", summary="ok").finish()

    class FakeBackup:
        def __init__(self, config):
            pass

        def run(self):
            return ModuleResult(module="backup_wms", status="ERROR", summary="db down").finish()

    class FakeAudit:
        def __init__(self, config):
            pass

        def run_action(self, action: str, **kwargs):
            return ModuleResult(module="obsolescence", status="SUCCESS", summary=action, details=kwargs).finish()

    monkeypatch.setattr(mainmod, "DiagnosticModule", FakeDiag)
    monkeypatch.setattr(mainmod, "BackupWMSModule", FakeBackup)
    monkeypatch.setattr(mainmod, "AuditObsolescenceModule", FakeAudit)

    code = mainmod.cli_main(["diagnostic", "--dc01", "1.1.1.1"])
    assert code == 0

    code = mainmod.cli_main(["backup", "--host", "1.1.1.1"])
    assert code == 2

    code = mainmod.cli_main(["audit", "scan", "--cidr", "192.168.0.0/24"])
    assert code == 0
