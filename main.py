# main.py
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer
from sqladmin import Admin, ModelView
import httpx
import shutil
import os

DATABASE_URL = "sqlite+aiosqlite:///./db.sqlite3"  # для старта, потом легко заменить на Postgres
GEOAPIFY_KEY = "77753fef68564b96b586582efdf692f7"
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


# -------------------- SCHEDULE ENDPOINTS --------------------


@app.get("/api/times")
def get_times():
    return JSONResponse([
        "08:00 AM",
        "09:00 AM",
        "10:00 AM",
        "11:00 AM",
        "12:00 PM",
        "01:00 PM",
        "02:00 PM",
        "03:00 PM",
        "04:00 PM",
        "05:00 PM",
        
    ])


@app.get("/api/days")
def get_days():
    return JSONResponse([
        "Monday",
        "Tuesdat",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        
    ])

@app.get("/api/applianceTypes")
def get_applianceTypes():
    return JSONResponse([
        "Refrigerator",
        "Oven/Range",
        "Dryer",
        "Washer",
        "Microwave",
        "Dishwasher",
        "Water heater",
        "Window AC",
        
    ])

@app.post("/schedule")
def schedule(
    day: str = Form(...),
    time: str = Form(...),
    applianceType: str = Form(...),
    description: str = Form(...),
    address: str = Form(...),
    phone: str = Form(...)
):
    print(day, time, applianceType, description, address, phone)
    return {
        "status": "ok",
        "day": day,
        "time": time,
        "appliance": applianceType,
        "description": description,
        "address": address,
        "phone": phone
    }

@app.get("/api/address-search")
async def address_search(q: str):
    if len(q) < 3:
        return []

    url = "https://api.geoapify.com/v1/geocode/autocomplete"

    params = {
        "text": q,
        "filter": "countrycode:us",
        "limit": 5,
        "apiKey": GEOAPIFY_KEY
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(2)
        ) as client:
            
            r = await client.get(url, params=params)

            r.raise_for_status()

            data = r.json()



            # 👇 Ловим ВСЕ сетевые ошибки
    except httpx.HTTPError as e:
        print("HTTP error:", e)
        return []

    # 👇 Ловим любые другие ошибки
    except Exception as e:
        print("Unexpected error:", e)
        return []

    results = []

        
    for item in data.get("features", []):
        props = item["properties"]

        if props.get("country_code") != "us":
            continue
        
        results.append({
            "formatted": props.get("formatted", ""),
            "street": props.get("street", ""),
            "city": props.get("city", ""),
            "state": props.get("state", ""),
            "postcode": props.get("postcode", "")
        })

    return results


# -------------------- RUN --------------------
# uvicorn main:app --reload
