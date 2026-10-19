// Vuetify usa APIs del navegador que jsdom no trae
class ResizeObserverFalso {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverFalso as unknown as typeof ResizeObserver

if (!window.matchMedia) {
  window.matchMedia = (consulta: string) =>
    ({
      matches: false,
      media: consulta,
      onchange: null,
      addEventListener() {},
      removeEventListener() {},
      addListener() {},
      removeListener() {},
      dispatchEvent: () => false,
    }) as MediaQueryList
}

// Los diálogos de Vuetify consultan el viewport visual
if (!('visualViewport' in globalThis)) {
  Object.defineProperty(globalThis, 'visualViewport', {
    value: { width: 1024, height: 768, scale: 1, addEventListener() {}, removeEventListener() {} },
  })
}
