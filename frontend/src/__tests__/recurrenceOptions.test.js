import { describe, it, expect } from 'vitest';
import { RECURRENCE_OPTIONS, RECURRENCE_LABELS } from '../components/BusinessShared';

describe('RECURRENCE_OPTIONS', () => {
  it('has exactly 10 options', () => {
    expect(RECURRENCE_OPTIONS).toHaveLength(10);
  });

  it('first option is "Does not recur" with empty value', () => {
    expect(RECURRENCE_OPTIONS[0]).toEqual({ value: '', label: 'Does not recur' });
  });

  it('contains all required frequency values in order', () => {
    const values = RECURRENCE_OPTIONS.map(o => o.value);
    expect(values).toEqual([
      '',
      'weekly',
      'two_weekly',
      'four_weekly',
      'monthly',
      'two_monthly',
      'quarterly',
      'biannually',
      'annually',
      'two_yearly',
    ]);
  });

  it('labels match the spec exactly', () => {
    const labels = RECURRENCE_OPTIONS.map(o => o.label);
    expect(labels).toEqual([
      'Does not recur',
      'Weekly',
      'Two Weekly',
      'Four Weekly',
      'Monthly',
      'Two Monthly',
      'Quarterly',
      'Biannually',
      'Annually',
      '2-Yearly',
    ]);
  });

  it('all values are unique', () => {
    const values = RECURRENCE_OPTIONS.map(o => o.value);
    expect(new Set(values).size).toBe(values.length);
  });
});

describe('RECURRENCE_LABELS', () => {
  it('maps all non-empty frequency values to their display labels', () => {
    expect(RECURRENCE_LABELS['weekly']).toBe('Weekly');
    expect(RECURRENCE_LABELS['two_weekly']).toBe('Two Weekly');
    expect(RECURRENCE_LABELS['four_weekly']).toBe('Four Weekly');
    expect(RECURRENCE_LABELS['monthly']).toBe('Monthly');
    expect(RECURRENCE_LABELS['two_monthly']).toBe('Two Monthly');
    expect(RECURRENCE_LABELS['quarterly']).toBe('Quarterly');
    expect(RECURRENCE_LABELS['biannually']).toBe('Biannually');
    expect(RECURRENCE_LABELS['annually']).toBe('Annually');
    expect(RECURRENCE_LABELS['two_yearly']).toBe('2-Yearly');
  });

  it('has exactly 9 entries (no empty-string key)', () => {
    expect(Object.keys(RECURRENCE_LABELS)).toHaveLength(9);
    expect(RECURRENCE_LABELS['']).toBeUndefined();
  });
});
