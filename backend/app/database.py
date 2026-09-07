from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured. Set it in backend/.env before starting the API.")

# ``host.docker.internal`` is available to containers, but it is not
# resolvable by a normal Windows Python process. Keep Docker configuration
# portable while allowing ``uvicorn`` to run directly on the host.
if not os.path.exists("/.dockerenv"):
    parsed_url = urlparse(DATABASE_URL)
    if parsed_url.hostname == "host.docker.internal":
        DATABASE_URL = urlunparse(parsed_url._replace(netloc=parsed_url.netloc.replace("host.docker.internal", "localhost", 1)))

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
