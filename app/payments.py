from uuid import uuid4
from typing import Any
from decimal import Decimal
from anyio import to_thread
from yookassa import Configuration, Payment

from app.config import settings


async def create_yookassa_payment(order_id: int, amount: Decimal,
                                    user_email: str, description: str) -> dict[str, Any]:

    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        raise RuntimeError("Задайте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY в .env")
    
    # Настройка SDK
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    payload = {
        "amount": {
            "value": f"{amount:.2f}", 
            "currency": "RUB",
        },
        "confirmation": {
            "type":"redirect",
            "return_url": settings.YOOKASSA_RETURN_URL,
        },
        "capture": True, # Автосписание денег после авторизации
        "description": description,
        "metadata": {
            "order_id": order_id,
        },
        "receipt": { # ФИСКальный ЧЕК
            "customer":
            {
                "email": user_email
            },
            "items":[
                {
                    "description": description[:128],
                    "quantity": "1.00",
                    "amount":
                    {
                        "value": f"{amount:.2f}",
                        "currency": "RUB",
                    },
                    "vat_code": 1, # НДС: 1=без НДС
                    "payment_mode": "full_prepayment",
                    "payment_subject": "commodity",
                },
            ],
        },
    }

    def _request() -> Payment:
        return Payment.create(payload, str(uuid4()))
    
    payment: Payment = await to_thread.run_sync(_request)

    # Cсылка для оплаты
    confirmation_url = getattr(payment.confirmation, "confirmation_url", None)

    return {
        "id": payment.id,
        "status": payment.status,
        "confirmation_url": confirmation_url,
    }   