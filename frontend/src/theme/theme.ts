import type { UIState, ContrastLevel, Theme } from '../types';

export const DEFAULT_UI_STATE: UIState = {
  font_scale: 1.0,
  contrast_level: 'normal',
  density: 'default',
  theme: 'light',
  hit_target_min_px: 32,
  reduced_motion: false,
  hide_nonessential: false,
};

interface PaletteColors {
  fg: string;
  bg: string;
  surface: string;
  border: string;
  accent: string;
  accentFg: string;
  muted: string;
  warn: string;
  fail: string;
  ok: string;
}

const PALETTES: Record<Theme, Record<ContrastLevel, PaletteColors>> = {
  light: {
    low: {
      fg: '#888888',
      bg: '#ffffff',
      surface: '#f7f7f7',
      border: '#e0e0e0',
      accent: '#5a78c2',
      accentFg: '#ffffff',
      muted: '#999999',
      warn: '#b67500',
      fail: '#a83232',
      ok: '#2f7a3a',
    },
    normal: {
      fg: '#222222',
      bg: '#ffffff',
      surface: '#f4f5f7',
      border: '#d8dce3',
      accent: '#2c4d9e',
      accentFg: '#ffffff',
      muted: '#5e6470',
      warn: '#8a5300',
      fail: '#8a2222',
      ok: '#1f5e2a',
    },
    high: {
      fg: '#0a0a0a',
      bg: '#ffffff',
      surface: '#ffffff',
      border: '#1a1a1a',
      accent: '#1a3a85',
      accentFg: '#ffffff',
      muted: '#3a3a3a',
      warn: '#6a3c00',
      fail: '#6a1818',
      ok: '#0e4818',
    },
    max: {
      fg: '#000000',
      bg: '#ffffff',
      surface: '#ffffff',
      border: '#000000',
      accent: '#000000',
      accentFg: '#ffffff',
      muted: '#1a1a1a',
      warn: '#552c00',
      fail: '#5a0000',
      ok: '#003200',
    },
  },
  dark: {
    low: {
      fg: '#888888',
      bg: '#1a1a1a',
      surface: '#222222',
      border: '#2e2e2e',
      accent: '#7a92cc',
      accentFg: '#0a0a0a',
      muted: '#666666',
      warn: '#d4a040',
      fail: '#d46868',
      ok: '#7ac28a',
    },
    normal: {
      fg: '#e7e7ec',
      bg: '#0e1117',
      surface: '#161a23',
      border: '#262b36',
      accent: '#7da7ff',
      accentFg: '#0a0a0a',
      muted: '#8b91a3',
      warn: '#f4c04a',
      fail: '#f47272',
      ok: '#7fd49a',
    },
    high: {
      fg: '#f5f5f5',
      bg: '#000000',
      surface: '#0a0a0a',
      border: '#404040',
      accent: '#a8c4ff',
      accentFg: '#000000',
      muted: '#bdbdbd',
      warn: '#ffd070',
      fail: '#ff8a8a',
      ok: '#9ee5b0',
    },
    max: {
      fg: '#ffffff',
      bg: '#000000',
      surface: '#000000',
      border: '#ffffff',
      accent: '#ffffff',
      accentFg: '#000000',
      muted: '#e0e0e0',
      warn: '#ffe080',
      fail: '#ffa0a0',
      ok: '#b0ffc4',
    },
  },
};

const DENSITY_SPACING: Record<UIState['density'], number> = {
  compact: 0.75,
  default: 1.0,
  comfortable: 1.25,
};

export function applyUIState(state: UIState): void {
  const root = document.documentElement;
  const palette = PALETTES[state.theme][state.contrast_level];

  root.style.setProperty('--fg', palette.fg);
  root.style.setProperty('--bg', palette.bg);
  root.style.setProperty('--surface', palette.surface);
  root.style.setProperty('--border', palette.border);
  root.style.setProperty('--accent', palette.accent);
  root.style.setProperty('--accent-fg', palette.accentFg);
  root.style.setProperty('--muted', palette.muted);
  root.style.setProperty('--warn', palette.warn);
  root.style.setProperty('--fail', palette.fail);
  root.style.setProperty('--ok', palette.ok);

  root.style.setProperty('--font-scale', String(state.font_scale));
  root.style.setProperty('--font-base', `${state.font_scale * 16}px`);
  root.style.setProperty('--spacing-mult', String(DENSITY_SPACING[state.density]));
  root.style.setProperty('--hit-target', `${state.hit_target_min_px}px`);
  root.style.setProperty('--motion-scale', state.reduced_motion ? '0' : '1');

  root.dataset.theme = state.theme;
  root.dataset.contrast = state.contrast_level;
  root.dataset.density = state.density;
  root.dataset.reducedMotion = state.reduced_motion ? 'true' : 'false';
  root.dataset.hideNonessential = state.hide_nonessential ? 'true' : 'false';
}

export function mergeAdaptation(
  current: UIState,
  applied: Partial<UIState>
): UIState {
  return {
    ...current,
    ...applied,
  };
}
