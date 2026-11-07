/** Attribute that keeps an element and its children out of the exported SVG (e.g. hover layers). */
export const EXPORT_SKIP = 'data-export-skip'

const SVG_NS = 'http://www.w3.org/2000/svg'

/**
 * Computed properties written into every exported element, with their initial values: a value equal to it is left out,
 * which keeps the file small. Without them the copy would lose everything the CSS modules and custom properties set.
 */
const STYLE_DEFAULTS: Record<string, string> = {
  fill: 'rgb(0, 0, 0)',
  'fill-opacity': '1',
  stroke: 'none',
  'stroke-width': '1px',
  'stroke-dasharray': 'none',
  'stroke-linecap': 'butt',
  'stroke-linejoin': 'miter',
  'stroke-opacity': '1',
  opacity: '1',
  'text-anchor': 'start',
}
const TEXT_STYLE = ['font-size', 'font-weight'] as const

/** Inline style of the computed values of an element that differ from their initial values. */
function inlineStyle(element: Element): string {
  const computed = getComputedStyle(element)
  const parts = Object.entries(STYLE_DEFAULTS)
    .map(([name, initial]) => [name, computed.getPropertyValue(name), initial])
    .filter(([, value, initial]) => value !== '' && value !== initial)
    .map(([name, value]) => `${name}:${value}`)
  if (element instanceof SVGTextElement) parts.push(...TEXT_STYLE.map((name) => `${name}:${computed.getPropertyValue(name)}`))
  return parts.join(';')
}

/**
 * Standalone copy of a rendered SVG as markup: computed styles inlined, classes and elements marked with EXPORT_SKIP
 * removed, size from the viewBox, the font of the page and a background rectangle, so it looks the same outside the
 * app.
 */
export function standaloneSvg(svg: SVGSVGElement, background: string): string {
  const copy = svg.cloneNode(true) as SVGSVGElement
  // Clone and original list their descendants in the same order; styles are read before anything is removed.
  const originals = svg.querySelectorAll('*')
  copy.querySelectorAll('*').forEach((element, i) => {
    const style = element instanceof SVGGElement ? '' : inlineStyle(originals[i])
    if (style !== '') element.setAttribute('style', style)
    element.removeAttribute('class')
  })
  copy.querySelectorAll(`[${EXPORT_SKIP}]`).forEach((element) => element.remove())

  const { width, height } = svg.viewBox.baseVal
  copy.removeAttribute('class')
  copy.setAttribute('xmlns', SVG_NS)
  copy.setAttribute('width', String(width))
  copy.setAttribute('height', String(height))
  copy.setAttribute('font-family', getComputedStyle(svg).fontFamily)
  const backdrop = document.createElementNS(SVG_NS, 'rect')
  backdrop.setAttribute('width', '100%')
  backdrop.setAttribute('height', '100%')
  backdrop.setAttribute('fill', background)
  copy.prepend(backdrop)
  return `<?xml version="1.0" encoding="UTF-8"?>\n${new XMLSerializer().serializeToString(copy)}`
}

/** Saves the SVG as a file through a temporary object URL. */
export function downloadSvg(svg: SVGSVGElement, fileName: string, background: string): void {
  const blob = new Blob([standaloneSvg(svg, background)], { type: 'image/svg+xml' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  // Released later: some browsers read the URL only after click() has returned.
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
