# User Management System

## Overview

The User Management system (Epic wq5) adds multi-user support to vtt-transcribe with secure authentication, encrypted API key storage, and job history tracking.

## Features

### Authentication & Authorization
- **User Registration**: Create accounts with email and username
- **JWT-based Authentication**: OAuth2 password flow with secure token-based access
- **Password Security**: Bcrypt hashing for password storage
- **Role-based Access**: Support for regular users and superusers

### API Key Management
- **Encrypted Storage**: API keys encrypted using Fernet (symmetric encryption)
- **Multi-Service Support**: Store keys for OpenAI, HuggingFace, and other services
- **Key Metadata**: Track key names, creation dates, and last usage
- **Per-User Keys**: Each user manages their own API keys

### Job History
- **Transcript Storage**: All transcription results saved to database
- **Job Tracking**: Monitor status (pending, processing, completed, failed)
- **Detailed Metadata**: Language detection, translation, diarization flags
- **User Statistics**: Summary of job counts and success rates

## Database Schema

### Users Table
```sql
- id: Primary key
- email: Unique email address
- username: Unique username
- hashed_password: Bcrypt-hashed password
- is_active: Account status flag
- is_superuser: Admin privileges flag
- created_at: Account creation timestamp
- updated_at: Last modification timestamp
```

### API Keys Table
```sql
- id: Primary key
- user_id: Foreign key to users
- service: Service name (openai, huggingface, etc.)
- encrypted_key: Fernet-encrypted API key
- key_name: User-friendly key identifier
- created_at: Key creation timestamp
- last_used_at: Last usage timestamp
```

### Transcription Jobs Table
```sql
- id: Primary key
- job_id: UUID for job identification
- user_id: Foreign key to users
- filename: Original file name
- status: Job status (pending, processing, completed, failed)
- transcript: Transcribed text content
- error: Error message if failed
- detected_language: Language detected by Whisper
- translated_to: Target language if translated
- with_diarization: Whether diarization was applied
- created_at: Job start timestamp
- completed_at: Job completion timestamp
```

## API Endpoints

### Authentication
- `POST /auth/register` - Create new user account
- `POST /auth/token` - Login and receive JWT token
- `GET /auth/me` - Get current user information

### API Key Management
- `POST /api-keys/` - Create encrypted API key
- `GET /api-keys/` - List user's API keys
- `GET /api-keys/{key_id}` - Get specific API key details
- `DELETE /api-keys/{key_id}` - Delete API key

### Job History
- `GET /jobs/` - List user's transcription jobs (with filtering)
- `GET /jobs/{job_id}` - Get detailed job information
- `DELETE /jobs/{job_id}` - Delete job from history
- `GET /jobs/stats/summary` - Get user statistics

## Setup

### Environment Variables

Add to your `.env` file:

```bash
# Database (choose one)
DATABASE_URL=sqlite+aiosqlite:///./vtt_transcribe.db  # Development
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/vtt_transcribe  # Production

# Generate SECRET_KEY with:
# python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-secret-key-here

# JWT Configuration
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Generate ENCRYPTION_KEY with:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-encryption-key-here
```

### Database Initialization

**Option 1: Automatic (via API startup)**
```bash
# Database tables are created automatically when the API starts
uv run uvicorn vtt_transcribe.api.app:app
```

**Option 2: Manual (using script)**
```bash
uv run python scripts/init_db.py
```

### Install Dependencies

```bash
# Install with API and database support
uv sync --extra api

# Or update existing environment
uv pip install sqlalchemy[asyncio] asyncpg aiosqlite python-jose[cryptography] passlib[bcrypt] cryptography
```

## Usage Examples

### User Registration
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "secure_password"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=secure_password"

# Response: {"access_token": "eyJ...", "token_type": "bearer"}
```

### Create API Key
```bash
curl -X POST http://localhost:8000/api-keys/ \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "service": "openai",
    "key": "sk-...",
    "key_name": "My OpenAI Key"
  }'
```

### List Jobs
```bash
# All jobs
curl http://localhost:8000/jobs/ \
  -H "Authorization: Bearer eyJ..."

# Filter by status
curl http://localhost:8000/jobs/?status_filter=completed \
  -H "Authorization: Bearer eyJ..."
```

### Get Job Statistics
```bash
curl http://localhost:8000/jobs/stats/summary \
  -H "Authorization: Bearer eyJ..."
```

## Security Considerations

### Password Security
- Passwords are hashed using bcrypt with automatic salt generation
- Plaintext passwords are never stored in the database
- Password verification uses constant-time comparison

### API Key Encryption
- API keys are encrypted using Fernet (AES-128-CBC)
- Encryption key must be kept secure and backed up
- Changing ENCRYPTION_KEY will invalidate existing keys

### JWT Tokens
- Tokens expire after configured duration (default 30 minutes)
- SECRET_KEY must be kept secure and unique per deployment
- Tokens are stateless (no server-side session storage)

### Best Practices
1. Use strong, unique SECRET_KEY and ENCRYPTION_KEY
2. Never commit `.env` files to version control
3. Use PostgreSQL for production (better concurrency than SQLite)
4. Enable HTTPS in production
5. Implement rate limiting for authentication endpoints
6. Regularly rotate API keys
7. Monitor failed login attempts

## Database Migrations

For production use, consider using Alembic for schema migrations:

```bash
# Install Alembic
uv pip install alembic

# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add user management tables"

# Apply migration
alembic upgrade head
```

## Testing

Tests are located in `tests/test_api/`:
- `test_auth.py` - Authentication endpoints
- `test_api_keys.py` - API key management
- `test_jobs.py` - Job history endpoints

Run tests:
```bash
make test
```

## Architecture Notes

### Async Database Operations
- Uses SQLAlchemy 2.0+ with async support
- AsyncSession for all database operations
- Connection pooling configured for production use

### Dependency Injection
- FastAPI dependencies for authentication
- Database session lifecycle management
- Automatic cleanup of resources

### Error Handling
- HTTP 401 for authentication failures
- HTTP 403 for authorization failures
- HTTP 404 for missing resources
- Detailed error messages in development mode

## Future Enhancements

Potential improvements:
- Password reset flow (email-based)
- Two-factor authentication (TOTP)
- API rate limiting per user
- User quotas and billing
- Team/organization support
- SSO integration (OAuth2 providers)
- Audit logging
- Key rotation automation
