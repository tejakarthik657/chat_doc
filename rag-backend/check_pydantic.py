try:
    from pydantic import BaseModel, EmailStr, ValidationError
    print("Import successful")
except ImportError as e:
    print(f"Import failed: {e}")
    exit(1)

try:
    class User(BaseModel):
        email: EmailStr

    print("Model defined")
    u = User(email="test@example.com")
    print(f"Validation successful: {u}")
except Exception as e:
    print(f"Validation failed: {e}")
