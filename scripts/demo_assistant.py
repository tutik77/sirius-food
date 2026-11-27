import sys

import httpx

BASE_URL = "http://127.0.0.1:8000"
STUDENT = ("load-student@sirius.ru", "StudentPass123")
QUESTIONS = [
    "Что у вас есть из супов и сколько стоит?",
    "Сколько стоит доставка и до скольки вы работаете?",
    "Где мой последний заказ?",
    "Сколько у меня баллов и есть ли сейчас промокоды?",
]


def main(questions: list[str]) -> None:
    api = httpx.Client(base_url=BASE_URL, timeout=90)
    token = api.post("/auth/token", data={"username": STUDENT[0], "password": STUDENT[1]}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for question in questions:
        reply = api.post("/assistant/chat", json={"question": question}, headers=headers).json()
        print(f"\nВопрос: {question}\nОтвет ({reply['latency_ms']} мс, fallback={reply['is_fallback']}): {reply['answer']}")
        api.post(f"/assistant/messages/{reply['id']}/feedback", json={"helpful": True}, headers=headers)


if __name__ == "__main__":
    main(sys.argv[1:] or QUESTIONS)
