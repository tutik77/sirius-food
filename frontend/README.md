# Сириус.Еда — дизайн-кит для ЛР № 8 (SSR-витрина)

Next.js 16 (App Router) + TypeScript + Tailwind CSS + нативный fetch.
Кит даёт визуальные компоненты и REST-клиент; страницы-маршруты, состояния и
ISR вы пишете сами по методичке ЛР № 8.

## Быстрый старт

```bash
npm install
cp .env.example .env.local
npm run dev
```

Откройте http://localhost:3000 — корень ведёт на /menu (пока заглушка TODO).
Бэкенд должен отвечать на адресе из .env.local (по умолчанию 127.0.0.1:8000).

Если ваш бэкенд на другом порту/хосте — поменяйте API_URL и
NEXT_PUBLIC_API_URL в .env.local и перезапустите dev-сервер. Код не трогаем.

## Что готово (не переписывать)

| Файл | Назначение |
|---|---|
| src/lib/api.ts | REST-клиент: getMenuItems(), getMenuItem(id), formatPrice(); адрес из окружения |
| src/lib/presentation.ts | Детерминированный подбор эмодзи/тона карточки по категории |
| src/components/DishCard.tsx | Карточка блюда (использует api + presentation) |
| src/components/DishArtwork.tsx | Иллюстрация-«тарелка» для карточки и hero |
| src/components/AddToCartButton.tsx | Пример клиентского острова (use client, useState) |
| src/components/SiteHeader.tsx, SiteFooter.tsx | Каркас страницы |
| src/app/layout.tsx, globals.css | Корневой layout и дизайн-токены |
| src/app/page.tsx | Корень, redirect на /menu |
| check.sh | Объективные проверки (PASS/FAIL), приложите вывод к README |

## Что реализовать (TODO)

| Файл | Баллы | Задание |
|---|---|---|
| src/app/menu/page.tsx | 6–7 | SSR списка блюд (+ revalidate на 8) |
| src/app/menu/[id]/page.tsx | 6–7 | SSR карточки, notFound() (+ revalidate на 8, generateMetadata на 9) |
| src/app/menu/loading.tsx | 8 | Скелетон загрузки (создать) |
| src/app/menu/error.tsx | 8 | Экран ошибки с use client и кнопкой reset (создать) |
| SEO / кабинет-lite | 9 | По методичке, вариант А или Б |
| GraphQL BFF / /menu-csr | 10 | По методичке, вариант А или Б |

## Проверки

```bash
./check.sh                      # объективные PASS/FAIL
curl -s http://localhost:3000/menu | grep -F "<название блюда>"   # SSR вручную
```

Для ISR (8 баллов) проверяйте в production-режиме:

```bash
npm run build
npm start
```

## Дизайн-токены

В globals.css готовы классы: hero-panel, tech-panel, menu-section, dish-grid,
dish-card, detail-card, ssr-note, loading-*, error-*, category-chip и др.
Используйте их, чтобы витрина выглядела цельно, или пишите свои — дорога Б
разрешает любой дизайн при тех же критериях.
