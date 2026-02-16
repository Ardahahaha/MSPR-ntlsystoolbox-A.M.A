cat > src/ntlsystoolbox/__main__.py <<'PY'
from ntlsystoolbox.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
PY
