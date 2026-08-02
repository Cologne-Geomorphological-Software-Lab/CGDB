// Every data layer loads via a manual fetch() + addFeatures() call (see
// layers/*.js), not OpenLayers' declarative VectorSource({url, format})
// loader, so the usual featuresloadstart/featuresloadend source events never
// fire. Instead, wrap each loader call directly: flip the layer's spinner on
// before the call and off after, regardless of success or failure.
export function trackLoading(layerKey, setLayerLoading, loaderFn) {
  return async (...args) => {
    setLayerLoading(layerKey, true);
    try {
      return await loaderFn(...args);
    } finally {
      setLayerLoading(layerKey, false);
    }
  };
}
