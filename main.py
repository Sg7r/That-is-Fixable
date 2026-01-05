# main.py
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer
from sqladmin import Admin, ModelView
import shutil
import os

# DATABASE_URL = "sqlite+aiosqlite:///./db.sqlite3"  # для старта, потом легко заменить на Postgres

# -------------------- DB --------------------
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    image_path: Mapped[str] = mapped_column(String(255))

# -------------------- APP --------------------
app = FastAPI(title="Starter Site")

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "static/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------- ADMIN --------------------
class PhotoAdmin(ModelView, model=Photo):
    column_list = [Photo.id, Photo.title, Photo.image_path]
    form_columns = [Photo.title]

admin = Admin(app, engine)
admin.add_view(PhotoAdmin)

# -------------------- ROUTES --------------------
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def homepage(request: Request):
    async with SessionLocal() as session:
        result = await session.execute(Photo.__table__.select())
        photos = result.fetchall()

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "photos": photos},
    )

@app.post("/upload")
async def upload_photo(title: str = Form(...), file: UploadFile = Form(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    async with SessionLocal() as session:
        photo = Photo(title=title, image_path=f"/static/uploads/{file.filename}")
        session.add(photo)
        await session.commit()

    return {"status": "ok"}


@app.get("/commercial")
async def commercial(request: Request):
    return templates.TemplateResponse(
        "commercial.html",
        {"request": request},
    )


@app.get("/residential")
async def residential(request: Request):
    return templates.TemplateResponse(
        "residential.html",
        {"request": request},
    )
# -------------------- RUN --------------------
# uvicorn main:app --reload
