from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_buyer
from app.db_depends import get_async_db
from app.models.cart_items import CartItem as CartItemModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.schemas import (
    Cart as CartSchema,
    CartItem as CartItemSchema,
    CartItemCreate,
    CartItemUpdate,
)


router = APIRouter(prefix="/cart", tags=["carts"])


async def _get_cart_item(
    session: AsyncSession, user_id: int, product_id: int
) -> CartItemModel | None:
    result = await session.scalars(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(
            CartItemModel.user_id == user_id,
            CartItemModel.product_id == product_id,
        )
    )
    return result.first()

async def _check_product_item(session: AsyncSession, product_id: int) -> ProductModel:

    check_stuck_product = await session.scalars(select(ProductModel).
                                                where(ProductModel.id == product_id,
                                                ProductModel.is_active == True))
    product = check_stuck_product.first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product



@router.get('/', response_model=CartSchema, status_code=status.HTTP_200_OK)
async def get_cart(current_user: UserModel =  Depends(get_current_buyer), session: AsyncSession = Depends(get_async_db)):
    
    stmt_check_cart = await session.scalars(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(
            CartItemModel.user_id == current_user.id,
        )
    )
    check_cart_user = stmt_check_cart.all()
    total_quantity = sum(elem.quantity for elem in check_cart_user)
    total_sum_elem = (Decimal(elem.quantity) * (elem.product.price if elem.product.price is not None else Decimal("0")) 
                 for elem in check_cart_user)
    total_sum = sum(total_sum_elem, Decimal("0"))
    
    return CartSchema(user_id=current_user.id, items=check_cart_user, total_quantity=total_quantity, total_price=total_sum)

@router.post("/items", response_model=CartItemSchema, status_code=status.HTTP_201_CREATED)
async def add_new_items(cart_item: CartItemCreate,current_user: UserModel =  Depends(get_current_buyer),
                         session: AsyncSession = Depends(get_async_db)):
    
    product = await _check_product_item(session=session, product_id=cart_item.product_id)
    cart_item_model = await _get_cart_item(session=session, user_id=current_user.id, product_id=cart_item.product_id)

    if cart_item_model:
        cart_item_model.quantity += cart_item.quantity
    else:
        new_cart_item = CartItemModel(user_id=current_user.id,
                                       product_id=cart_item.product_id,
                                       quantity=cart_item.quantity)
        session.add(new_cart_item)

    await session.commit()
    updated_item = await _get_cart_item(session=session, user_id=current_user.id, product_id=cart_item.product_id)
    return updated_item

@router.post("/items/{product_id}", response_model=CartItemSchema, status_code=status.HTTP_200_OK)
async def updated_item_cart(product_id: int, new_cart_item: CartItemUpdate, current_user: UserModel = Depends(get_current_buyer),
                             session: AsyncSession = Depends(get_async_db)):
    
    product = await _check_product_item(session=session, product_id=product_id)
    cart_item_model = await _get_cart_item(session=session, user_id=current_user.id, product_id=product_id)
    if cart_item_model:
        cart_item_model.quantity = new_cart_item.quantity
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This item not found in your cart")

    await session.commit()
    updated_item = await _get_cart_item(session=session, user_id=current_user.id, product_id=product_id)
    return updated_item

@router.delete("/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item_by_product_id(product_id: int,
                                     current_user: UserModel = Depends(get_current_buyer),
                                     session: AsyncSession = Depends(get_async_db)):
    
    product = await _check_product_item(session=session, product_id=product_id)
    cart_item_model = await _get_cart_item(session=session, user_id=current_user.id, product_id=product_id)
    if cart_item_model:
        await session.delete(cart_item_model)
        await session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This item not found in your cart")
    
@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_items(current_user: UserModel = Depends(get_current_buyer),
                            session: AsyncSession = Depends(get_async_db)):

    await session.execute(delete(CartItemModel).where(CartItemModel.user_id == current_user.id))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)