// jsdom doesn't implement SVG layout, which chart libraries (unovis) rely on.
if (typeof SVGGraphicsElement !== 'undefined' && !SVGGraphicsElement.prototype.getBBox) {
  SVGGraphicsElement.prototype.getBBox = () => ({ x: 0, y: 0, width: 0, height: 0 }) as DOMRect;
}

// jsdom has no real ResizeObserver; without one, unovis falls back to a
// polyfill that errors during test teardown. A no-op stub avoids that path.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
