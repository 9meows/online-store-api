import jwt

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status

from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.models import Product as ProductModel
from app.models.reviews import Review as ReviewModel
from app.auth import get_current_buyer, get_current_admin
from app.schemas import Review as ReviewResponse, ReviewCreate as ReviewRequest

router = APIRouter(tags=["reviews"])


@router.get("/reviews/", response_model=list[ReviewResponse], status_code=status.HTTP_200_OK)
async def get_all_reviews(session: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех отзывов.
    """
    stmt = await session.scalars(select(ReviewModel).where(ReviewModel.is_active == True))
    all_reviews = stmt.all()
    return all_reviews

@router.get("/products/{product_id}/reviews/", response_model=list[ReviewResponse], status_code=status.HTTP_200_OK)
async def get_reviews_by_id_product(product_id: int, session: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список отзывов по продукт ID.
    """
    stmt = await session.scalars(select(ReviewModel).where(ReviewModel.is_active == True, 
                                                           ReviewModel.product_id == product_id))
    all_reviews_product_id = stmt.all()
    
    if not all_reviews_product_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviews not found")
    return all_reviews_product_id


async def update_rating_product(id_product: int, session: AsyncSession):
    """
    Обновляет рейтинг у отзыва
    """
    stmt_avg_rating_product = await session.execute(select(func.avg(ReviewModel.grade)).
                                                    where(ReviewModel.is_active == True,
                                                          ReviewModel.product_id == id_product))
    avg_rating_product = stmt_avg_rating_product.scalar() or 0.0
    product = await session.get(ProductModel, id_product)
    await session.execute(update(ProductModel).where(ProductModel.id == product.id).values(rating = avg_rating_product))


@router.post("/reviews/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_new_reviews(new_review: ReviewRequest, session: AsyncSession = Depends(get_async_db),
                              current_user: UserModel = Depends(get_current_buyer)):
    """
    Создаёт отзыв, один 'buyer' один отзыв для каждого товара.
    """
    stmt = await session.scalars(select(ProductModel).where(ProductModel.id == new_review.product_id, 
                                                            ProductModel.is_active == True))
    product = stmt.first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    stmt_second_review = await session.scalars(select(ReviewModel).where(ReviewModel.product_id == new_review.product_id, ReviewModel.user_id == current_user.id))
    check_second_review = stmt_second_review.first()
    if check_second_review is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Сan't leave more than one product review.")

    db_new_review = ReviewModel(**new_review.model_dump(), user_id = current_user.id)
    session.add(db_new_review)

    await update_rating_product(product.id, session)
    await session.commit()
    return db_new_review
    

@router.delete("/reviews/{review_id}", status_code=status.HTTP_200_OK)
async def delete_reviews_by_id(review_id: int, session: AsyncSession = Depends(get_async_db),
                                current_user: UserModel = Depends(get_current_admin)) -> dict:
    """
    Выполняет мягкое удаление отзыва, можно только с ролью 'admin'.
    """
    stmt_review_id = await session.scalars(select(ReviewModel).where(ReviewModel.id == review_id, ReviewModel.is_active == True))
    review = stmt_review_id.first()

    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")    
    
    await session.execute(update(ReviewModel).where(ReviewModel.id == review_id).values(is_active = False))
    await update_rating_product(review.product_id, session)
    await session.commit()
    return {"message": "Review deleted"}
