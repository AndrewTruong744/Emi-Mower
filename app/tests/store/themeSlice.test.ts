import { beforeEach, describe, expect, it } from '@jest/globals';
import { useBoundStore } from '@/store/useBoundStore';

describe('theme store slice', () => {
  beforeEach(() => useBoundStore.getState().setThemePreference('system'));

  it('sets and toggles theme preferences', () => {
    useBoundStore.getState().toggleThemePreference();
    expect(useBoundStore.getState().themePreference).toBe('dark');
    useBoundStore.getState().setThemePreference('dark');
    useBoundStore.getState().toggleThemePreference();
    expect(useBoundStore.getState().themePreference).toBe('light');
  });
});
