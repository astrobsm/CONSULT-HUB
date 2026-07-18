/**
 * Appearance preferences applied to the document root:
 * - theme: system | light | dark  -> `data-theme` attribute
 * - accent: named color           -> `--primary` / `--primary-dark`
 * - font:  system | serif | mono | rounded -> `--app-font`
 *
 * Values are mirrored to localStorage so the choice applies instantly on the
 * next load (before the authenticated user resolves) — no flash of default.
 */

export interface Appearance {
  theme?: string
  accent?: string
  font_family?: string
}

export const ACCENTS: Record<string, { primary: string; dark: string }> = {
  blue: { primary: '#1e6fd9', dark: '#1857ab' },
  teal: { primary: '#0d9488', dark: '#0b7268' },
  green: { primary: '#0f9d58', dark: '#0b7a43' },
  purple: { primary: '#6d3bd9', dark: '#572eae' },
  rose: { primary: '#e11d6b', dark: '#b71655' },
  amber: { primary: '#d97706', dark: '#b45309' },
  slate: { primary: '#475569', dark: '#334155' },
}

export const FONTS: Record<string, string> = {
  system: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  serif: "Georgia, 'Times New Roman', serif",
  mono: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
  rounded:
    "ui-rounded, 'Segoe UI', 'Nunito', system-ui, sans-serif",
}

const KEY = 'consulthub_appearance'

export function loadStoredAppearance(): Appearance {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '{}')
  } catch {
    return {}
  }
}

export function applyAppearance(a: Appearance) {
  const root = document.documentElement
  const theme = a.theme ?? 'system'
  if (theme === 'light' || theme === 'dark') {
    root.setAttribute('data-theme', theme)
  } else {
    root.removeAttribute('data-theme')
  }

  const accent = ACCENTS[a.accent ?? 'blue'] ?? ACCENTS.blue
  root.style.setProperty('--primary', accent.primary)
  root.style.setProperty('--primary-dark', accent.dark)

  const font = FONTS[a.font_family ?? 'system'] ?? FONTS.system
  root.style.setProperty('--app-font', font)

  localStorage.setItem(KEY, JSON.stringify(a))
}
