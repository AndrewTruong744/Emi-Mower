import { describe, expect, it } from '@jest/globals';
import { APP_SAFE_AREA_EDGES } from '@/constants/layout';

describe('app layout constants', () => {
  it('protects content from the status area and side cutouts', () => {
    expect(APP_SAFE_AREA_EDGES).toEqual(['top', 'left', 'right']);
  });
});
