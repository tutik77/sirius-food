import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <Link className="brand brand--footer" href="/menu">
        <span className="brand-mark" aria-hidden="true">с.</span>
        <span className="brand-copy">
          <strong>Сириус.Еда</strong>
          <small>Кухня рядом</small>
        </span>
      </Link>
      <p>Учебная витрина кампусного сервиса доставки.</p>
      <span className="footer-status"><i /> Next.js · FastAPI</span>
    </footer>
  );
}
