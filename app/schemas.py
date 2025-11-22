from decimal import Decimal
from typing import Annotated
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from fastapi import Form

class CategoryCreate(BaseModel):
    """
    Модель для создания и обновления категории.
    Используется в POST и PUT запросах.
    """
    name: Annotated[str, Field(min_length=3, max_length=50,
                      description="Название категории (3-50 символов)")]
    parent_id: Annotated[int | None, Field(None, description="ID родительской категории, если есть")]


class Category(BaseModel):
    """
    Модель для ответа с данными категории.
    Используется в GET-запросах.
    """
    id: Annotated[int, Field(description="Уникальный идентификатор категории")]
    name: Annotated[str, Field(description="Название категории")]
    parent_id: Annotated[int | None, Field(None, description="ID родительской категории, если есть")]
    is_active: Annotated[bool, Field(description="Активность категории")]

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """
    Модель для создания и обновления товара.
    Используется в POST и PUT запросах.
    """
    name:Annotated[str, Field(min_length=3, max_length=100,
                      description="Название товара (3-100 символов)")]
    description: Annotated[str | None, Field(None, max_length=500,
                                       description="Описание товара (до 500 символов)")]
    price: Annotated[Decimal, Field(gt=0, description="Цена товара (больше 0)", decimal_places=2)]
    stock: Annotated[int, Field(ge=0, description="Количество товара на складе (0 или больше)")]
    category_id: Annotated[int, Field(description="ID категории, к которой относится товар")]

    @classmethod
    def as_form(
            cls,
            name: Annotated[str, Form(...)],
            price: Annotated[Decimal, Form(...)],
            stock: Annotated[int, Form(...)],
            category_id: Annotated[int, Form(...)],
            description: Annotated[str | None, Form()] = None,
    ) -> "ProductCreate":
        return cls(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
        )

class Product(BaseModel):
    """
    Модель для ответа с данными товара.
    Используется в GET-запросах.
    """
    id: Annotated[int, Field(description="Уникальный идентификатор товара")]
    name: Annotated[str, Field(description="Название товара")]
    description: Annotated[str | None, Field(None, description="Описание товара")]
    price: Annotated[Decimal, Field(description="Цена товара в рублях", gt=0, decimal_places=2)]
    image_url: Annotated[str | None, Field(None, description="URL изображения товара")]
    stock: Annotated[int, Field(description="Количество товара на складе")]
    category_id: Annotated[int, Field(description="ID категории")]
    rating: Annotated[float, Field(description="Рейтинг товара", ge=0, le=5)]
    is_active: Annotated[bool, Field(description="Активность товара")]
    
    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    """
    Модель для создания и обновления пользователя.
    Используется в POST и PUT запросах.
    """
    email: Annotated[EmailStr, Field(description="Email пользователя")]
    password: Annotated[str, Field(min_length=8, description="Пароль (минимум 8 символов)")]
    role: Annotated[str, Field(default="buyer", pattern="^(buyer|seller)$", description="Роль: 'buyer', 'seller'")]

class User(BaseModel):
    """
    Модель для ответа с данными пользователя.
    """
    id: Annotated[int, Field(description="Уникальный идентификатор пользователя")]
    email: Annotated[EmailStr, Field(description="Email пользователя")]
    is_active: Annotated[bool, Field(description="Активность пользователя")]
    role: Annotated[str, Field(description="Роль пользователя")]

    model_config = ConfigDict(from_attributes=True)

class ReviewCreate(BaseModel):
    """
    Модель для создания и обновления отзыва.
    Используется в POST и PUT запросах.
    """
    product_id: Annotated[int, Field("ID продукта, к которому относится к отзыв")]
    comment: Annotated[str, Field(description="Комментарий пользователя")]
    grade: Annotated[int, Field(description="Оценка пользователя", ge=1, le=5)]


class Review(BaseModel):
    """
    Модель для ответа с данными отзыва.
    Используется в GET-запросах.
    """
    id: Annotated[int, Field(description="Уникальный идентификатор отзыва")]
    user_id: Annotated[int, Field(description="ID пользователя, к которому относится к отзыв")]
    product_id: Annotated[int, Field(description="ID продукта, к которому относится к отзыв")]
    comment: Annotated[str, Field(description="Комментарий пользователя")]
    comment_date: Annotated[datetime, Field(description="Дата комментария")]
    grade: Annotated[int, Field(description="Оценка пользователя", ge=1, le=5)]
    is_active: Annotated[bool, Field(description="Активность отзыва")]


