from pathlib import Path

path = Path("src/nfldb/api/main.py")
text = path.read_text(encoding="utf-8")
text = text.replace("from typing import Generator, List, Optional\n\nfrom fastapi import Depends, FastAPI, Query\nfrom fastapi.middleware.cors import CORSMiddleware\nfrom sqlalchemy =", "from typing import Generator, List, Optional\n\nfrom fastapi import Depends, FastAPI, Query\nfrom fastapi.middleware.cors import CORSMiddleware\nfrom pydantic import BaseModel\nfrom sqlalchemy")
if "BaseModel" not in text:
    raise SystemExit("substitution failed")
path.write_text(text, encoding="utf-8")
