import time

from app.core.celery_app import celery_app
from app.tasks.reliability import ReliableTask, already_done, mark_done


@celery_app.task(base=ReliableTask)
def generate_order_pdf(order_id: int) -> str:
    key = f"pdf_generated:{order_id}"
    if already_done(key):
        return f"PDF already generated for order {order_id}"
    time.sleep(2)
    mark_done(key)
    return f"PDF generated for order {order_id}"


@celery_app.task(base=ReliableTask)
def send_order_email(order_id: int, email: str) -> str:
    key = f"email_sent:{order_id}"
    if already_done(key):
        return f"Email already sent for order {order_id}"
    time.sleep(1)
    if order_id % 5 == 0:
        raise ConnectionError("Email service unavailable")
    mark_done(key)
    return f"Email sent to {email} for order {order_id}"


@celery_app.task(base=ReliableTask)
def send_order_sms(order_id: int, phone: str) -> str:
    key = f"sms_sent:{order_id}"
    if already_done(key):
        return f"SMS already sent for order {order_id}"
    time.sleep(1)
    mark_done(key)
    return f"SMS sent to {phone} for order {order_id}"
