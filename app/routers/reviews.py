import jwt

from sqlalchemy import select, func
from app.db_depends import get_async_db
from app.models.users import User as UserModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import Review as ReviewResponse, ReviewCreate as ReviewRequest
from app.models.reviews import Review as ReviewModel
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas import UserCreate, User as UserSchema
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import get_current_buyer
from app.models import Product as ProductModel

router = APIRouter(tags=["reviews"])

@router.get("/reviews/", response_model=list[ReviewResponse], status_code=status.HTTP_200_OK)
async def get_all_reviews(session: AsyncSession = Depends(get_async_db)):
    stmt = await session.scalars(select(ReviewModel).where(ReviewModel.is_active == True))
    all_reviews = stmt.all()
    return all_reviews

@router.get("/products/{product_id}/reviews/", response_model=list[ReviewResponse], status_code=status.HTTP_200_OK)
async def get_reviews_by_id_product(product_id: int, session: AsyncSession = Depends(get_async_db)):
    stmt = await session.scalars(select(ReviewModel).where(ReviewModel.is_active == True, 
                                                           ReviewModel.product_id == product_id))
    all_reviews_product_id = stmt.all()
    if not all_reviews_product_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return all_reviews_product_id

@router.post("/reviews/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_new_reviews(new_review: ReviewRequest, session: AsyncSession = Depends(get_async_db),
                              current_user: UserModel = Depends(get_current_buyer)):
    stmt = await session.scalars(select(ProductModel).where(ProductModel.id == new_review.product_id, 
                                                            ProductModel.is_active == True))
    product = stmt.first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detali="Product not found")
    
    stmt_avg_rating_product = await session.execute(select(func.avg(ReviewModel.grade)).
                                                    where(ReviewModel.is_active == True,
                                                          new_review.product_id == ReviewModel.product_id))
    avg_rating_product = stmt_avg_rating_product.scalar() or 0.0

    db_new_review = ReviewModel(**new_review.model_dump(), user_id = current_user.id)
    session.add(db_new_review)
    product_db = await session.get(ProductModel, product.id)
    product_db.rating = avg_rating_product
    await session.commit()
    return db_new_review
    

