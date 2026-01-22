# Ambiguities and Decisions

## Output JSON Structure
Since the specification did not define the exact JSON structure, the following schema is adopted:
```json
{
  "metadata": {
    "module": "string",
    "timestamp": "ISO8601 string",
    "status": "string (SUCCESS|WARNING|CRITICAL|ERROR|UNKNOWN)",
    "exit_code": "integer"
  },
  "data": {
    "key": "value"
  }
}
```

## Exit Codes Mapping
Standardized exit codes for supervision integration:
- `0 (SUCCESS)`: Everything is operational.
- `1 (WARNING)`: Minor issues detected but system is functional.
- `2 (CRITICAL)`: Major failure or critical service down.
- `3 (ERROR)`: Script/Module failed to execute (e.g., connection error).
- `4 (UNKNOWN)`: State cannot be determined.

## Configuration Loading Order
1. Default values in code.
2. `config/config.yml` (or path in `NTL_CONFIG_PATH`).
3. `.env` file.
4. Environment variables (prefixed with `NTL_`).

## Diagnostic Module Details
- **AD/DNS Verification**: Port checks on 53 (DNS), 389 (LDAP), and 636 (LDAPS) are used as a baseline for service availability. A basic LDAP bind test is performed if port 389 is open.
- **Hardware Metrics**: 
  - CPU: Load percentage.
  - RAM: Format "Used/TotalMB".
  - Disk: Percentage used on the system drive (`C:` for Windows, `/` for Ubuntu).
  - **Remote Access**: Windows diagnostics require WinRM (HTTP/HTTPS) to be enabled on the target. Ubuntu diagnostics require SSH.
  
  ## Backup WMS Module Details
  - **SQL Dump**: Implemented using pure Python (`pymysql`). It performs `SHOW CREATE TABLE` for structure and `SELECT *` for data. 
    - *Limitation*: This is a basic logical dump. It may be slower than `mysqldump` for very large databases and does not handle advanced features like triggers or routines unless explicitly added.
    - *Data Handling*: Basic escaping of single quotes and handling of `NULL` values.
    - **CSV Export**: Uses the standard `csv` module with a semicolon (`;`) delimiter as it is the standard for European/French Excel compatibility.
    - **Storage**: Artifacts (.sql, .csv) are stored in `outputs/backups/` by default, while reports remain in `outputs/reports/`.

## Audit Obsolescence Module Details
- **Network Scan Heuristic**: Since no external binaries (nmap) are allowed, the tool uses standard Python `socket` for TCP port scanning. 
    - *Discovery*: IPs are considered "Up" if at least one common port (22, 135, 445, 80, 443) responds.
    - *OS Detection*: Very basic heuristic (135/445 -> Windows, 22 -> Linux). Precise detection is impossible without credentialed access or deep packet inspection (prohibited).
- **EOL Data Source**: Uses the `endoflife.date` API via standard `urllib.request`.
- **EOL Threshold**: "Soon EOL" is defined as **180 days (6 months)** before the official end-of-life date.
- **Ambiguities**: Scan-based OS detection is documented as "Best Effort". For accurate EOL auditing, the CSV input mode (providing product name and version) is highly recommended.


