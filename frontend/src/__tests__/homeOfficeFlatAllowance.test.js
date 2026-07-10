import { describe, it, expect } from 'vitest';
import { homeOfficeFlatAllowance } from '../components/BusinessShared';

const BASE_CONFIG = {
  home_office_band_25_50:    10.0,
  home_office_band_51_100:   18.0,
  home_office_band_101_plus: 26.0,
};

describe('homeOfficeFlatAllowance — band mapping', () => {
  it('25_50 band returns the 25_50 config value', () => {
    expect(homeOfficeFlatAllowance('25_50', BASE_CONFIG)).toBe(10.0);
  });

  it('51_100 band returns the 51_100 config value', () => {
    expect(homeOfficeFlatAllowance('51_100', BASE_CONFIG)).toBe(18.0);
  });

  it('101_plus band returns the 101_plus config value', () => {
    expect(homeOfficeFlatAllowance('101_plus', BASE_CONFIG)).toBe(26.0);
  });
});

describe('homeOfficeFlatAllowance — values come from config, not hardcoded', () => {
  it('changing the 25_50 rate in config changes the returned value', () => {
    const altConfig = { ...BASE_CONFIG, home_office_band_25_50: 15.0 };
    expect(homeOfficeFlatAllowance('25_50', altConfig)).toBe(15.0);
    // Original config unchanged
    expect(homeOfficeFlatAllowance('25_50', BASE_CONFIG)).toBe(10.0);
  });

  it('changing the 101_plus rate in config changes the returned value', () => {
    const altConfig = { ...BASE_CONFIG, home_office_band_101_plus: 30.0 };
    expect(homeOfficeFlatAllowance('101_plus', altConfig)).toBe(30.0);
  });

  it('three bands each return their own distinct config value', () => {
    const values = ['25_50', '51_100', '101_plus'].map(b => homeOfficeFlatAllowance(b, BASE_CONFIG));
    expect(values).toEqual([10.0, 18.0, 26.0]);
    expect(new Set(values).size).toBe(3); // all distinct
  });
});

describe('homeOfficeFlatAllowance — edge cases', () => {
  it('returns null when taxConfig is null', () => {
    expect(homeOfficeFlatAllowance('25_50', null)).toBeNull();
  });

  it('returns null when taxConfig is undefined', () => {
    expect(homeOfficeFlatAllowance('25_50', undefined)).toBeNull();
  });

  it('returns null when band is null', () => {
    expect(homeOfficeFlatAllowance(null, BASE_CONFIG)).toBeNull();
  });

  it('returns null when band is undefined', () => {
    expect(homeOfficeFlatAllowance(undefined, BASE_CONFIG)).toBeNull();
  });

  it('returns null for an unrecognised band string', () => {
    expect(homeOfficeFlatAllowance('200_plus', BASE_CONFIG)).toBeNull();
  });

  it('returns null when the matching config value is undefined', () => {
    const sparseConfig = { home_office_band_51_100: 18.0 };
    expect(homeOfficeFlatAllowance('25_50', sparseConfig)).toBeNull();
  });
});
