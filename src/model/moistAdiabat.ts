/**
 * Reference for the vertical totals T850 − T500: a parcel lifted from 850 hPa with its own dew point (from the
 * ECMWF relative humidity), dry adiabatically to its lifting condensation level, then along the pseudo-adiabat
 * to 500 hPa. Vertical totals above its T850 − T500 mean a Showalter index below 0.
 */

/** Gas constant of dry air, J/(kg K). */
const RD = 287.04749
/** Specific heat of dry air at constant pressure, J/(kg K). */
const CP = 1005.7
/** Poisson constant RD / CP of the dry adiabat. */
const KAPPA = RD / CP
/** Latent heat of vaporisation, J/kg. */
const LV = 2.501e6
/** Ratio of the molar masses of water vapour and dry air. */
const EPSILON = 0.6219569
const KELVIN = 273.15
/** Largest integration step of the pseudo-adiabat, hPa; 10 hPa keeps the error below 0.01 K. */
const MAX_STEP = 10
/** Levels the parcel starts at and is compared at, hPa. */
const P_START = 850
const P_END = 500

/** Above this temperature the IFS saturates over water, K (IFS Cy4x, Part IV Physical processes, ch. 12). */
const IFS_WATER = 273.16
/** Below this temperature the IFS saturates over ice; mixed phase in between, K (ibid.). */
const IFS_ICE = 250.16
/** Saturation vapour pressure at IFS_WATER in the IFS formulas, hPa. */
const IFS_E0 = 6.1121
/** Magnus coefficients of the IFS over water: factor and K added to T (ibid.). */
const IFS_A_WATER = 17.502
const IFS_B_WATER = 32.19
/** Magnus coefficients of the IFS over ice: factor and K subtracted from T, written as T + 0.7 (ibid.). */
const IFS_A_ICE = 22.587
const IFS_B_ICE = -0.7
/** Lowest and highest relative humidity used, %: 1 % avoids log(0), the IFS has values above 100 %. */
const RH_MIN = 1
const RH_MAX = 100
/** Constants of the LCL temperature after Bolton (1980), eq. 15, K. */
const BOLTON_LCL_OFFSET = 56
const BOLTON_LCL_SCALE = 800

/** Saturation vapour pressure over water, hPa; T in K (Bolton 1980). */
function saturationVapourPressure(t: number): number {
  return 6.112 * Math.exp((17.67 * (t - KELVIN)) / (t - 29.65))
}

/** Saturation mixing ratio over water, kg/kg; T in K, p in hPa (Bolton 1980). */
function saturationMixingRatio(t: number, p: number): number {
  const vapourPressure = saturationVapourPressure(t)
  return (EPSILON * vapourPressure) / (p - vapourPressure)
}

/** dT/dp of saturated air on the pseudo-adiabat, K/hPa (the formula of MetPy's moist_lapse). */
function moistLapse(t: number, p: number): number {
  const rs = saturationMixingRatio(t, p)
  return (RD * t + LV * rs) / (CP + (LV * LV * rs * EPSILON) / (RD * t * t)) / p
}

/** Temperature (K) of saturated air lifted pseudo-adiabatically from p0 to p1 (hPa), RK4 in steps of ≤ 10 hPa. */
function liftMoist(t0: number, p0: number, p1: number): number {
  const steps = Math.max(1, Math.ceil((p0 - p1) / MAX_STEP))
  const h = (p1 - p0) / steps
  let t = t0
  let p = p0
  // Classical Runge–Kutta of 4th order in pressure.
  for (let i = 0; i < steps; i++) {
    const k1 = moistLapse(t, p)
    const k2 = moistLapse(t + (h / 2) * k1, p + h / 2)
    const k3 = moistLapse(t + (h / 2) * k2, p + h / 2)
    const k4 = moistLapse(t + h * k3, p + h)
    t += (h / 6) * (k1 + 2 * k2 + 2 * k3 + k4)
    p += h
  }
  return t
}

/** Saturation vapour pressure the IFS relative humidity refers to, hPa: water, ice, or mixed in between; T in K. */
function ifsSaturationVapourPressure(t: number): number {
  const water = IFS_E0 * Math.exp((IFS_A_WATER * (t - IFS_WATER)) / (t - IFS_B_WATER))
  const ice = IFS_E0 * Math.exp((IFS_A_ICE * (t - IFS_WATER)) / (t - IFS_B_ICE))
  const alpha = t >= IFS_WATER ? 1 : t <= IFS_ICE ? 0 : ((t - IFS_ICE) / (IFS_WATER - IFS_ICE)) ** 2
  return alpha * water + (1 - alpha) * ice
}

/** Dew point over water (K) of air at T (K) with the IFS relative humidity rh (%). */
function dewPointOf(t: number, rh: number): number {
  const clamped = Math.min(RH_MAX, Math.max(RH_MIN, rh))
  const vapourPressure = (clamped / 100) * ifsSaturationVapourPressure(t)
  // Inverse of Bolton's formula, consistent with saturationMixingRatio.
  const ln = Math.log(vapourPressure / 6.112)
  return (243.5 * ln) / (17.67 - ln) + KELVIN
}

export interface ParcelLift {
  /** T850 − T of the parcel at 500 hPa, K; comparable with the vertical totals. */
  totals: number
  /** Dew point at 850 hPa, °C. */
  dewPoint: number
  /** Pressure of the lifting condensation level, hPa (≤ 850). */
  lclPressure: number
}

/**
 * Parcel lifted from 850 hPa with its own dew point: dry adiabatically to the LCL, then pseudo-adiabatically.
 * With RH 100 % about 33 K at T850 −10 °C, 30 K at 0 °C, 27 K at +5 °C; drier air gives more.
 *
 * @param t850 temperature at 850 hPa, °C
 * @param rh850 relative humidity at 850 hPa as the IFS defines it, %
 */
export function parcelLift(t850: number, rh850: number): ParcelLift {
  const t = t850 + KELVIN
  const td = dewPointOf(t, rh850)
  // LCL temperature after Bolton (1980), eq. 15; pressure along the dry adiabat without moisture correction (< 1 hPa).
  const tLcl = 1 / (1 / (td - BOLTON_LCL_OFFSET) + Math.log(t / td) / BOLTON_LCL_SCALE) + BOLTON_LCL_OFFSET
  const pLcl = P_START * (tLcl / t) ** (1 / KAPPA)
  const parcel = pLcl <= P_END ? t * (P_END / P_START) ** KAPPA : liftMoist(tLcl, pLcl, P_END)
  return { totals: t - parcel, dewPoint: td - KELVIN, lclPressure: pLcl }
}
