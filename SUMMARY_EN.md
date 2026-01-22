# Executive Summary - NTL-SysToolbox

## Overview
NTL-SysToolbox is a specialized 100% Python-based suite designed for network diagnostics, WMS database backups, and software obsolescence auditing. It is purpose-built for critical infrastructure environments where external binary tools (like `nmap`, `mysqldump`, or `curl`) are restricted.

## Key Modules

### 1. Diagnostic Module
Automates connectivity and service health checks for Active Directory, DNS, and MySQL databases. It ensures that the core infrastructure is reachable and performing within expected latency parameters.

### 2. WMS Backup Module
Provides native Python implementation for logical SQL dumps and CSV exports. It enables full database backups and targeted data extraction without requiring MySQL client binaries on the host system.

### 3. Obsolescence Audit Module
Performs non-intrusive network scans to inventory assets and determine their Operating System. It integrates with the `endoflife.date` API to identify End-of-Life (EOL) risks, generating visual HTML reports for stakeholders.

## Strategic Advantages
- **No External Dependencies**: Pure Python implementation ensures high portability across Windows and Linux.
- **Traceability**: Every action generates time-stamped JSON reports and standardized exit codes (0-4) for integration with monitoring systems (Zabbix, Nagios).
- **Security-First**: Uses environment variable overrides for secrets and follows secure input handling practices.
- **Modern UI**: Interactive CLI using `questionary` and `rich` for a superior operator experience.
