from prometheus_client import Counter, Histogram

RESPONSE_SECONDS = Histogram(
    "assistant_response_seconds",
    "Время ответа AI-ассистента",
    buckets=(0.5, 1, 2, 3, 5, 8, 13, 20, 30),
)
REQUESTS = Counter("assistant_requests_total", "Вопросы к ассистенту", ["outcome"])
FEEDBACK = Counter("assistant_feedback_total", "Оценки ответов ассистента", ["helpful"])
