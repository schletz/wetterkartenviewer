/**
 * Austrian public holidays, ported from calendar_days.py of the synop skill.
 * Dates are calendar days in UTC, as the slider shows valid times in UTC.
 */

/** Fixed holidays by "month-day". */
const FIXED_HOLIDAYS: Record<string, string> = {
  '1-1': 'Neujahr',
  '1-6': 'Heilige Drei Könige',
  '5-1': 'Staatsfeiertag',
  '8-15': 'Mariä Himmelfahrt',
  '10-26': 'Nationalfeiertag',
  '11-1': 'Allerheiligen',
  '12-8': 'Mariä Empfängnis',
  '12-25': 'Christtag',
  '12-26': 'Stefanitag',
}

/** Movable holidays by days after Easter Sunday. */
const EASTER_HOLIDAYS: Record<number, string> = {
  1: 'Ostermontag',
  39: 'Christi Himmelfahrt',
  50: 'Pfingstmontag',
  60: 'Fronleichnam',
}

const DAY_MS = 86_400_000

/** Easter Sunday of a year as UTC midnight (Gregorian calendar, anonymous algorithm). */
function easterSunday(year: number): number {
  const a = year % 19, b = Math.floor(year / 100), c = year % 100
  const d = Math.floor(b / 4), e = b % 4
  const f = Math.floor((b + 8) / 25)
  const g = Math.floor((b - f + 1) / 3)
  const h = (19 * a + b - d - g + 15) % 30
  const i = Math.floor(c / 4), k = c % 4
  const w = (32 + 2 * e + 2 * i - h - k) % 7
  const m = Math.floor((a + 11 * h + 22 * w) / 451)
  const month = Math.floor((h + w - 7 * m + 114) / 31)
  const day = ((h + w - 7 * m + 114) % 31) + 1
  return Date.UTC(year, month - 1, day)
}

/** Name of the Austrian public holiday on the UTC calendar day of ``date``, or undefined. */
export function holidayName(date: Date): string | undefined {
  const fixed = FIXED_HOLIDAYS[`${date.getUTCMonth() + 1}-${date.getUTCDate()}`]
  if (fixed) return fixed
  const midnight = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate())
  return EASTER_HOLIDAYS[Math.round((midnight - easterSunday(date.getUTCFullYear())) / DAY_MS)]
}
