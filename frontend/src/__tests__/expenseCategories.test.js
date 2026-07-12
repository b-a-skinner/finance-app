import { describe, it, expect } from 'vitest';
import { CATEGORY_INFO, ALLOWABLE_CATS, NON_ALLOWABLE_CATS, DUAL_CATS } from '../components/BusinessShared';

// ---------------------------------------------------------------------------
// New HMRC categories: goods bought to sell on, clothing
// ---------------------------------------------------------------------------

describe('new allowable categories', () => {
  it('goods_for_resale is present, allowable, and labelled per spec', () => {
    expect(CATEGORY_INFO.goods_for_resale).toBeDefined();
    expect(CATEGORY_INFO.goods_for_resale.label).toBe('Goods bought to sell on (stock & materials)');
    expect(CATEGORY_INFO.goods_for_resale.allowable).toBe(true);
  });

  it('clothing is present, allowable, and labelled per spec', () => {
    expect(CATEGORY_INFO.clothing).toBeDefined();
    expect(CATEGORY_INFO.clothing.label).toBe('Clothing');
    expect(CATEGORY_INFO.clothing.allowable).toBe(true);
  });

  it('both new categories appear in ALLOWABLE_CATS (the "Allowable expenses" dropdown group)', () => {
    expect(ALLOWABLE_CATS).toContain('goods_for_resale');
    expect(ALLOWABLE_CATS).toContain('clothing');
  });

  it('both new categories are absent from the non-allowable and dual-purpose groups', () => {
    expect(NON_ALLOWABLE_CATS).not.toContain('goods_for_resale');
    expect(NON_ALLOWABLE_CATS).not.toContain('clothing');
    expect(DUAL_CATS).not.toContain('goods_for_resale');
    expect(DUAL_CATS).not.toContain('clothing');
  });

  it('every ALLOWABLE_CATS entry, including the two new ones, defaults allowable to true', () => {
    for (const cat of ALLOWABLE_CATS) {
      expect(CATEGORY_INFO[cat].allowable).toBe(true);
    }
  });

  it('every category, including the two new ones, carries a tip for the info bubble', () => {
    for (const cat of ['goods_for_resale', 'clothing']) {
      expect(typeof CATEGORY_INFO[cat].tip).toBe('string');
      expect(CATEGORY_INFO[cat].tip.length).toBeGreaterThan(0);
    }
  });
});

describe('existing categories are unchanged', () => {
  it('existing allowable categories keep their exact labels', () => {
    expect(CATEGORY_INFO.office.label).toBe('Office costs (rent, utilities)');
    expect(CATEGORY_INFO.equipment.label).toBe('Equipment');
    expect(CATEGORY_INFO.bank_charges.label).toBe('Bank & finance charges');
  });

  it('office costs stays a single category, not split', () => {
    expect(CATEGORY_INFO.office).toBeDefined();
    expect(Object.keys(CATEGORY_INFO).filter(k => k.startsWith('office'))).toEqual(['office']);
  });

  it('non-allowable and dual-purpose category sets are untouched', () => {
    expect(NON_ALLOWABLE_CATS).toEqual(['client_entertainment', 'fines', 'personal', 'political']);
    expect(DUAL_CATS).toEqual(['home_office', 'other']);
  });

  it('original 12 allowable categories are all still present, in addition to the 2 new ones', () => {
    const original = ['equipment', 'software', 'office', 'travel', 'professional_fees', 'marketing',
      'training', 'insurance', 'staff_costs', 'phone_internet', 'pension_employer', 'bank_charges'];
    for (const cat of original) expect(ALLOWABLE_CATS).toContain(cat);
    expect(ALLOWABLE_CATS).toHaveLength(original.length + 2);
  });
});
