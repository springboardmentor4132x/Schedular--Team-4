# Social Media Scheduler & Campaign Management Platform


# SocialPilot Backend

## Member 5 – Database, Backend Integration, API Testing & Deployment

### Completed Work

This branch contains the backend implementation for the SocialPilot project using FastAPI and PostgreSQL.

### Features Implemented

- User Registration API
- User Login API with JWT Authentication
- Protected `/me` endpoint
- Password hashing using bcrypt
- PostgreSQL database integration with SQLAlchemy
- User database schema
- FastAPI backend structure
- Swagger API documentation
- API testing using Swagger UI

### Technologies Used

- FastAPI
- PostgreSQL
- SQLAlchemy
- JWT Authentication
- Passlib (bcrypt)
- Pydantic
- Uvicorn

### API Endpoints

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/users/auth/register` | Register a new user |
| POST | `/api/v1/users/auth/login` | User login and JWT generation |
| GET | `/api/v1/users/auth/me` | Get authenticated user details |

### Authentication

- JWT-based authentication
- Passwords stored securely using bcrypt hashing
- Protected routes using OAuth2PasswordBearer

### Status

✅ Database Schema Completed

✅ Backend Integration Completed

✅ Authentication Completed

✅ API Testing Completed

🔄 Deployment (Next Phase)

### Branch

`Alvin-jose_Database_Api_testing`

---

**Developer:** Alvin Jose