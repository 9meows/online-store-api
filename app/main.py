from fastapi import FastAPI
from .routers import categories, products, users, reviews


app = FastAPI(title="Интернет-магазин", version="0.1.0")

app.include_router(categories.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(reviews.router)

@app.get("/")
async def root() -> dict:
    """
    Корневой маршрут, подтверждающий, что API работает.
    """
    return {"message": "Добро пожаловать в API интернет-магазина!"}