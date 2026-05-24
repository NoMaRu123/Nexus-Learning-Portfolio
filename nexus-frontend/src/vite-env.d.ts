/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_NEXUS_MODE: "tracker" | "portfolio";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
