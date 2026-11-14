import time

from core.celery_app import celery_app


@celery_app.task(name="tasks.test_task.add_numbers")
def add_numbers(x: int, y: int) -> int:
    time.sleep(2)
    return x + y
