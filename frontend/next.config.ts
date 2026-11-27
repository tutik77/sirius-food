import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep the lecture demo visually clean; the dev server logs still show build status.
  devIndicators: false,
  /*
   * В учебном проекте используем классическую модель кеширования Next.js:
   * fetch-запрос к REST API кешируется через `next: { revalidate: 60 }`.
   * Поэтому Cache Components (cacheComponents) намеренно выключены.
   */
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
