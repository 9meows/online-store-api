from typing import Annotated
from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.auth import get_current_seller
from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.models.products import Product as ProductModel
from app.schemas import Product, ProductCreate, ProductList
from app.models.categories import Category as CategoryModel


# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=ProductList, status_code=status.HTTP_200_OK)
async def get_all_products(page: int = Query(1, ge=1, le=30),
                            page_size: int = Query(20, ge=1, le=100),
                            category_id: int | None = Query(None, description="ID категории для фильтрации"),
                            search: str | None = Query(None, min_length=1, description="Поиск по названию товара"),
                            min_price: float | None = Query(None, ge=0, description="Минимальная цена товара"),
                            max_price: float | None = Query(None, ge=0, description="Максимальная цена товара"),
                            in_stock: bool | None = Query(None, description="true — только товары в наличии, false — только без остатка"),
                            seller_id: int | None = Query(None, description="ID продавца для фильтрации"),
                           session: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех активных товаров с поддержкой фильтров.
    """
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="min_price не может быть больше max_price")
    
    filters = [ProductModel.is_active == True]

    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    if in_stock is not None:
        filters.append(ProductModel.stock >= 0 if in_stock else ProductModel.stock == 0)
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)


    total_stmt = select(func.count()).select_from(ProductModel).where(*filters)

    rank_col = None
    if search:
        search_value = search.strip().lower()
        if search_value:
            ts_query = func.websearch_to_tsquery('english', search_value)
            filters.append(ProductModel.tsv.op('@@')(ts_query))
            rank_col = func.ts_rank_cd(ProductModel.tsv, ts_query).label('rank')
            total_stmt = select(func.count()).select_from(ProductModel).where(*filters)

    total = await session.scalar(total_stmt) or 0

    if rank_col is not None:
        product_stmt = (select(ProductModel, rank_col).
                        where(*filters).
                        order_by(desc(rank_col), ProductModel.id)).offset((page - 1)*page_size).limit(page_size)
        result = await session.execute(product_stmt)
        rows = result.all()
        items = [row[0] for row in rows]
    else:
        products_stmt = (
            select(ProductModel)
            .where(*filters)
            .order_by(ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await session.scalars(products_stmt)).all()

    response = ProductList(page=page, page_items=items, total_items=total, page_size=page_size)
    return response

@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Создаёт новый товар, привязанный к текущему продавцу (только для 'seller').
    """
    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id, CategoryModel.is_active == True)
    )
    
    if not category_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found or inactive")
    db_product = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)  # Для получения id и is_active из базы
    return db_product


@router.get("/category/{category_id}", response_model=list[Product], status_code=status.HTTP_200_OK)
async def get_products_by_category(category_id: int, session: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    query_category = await session.scalars(select(CategoryModel).where(CategoryModel.id == category_id,
                                                                        CategoryModel.is_active == True))
    result_query = query_category.first()
    if result_query is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")
    query_products = await session.scalars(select(ProductModel).where(ProductModel.category_id == category_id, ProductModel.is_active == True))

    return query_products.all()



@router.get("/{product_id}", response_model=Product, status_code=status.HTTP_200_OK)
async def get_product(product_id: int, session: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    query = await session.scalars(select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True))
    result_query = query.first()
    if result_query is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not found")
    
    query_check_categories = await session.scalars(select(CategoryModel).where(result_query.category_id == CategoryModel.id,
                                                                                CategoryModel.is_active == True))
    result_query_categories = query_check_categories.first()
    if result_query_categories is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    return result_query


@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: int,
    product: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Обновляет товар, если он принадлежит текущему продавцу (только для 'seller').
    """
    result = await db.scalars(select(ProductModel).where(ProductModel.id == product_id))
    db_product = result.first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if db_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")
    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id, CategoryModel.is_active == True)
    )

    if not category_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found or inactive")
    await db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(**product.model_dump())
    )

    await db.commit()
    await db.refresh(db_product)  # Для консистентности данных
    return db_product


@router.delete("/{product_id}", response_model=Product, status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Выполняет мягкое удаление товара, если он принадлежит текущему продавцу (только для 'seller').
    """
    result = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    product = result.first()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own products")
    
    await db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(is_active=False)
    )
    await db.commit()
    await db.refresh(product)  # Для возврата is_active = False
    return product

