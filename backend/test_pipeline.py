import os
from dotenv import load_dotenv
load_dotenv()

from chunker import chunk_all_files
from embedder import embed_chunks

# Simulate a small repo
test_files = {
    "auth.py": """
def login(username, password):
    user = db.query(User).filter_by(username=username).first()
    if not user or not check_password(password, user.password):
        raise Exception("Invalid credentials")
    token = generate_token(user.id)
    return {"token": token}

def logout(user_id):
    invalidate_token(user_id)
    return {"message": "Logged out"}

def register(username, password, email):
    existing = db.query(User).filter_by(username=username).first()
    if existing:
        raise Exception("User already exists")
    user = User(username=username, password=hash_password(password), email=email)
    db.add(user)
    db.commit()
    return user
""",
    "database.py": """
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
"""
}

print("Step 1: Chunking...")
chunks = chunk_all_files(test_files)
print(f"Created {len(chunks)} chunks")
for c in chunks:
    print(f"  - {c['metadata']['func_name']} in {c['metadata']['filepath']}")

print("\nStep 2: Embedding...")
embedded = embed_chunks(chunks)
print(f"Successfully embedded {len(embedded)} chunks")