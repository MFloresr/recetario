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