class ProductList(BaseModel):
    """
    Модель пагинации для товаров 
    """
    page: Annotated[int, Field(ge=1, description="Номер текущей страницы")]
    page_items: Annotated[list[Product], Field(description="Товары для текущей страницы")]
    total_items:Annotated[int, Field(ge=0, description="Общее количество товаров")]
    page_size: Annotated[int, Field(ge=1, description="Количество товаров на одной странице")]

    model_config = ConfigDict(from_attributes=True)


class CartItemBase(BaseModel):
    product_id: Annotated[int, Field(description="ID товара")]
    quantity: Annotated[int, Field(ge=1, description="Количество товара")]

class CartItemCreate(CartItemBase):
    """Модель для добавления нового товара в корзину."""
    pass

class CartItemUpdate(BaseModel):
    """Модель для обновления количества товара в корзине."""
    quantity: int = Field(ge=1, description="Новое количество товара")    

class CartItem(BaseModel):
    """Товар в корзине с данными продукта."""
    id: Annotated[int, Field(description="ID позиции корзины")]
    quantity: Annotated[int, Field(ge=1, description="Количество товара")]
    product: Annotated[Product, Field(description="Характеристики товара")]

    model_config = ConfigDict(from_attributes=True)

class Cart(BaseModel):
    """Полная информация о корзине пользователя."""
    user_id: Annotated[int, Field(description="ID пользователя")]
    items: Annotated[list[CartItem], Field(default_factory=list, description="Корзина пользователя")]
    total_quantity: Annotated[int, Field(ge=0, description="Общее количество товаров")]
    total_price: Annotated[Decimal, Field(ge=0, description="Общая сумма товаров")]

    model_config = ConfigDict(from_attributes=True)

class OrderItem(BaseModel):
    """
    Модель описывает одну строку заказа.
    Используется в ответах API.
    """
    id: Annotated[int, Field(description="ID позиции заказа")]
    product_id: Annotated[int, Field(description="ID товара")]
    quantity: Annotated[int, Field(ge=1, description="Количество")]
    unit_price: Annotated[Decimal, Field(ge=0, description="Цена за единицу на момент покупки")]
    total_price: Annotated[Decimal, Field(ge=0, description="Сумма по позиции")]
    product: Annotated[Product | None, Field(default=None, description="Полная информация о товаре")]

    model_config = ConfigDict(from_attributes=True)

class Order(BaseModel):
    """
    Модель даёт полное представление о заказе.
    Используется в ответах API.
    """
    id: Annotated[int, Field(description="ID заказа")]
    user_id: Annotated[int, Field(description="ID пользователя")]
    status: Annotated[str, Field(description="Текущий статус заказа")]
    total_amount: Annotated[Decimal, Field(ge=0, description="Общая стоимость")]
    created_at: Annotated[datetime, Field(description="Когда заказ был создан")]
    updated_at: Annotated[datetime, Field(description="Когда последний раз обновлялся")]
    items: Annotated[list[OrderItem], Field(default_factory=list, description="Список позиций")]

    model_config = ConfigDict(from_attributes=True)

class OrderList(BaseModel):
    """
    Модель обёртка для пагинированных списков заказов.
    """
    items: Annotated[list[Order], Field(description="Заказы на текущей странице")]
    total: Annotated[int, Field(ge=0, description="Общее количество заказов")]
    page: Annotated[int, Field(ge=1, description="Текущая страница")]
    page_size: Annotated[int, Field(ge=1, description="Размер страницы")]

    model_config = ConfigDict(from_attributes=True)

class OrderCheckoutResponse(BaseModel):
    """
    Модель для отправки данных клиенту от YooKassa
    """
    order: Annotated[Order, Field(description="Созданный заказ")]
    confirmation_url: Annotated[str | None, Field(default=None, description="URL для перехода на оплату в YooKassa")]