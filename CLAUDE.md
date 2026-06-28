# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run dev server (reload on change)
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev       # Dev server at http://localhost:5173
npm run build     # Production build to frontend/dist/
```

## Architecture

**Backend** (`backend/app/`): FastAPI app with CORS configured for the Vite dev server (`localhost:5173`). Routes live in `app/routes/` and are registered in `main.py` under the `/api` prefix.

**Frontend** (`frontend/src/`): React + Vite. The Vite dev server proxies all `/api` requests to `localhost:8000`, so no hardcoded API URLs are needed in client code.

**Domain model** (planned): salary, expenses, debts (student loans), savings, pension contributions — modelled in `backend/app/routes/finance.py` via Pydantic schemas.
