# Agri-CPQ MVP (FastAPI + MongoDB)

This is a starter scaffold for the **Agri-CPQ** project (Configure-Price-Quote for agriculture).
It provides a minimal FastAPI backend with MongoDB as the database.

## Features included
- User registration (farmer/buyer)
- Add crops with base price and season
- Add discount rules per crop
- Calculate quotes (apply discount tiers)
- Save & list quotes
- Simple HTML quote export (PDF generation via WeasyPrint optional)

## Quick start (local)
1. Install dependencies (preferably in a virtualenv):
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and update `MONGODB_URI` if needed.
3. Run the app:
   ```bash
   uvicorn main:app --reload
   ```
4. API docs: http://127.0.0.1:8000/docs

## Project structure
- `main.py` - FastAPI app and routes
- `db.py` - MongoDB connection helper
- `models.py` - Pydantic request/response models
- `utils.py` - CPQ calculation logic & helpers
- `templates/quote.html` - HTML template for PDF quote

You can extend the scaffold: add auth, frontend, payments, region logic, etc.