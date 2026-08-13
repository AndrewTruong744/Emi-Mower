import { describe, expect, it } from '@jest/globals';
import { APP_SAFE_AREA_EDGES } from '@/constants/layout';

describe('app layout constants', () => {
  it('keeps content edge-to-edge vertically while protecting side cutouts', () => {
    expect(APP_SAFE_AREA_EDGES).toEqual(['left', 'right']);
  });
});
