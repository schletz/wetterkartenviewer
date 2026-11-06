"""Moist air on a pressure level: vapour pressure from the IFS relative humidity and the equivalent potential temperature.

The formulas are those of src/model/moistAdiabat.ts. The app scales its θe line
with the θe of dry and of saturated air computed there, so both sides must give
the same value for the same temperature and humidity.
"""

import numpy as np

from .constants import KELVIN

# Above this temperature the IFS saturates over water, below IFS_ICE over ice, mixed in between, K
# (IFS Cy4x, Part IV Physical processes, ch. 12).
IFS_WATER = 273.16
IFS_ICE = 250.16
# Saturation vapour pressure at IFS_WATER in the IFS formulas, hPa, and the Magnus coefficients over water and ice.
IFS_E0 = 6.1121
IFS_A_WATER, IFS_B_WATER = 17.502, 32.19
IFS_A_ICE, IFS_B_ICE = 22.587, -0.7
# Lowest and highest relative humidity used, %: 1 % avoids log(0), the IFS has values slightly above 100 %.
RH_MIN, RH_MAX = 1.0, 100.0
# Ratio of the molar masses of water vapour and dry air.
EPSILON = 0.6219569
# Poisson exponent of dry air in Bolton's formula for the equivalent potential temperature.
BOLTON_KAPPA = 0.2854
# Constants of the LCL temperature after Bolton (1980), eq. 15, K.
BOLTON_LCL_OFFSET, BOLTON_LCL_SCALE = 56.0, 800.0
REFERENCE_PRESSURE = 1000.0


def ifs_saturation_vapour_pressure(t: np.ndarray) -> np.ndarray:
    """Saturation vapour pressure (hPa) the IFS relative humidity refers to: water, ice or mixed in between; T in K."""
    water = IFS_E0 * np.exp(IFS_A_WATER * (t - IFS_WATER) / (t - IFS_B_WATER))
    ice = IFS_E0 * np.exp(IFS_A_ICE * (t - IFS_WATER) / (t - IFS_B_ICE))
    alpha = np.clip((t - IFS_ICE) / (IFS_WATER - IFS_ICE), 0.0, 1.0) ** 2
    return alpha * water + (1.0 - alpha) * ice


def vapour_pressure(t: np.ndarray, rh: np.ndarray) -> np.ndarray:
    """Vapour pressure (hPa) of air at T (K) with the IFS relative humidity rh (%), clamped to RH_MIN…RH_MAX."""
    return np.clip(rh, RH_MIN, RH_MAX) / 100.0 * ifs_saturation_vapour_pressure(t)


def dew_point(e: np.ndarray) -> np.ndarray:
    """Dew point over water (K) of the vapour pressure e (hPa): the inverse of Bolton's saturation formula."""
    ln = np.log(e / 6.112)
    return 243.5 * ln / (17.67 - ln) + KELVIN


def equivalent_potential_temperature(t: np.ndarray, rh: np.ndarray, p: float) -> np.ndarray:
    """Equivalent potential temperature (K) after Bolton (1980), eq. 43, of air at T (K), RH (%) and p (hPa).

    The air is lifted to its condensation level (temperature from the dew
    point, Bolton eq. 15), then pseudo-adiabatically until all vapour has
    condensed and fallen out, and brought down to 1000 hPa. Dry air gives its
    potential temperature; RH is clamped to RH_MIN…RH_MAX.
    """
    t = np.asarray(t, dtype=np.float64)
    e = vapour_pressure(t, np.asarray(rh, dtype=np.float64))
    td = dew_point(e)
    t_lcl = 1.0 / (1.0 / (td - BOLTON_LCL_OFFSET) + np.log(t / td) / BOLTON_LCL_SCALE) + BOLTON_LCL_OFFSET
    mixing_ratio = 1000.0 * EPSILON * e / (p - e)  # g/kg
    theta = t * (REFERENCE_PRESSURE / p) ** (BOLTON_KAPPA * (1.0 - 0.28e-3 * mixing_ratio))
    return theta * np.exp((3.376 / t_lcl - 0.00254) * mixing_ratio * (1.0 + 0.81e-3 * mixing_ratio))
