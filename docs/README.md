# Kitchen Assistant (Trợ lý kho bếp)

Status: Phase 1 foundation only. See BUILD_STATUS.md.

## Setup (Windows PowerShell, project at D:\Kitchen Assistant)
```powershell
cd "D:\Kitchen Assistant"
Copy-Item .env.example backend\.env        # then edit backend\.env
Copy-Item .env.example frontend\.env.local # keep only the VITE_* lines
```
Fill: DATABASE_URL (port 6543), MIGRATION_DATABASE_URL (port 5432), SUPABASE_URL, JWT_MODE (+ SUPABASE_JWT_SECRET if hs256), VITE_* values.

## Verify Phase 1
Backend:
```powershell
cd "D:\Kitchen Assistant\backend"
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/health and http://localhost:8000/health/db, docs at /docs.

Frontend (new PowerShell window):
```powershell
cd "D:\Kitchen Assistant\frontend"
npm install
npm run build
npm run dev
```
Open http://localhost:5173, log in with the Supabase test account; you should see "Đã xác thực với backend".

## Troubleshooting
- `prepared statement ... does not exist`: DATABASE_URL must use port 6543 and the code already sets prepare_threshold=None.
- 401 INVALID_TOKEN after login: JWT_MODE does not match the project signing method (item U12).
- CORS error: add the frontend origin to CORS_ORIGINS.
- Never run Alembic on port 6543.
