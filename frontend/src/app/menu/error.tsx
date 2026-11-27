"use client";

export default function MenuError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="page-shell">
      <section className="error-card" role="alert">
        <div className="error-card__icon" aria-hidden="true">⚠️</div>
        <h1>Не удалось загрузить меню</h1>
        <p>Бэкенд «Сириус.Еды» не ответил. Проверьте, что API запущен на http://127.0.0.1:8000.</p>
        <p>{error.message}</p>
        <button type="button" className="button button--dark" onClick={() => reset()}>
          Попробовать снова
        </button>
      </section>
    </main>
  );
}
