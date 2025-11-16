from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_buyer
from app.db_depends import get_async_db
from app.models.cart_items import CartItem as CartItemModel
from app.models.orders import Order as OrderModel, OrderItem as OrderItemModel
from app.models.users import User as UserModel
from app.schemas import Order as OrderSchema, OrderList
from app.models.products import Product as ProductModel

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)



async def _load_order_with_items(session: AsyncSession, order_id: int, user_id: int) -> OrderModel | None:
    result = await session.scalars(
        select(OrderModel)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.product),
        )
        .where(OrderModel.id == order_id, OrderModel.user_id == user_id)
    )
    return result.first()

@router.post("/checkout", response_model=OrderSchema, status_code=status.HTTP_201_CREATED)
async def checkout_order(user_current: UserModel = Depends(get_current_buyer), session:AsyncSession = Depends(get_async_db)):
    """
    Создаёт заказ на основе текущей корзины пользователя.
    Сохраняет позиции заказа, вычитает остатки и очищает корзину.
    """
    query_cart_items = await session.scalars(select(CartItemModel).options(selectinload(CartItemModel.product))
                                             .where(CartItemModel.user_id == user_current.id).order_by(CartItemModel.id))
    cart_user = query_cart_items.all()
    if not cart_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    total_amount = Decimal("0")
    order = OrderModel(user_id = user_current.id)

    for item in cart_user:
        product = item.product

        if product is None or product.is_active == False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product {item.product_id} is unavailable")
        if product.stock < item.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Not enough stock for product {product.name}")
        if product.price is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product {product.name} has no price set")
        
        unit_price = product.price
        total_unit_price = unit_price * item.quantity
        total_amount += total_unit_price
        order_item = OrderItemModel(product_id = item.product_id, quantity = item.quantity,
                                    unit_price=unit_price, total_price=total_unit_price) 
        order.items.append(order_item)
        product.stock-=item.quantity
        if product.stock == 0:
            product.is_active = False

    order.total_amount = total_amount
    session.add(order)

    await session.flush()  
    created_order = await _load_order_with_items(session, order.id, user_current.id)
    if not created_order:
        raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to load created order",
    )
    await session.execute(delete(CartItemModel).where(CartItemModel.user_id == user_current.id))
    await session.commit()
    return created_order

@router.get("/", response_model=OrderList, status_code=status.HTTP_200_OK)
async def get_all_orders(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
                          current_user: UserModel = Depends(get_current_buyer), session: AsyncSession = Depends(get_async_db)):
    
    all_orders = await session.scalars(select(OrderModel).
                                       options(selectinload(OrderModel.items).selectinload(OrderItemModel.product)).
                                       where(OrderModel.user_id == current_user.id).order_by(OrderModel.created_at.desc()).
                                       offset((page - 1)*page_size).limit(page_size))
    orders = all_orders.all()
    list_order = OrderList(items=orders, total=len(orders), page=page, page_size=page_size)
    return list_order

@router.get("/{order_id}", response_model=OrderSchema, status_code=status.HTTP_200_OK)
async def get_order_by_id(order_id:int, current_user: UserModel = Depends(get_current_buyer),
                           session: AsyncSession = Depends(get_async_db)):
    
    order = await _load_order_with_items(session, order_id, current_user.id)
    if order is None or current_user.id != order.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order