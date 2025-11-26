from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .celery_app import celery_app
from .routers import categories, products, users, reviews, cart, orders, payments
from app.log import log_middleware

app = FastAPI(title="Интернет-магазин", version="0.1.0")

app.mount("/media", StaticFiles(directory="media"), name="media")
app.middleware("http")(log_middleware)

app.include_router(cart.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(reviews.router)
app.include_router(orders.router)
app.include_router(payments.router)

@app.get("/")
async def root() -> dict:
    """
    Корневой маршрут, подтверждающий, что API работает.
    """
    return {"message": "Добро пожаловать в API интернет-магазина!"}