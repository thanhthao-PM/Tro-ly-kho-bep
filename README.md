# Kitchen Assistant (Trợ lý kho bếp) — Mobile Web

Status: see BUILD_STATUS.md. Specs gaps: PHASE2_READINESS.md.

## 1. Environment files (new machine)
Real files are git-ignored; never commit them or paste secrets in chat.
```powershell
cd "D:\Kitchen Assistant"
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
```
Edit `backend\.env`: DATABASE_URL (pooler port 6543), MIGRATION_DATABASE_URL (port 5432), SUPABASE_URL, JWT_MODE=auto, SUPABASE_JWT_SECRET (only needed if tokens are HS256).
Edit `frontend\.env.local`: VITE_API_BASE_URL, VITE_SUPABASE_URL, VITE_SUPABASE_PUBLISHABLE_KEY. Never put `sb_secret_...` or the JWT secret in the frontend.

## 2. Backend
```powershell
cd "D:\Kitchen Assistant"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
cd backend
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload --port 8000
```
Check: http://localhost:8000/health, /health/db, /docs.

## 3. Frontend (second window)
```powershell
cd "D:\Kitchen Assistant\frontend"
npm install
npm run build
npm run dev
```
Open http://localhost:5173, log in with a Supabase user; success text: "Đã xác thực với backend".

## 4. Migrations (Alembic 0001-0011)
Never run on the real project before reviewing the SQL. Needs `MIGRATION_DATABASE_URL` (port 5432).
```powershell
cd "D:\Kitchen Assistant\backend"
alembic upgrade head --sql > ..\migration_preview.sql    # prints SQL only, does not connect or change anything
```
Review `migration_preview.sql`. Apply first to a scratch database (a new empty Supabase project, or local PostgreSQL 15+), then:
```powershell
alembic upgrade head
$env:TEST_DATABASE_URL = "postgresql://...scratch db, port 5432..."
python -m pytest tests\db -q        # each test rolls back; do not point at real data
```
Never run Alembic on port 6543 and never at app startup. Downgrades exist for development only.

## 5. Demo data and the main flow
Create (or reuse) a Supabase Auth user, copy its UUID, then:
```powershell
cd "D:\Kitchen Assistant\backend"
python -m app.scripts.seed_demo --user-id <SUPABASE_USER_UUID>
```
The kitchen is named "DEMO - dữ liệu mẫu" so sample data is never mistaken for real operations. It only inserts; running it twice changes nothing.
In the app: Kho (nhập kho, xem lô, xử lý/bỏ) -> Bán hàng (ghi nhận bán, thiếu hụt, thực đơn) -> Báo cáo (R1, gợi ý nhập hàng) -> Trợ lý AI.
API docs: http://localhost:8000/docs (all business routes need the Bearer token).

## 6. Tests
```powershell
cd "D:\Kitchen Assistant\backend"
python -m pytest -q                                   # no database needed (db tests skip)
$env:TEST_DATABASE_URL = "postgresql://...SCRATCH database, migrated..."
python -m pytest tests\db -q                          # rolls back; never use the real project
```

## What is not built
Suppliers/purchase orders, user roles, OCR, adjustments, COOK, estimate write-offs, notifications, CSV import, external LLM (no spec, Stretch or Deferred in Revision 6.3). See PHASE2_READINESS.md.

## Troubleshooting
- 401 ALGORITHM_NOT_ALLOWED / INVALID_TOKEN: `python scripts\diagnose_jwt.py you@example.com` (prints no token).
- `prepared statement ... does not exist`: DATABASE_URL must use port 6543.
- CORS error: add the frontend origin to CORS_ORIGINS.
