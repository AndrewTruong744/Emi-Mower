import {
  autocanonize,
  concat,
  includes,
  intersects,
  join,
  new_key_expr,
} from '@/zenoh/keyExprShim';

describe('native Zenoh key-expression shim', () => {
  it('validates and combines key expressions', () => {
    expect(() => new_key_expr('user/login')).not.toThrow();
    expect(join('user/', '/login')).toBe('user/login');
    expect(concat('user/', 'login')).toBe('user/login');
    expect(autocanonize('/user//login/')).toBe('user/login');
  });

  it('checks key-expression relationships', () => {
    expect(includes('user', 'user/login')).toBe(true);
    expect(includes('user/login', 'user')).toBe(false);
    expect(intersects('user', 'user/login')).toBe(true);
    expect(intersects('mower', 'user/login')).toBe(false);
  });

  it('rejects empty and null-character expressions', () => {
    expect(() => new_key_expr('')).toThrow('Invalid Zenoh key expression');
    expect(() => join('user', '\0login')).toThrow('Invalid Zenoh key expression');
  });
});
