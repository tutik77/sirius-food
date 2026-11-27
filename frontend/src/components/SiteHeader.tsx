import Link from "next/link";

import { PUBLIC_API_URL } from "@/lib/api";

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link className="brand" href="/menu" aria-label="Сириус.Еда — к меню">
        <span className="brand-mark" aria-hidden="true">с.</span>
        <span className="brand-copy">
          <strong>Сириус.Еда</strong>
          <small>Кухня рядом</small>
        </span>
      </Link>

      <nav className="main-nav" aria-label="Основная навигация">
        <Link href="/menu#menu">Меню</Link>
        <a href={`${PUBLIC_API_URL}/docs`} target="_blank" rel="noreferrer">
          API <span aria-hidden="true">↗</span>
        </a>
      </nav>

      <Link className="header-action" href="/menu#menu">
        Выбрать блюдо <span aria-hidden="true">↗</span>
      </Link>
    </header>
  );
}
