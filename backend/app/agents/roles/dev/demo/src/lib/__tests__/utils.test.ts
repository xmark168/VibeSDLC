import { cn } from '../utils';

describe('cn utility function', () => {
  it('merges class names correctly', () => {
    const result = cn('class1', 'class2');
    expect(result).toBe('class1 class2');
  });

  it('handles conditional classes', () => {
    const result = cn('base', true && 'conditional', false && 'hidden');
    expect(result).toBe('base conditional');
  });

  it('merges Tailwind classes correctly', () => {
    // Tailwind merge should handle conflicting classes
    const result = cn('px-2 py-1', 'px-4');
    expect(result).toBe('py-1 px-4');
  });

  it('handles undefined and null values', () => {
    const result = cn('class1', undefined, null, 'class2');
    expect(result).toBe('class1 class2');
  });

  it('handles empty strings', () => {
    const result = cn('class1', '', 'class2');
    expect(result).toBe('class1 class2');
  });

  it('handles arrays of classes', () => {
    const result = cn(['class1', 'class2'], 'class3');
    expect(result).toBe('class1 class2 class3');
  });

  it('handles objects with boolean values', () => {
    const result = cn({
      'class1': true,
      'class2': false,
      'class3': true,
    });
    expect(result).toBe('class1 class3');
  });
});

