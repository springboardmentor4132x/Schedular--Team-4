# SocialPilot — Authentication & User Management Module

This is Dev Yadav's module for the SocialPilot Social Media Scheduler & Campaign
Management Platform (Infosys Springboard Internship).

## What's built (Milestone 1 — in progress)

- Professional FastAPI project structure (config / database / models / schemas / auth / services / routers)
- PostgreSQL connection via SQLAlchemy, configured through `.env`
- Alembic migrations initialized and wired to the models
- `User` model with role-based access control (admin, business_user, marketing_team, content_creator)
- Password hashing with bcrypt (passwords are never stored in plain text)
- JWT-based authentication (login issues a token, protected routes require it)
- Working, tested endpoints:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/users/profile` (JWT-protected)

Tested end-to-end: register → login → access protected profile → correctly
rejects requests with no token (401) and duplicate email registration (400).

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env with your real PostgreSQL DATABASE_URL and a strong SECRET_KEY

# create the first migration and apply it
alembic revision --autogenerate -m "create users table"
alembic upgrade head

uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000/docs for interactive Swagger UI to test the APIs.

## Still to do

- Update Profile / Change Password / Account Settings endpoints
- Team Management (create team, add member) endpoints
- GET /users (admin-only, role-checked) endpoint
- Role-based route protection (currently any logged-in user can hit
  protected routes — need a `require_role()` dependency)
- Push initial commit to the shared GitHub repo once it has its first commit
