/**
 * Reference for the vertical totals T850 − T500: the difference along the pseudo-adiabat of saturated air
 * lifted from 850 hPa. Vertical totals above it mean conditional instability between 850 and 500 hPa.
 */

/** Gas constant of dry air, J/(kg K). */
const RD = 287.04749
/** Specific heat of dry air at constant pressure, J/(kg K). */
const CP = 1005.7
/** Latent heat of vaporisation, J/kg. */
const LV = 2.501e6
/** Ratio of the molar masses of water vapour and dry air. */
const EPSILON = 0.6219569
const KELVIN = 273.15
/** Integration steps from 850 to 500 hPa; 10 hPa each keeps the error below 0.01 K. */
const STEPS = 35

/** Saturation mixing ratio over water, kg/kg; T in K, p in hPa (Bolton 1980). */
function saturationMixingRatio(t: number, p: number): number {
  const vapourPressure = 6.112 * Math.exp((17.67 * (t - KELVIN)) / (t - 29.65))
  return (EPSILON * vapourPressure) / (p - vapourPressure)
}

/** dT/dp of saturated air on the pseudo-adiabat, K/hPa (the formula of MetPy's moist_lapse). */
function moistLapse(t: number, p: number): number {
  const rs = saturationMixingRatio(t, p)
  return (RD * t + LV * rs) / (CP + (LV * LV * rs * EPSILON) / (RD * t * t)) / p
}

/**
 * T850 − T500 of saturated air lifted pseudo-adiabatically from 850 hPa, in K.
 * About 33 K at T850 −10 °C, 30 K at 0 °C, 27 K at +5 °C, 22 K at +15 °C.
 *
 * @param t850 temperature at 850 hPa, °C
 */
export function moistAdiabaticTotals(t850: number): number {
  const h = (500 - 850) / STEPS
  let t = t850 + KELVIN
  let p = 850
  // Classical Runge–Kutta of 4th order in pressure.
  for (let i = 0; i < STEPS; i++) {
    const k1 = moistLapse(t, p)
    const k2 = moistLapse(t + (h / 2) * k1, p + h / 2)
    const k3 = moistLapse(t + (h / 2) * k2, p + h / 2)
    const k4 = moistLapse(t + h * k3, p + h)
    t += (h / 6) * (k1 + 2 * k2 + 2 * k3 + k4)
    p += h
  }
  return t850 + KELVIN - t
}
