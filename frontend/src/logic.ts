export type FaultKind = 'latency' | 'http_errors' | 'timeout' | 'dependency_unavailable' | 'cpu_pressure'

export function buildFault(type: FaultKind, latencyMs: number, errorPercent: number) {
  if (type === 'latency' || type === 'timeout') {
    if (!Number.isInteger(latencyMs) || latencyMs < (type === 'timeout' ? 200 : 0) || latencyMs > 1000) {
      throw new Error('Latency must be within the supported range')
    }
    return { type, latency_ms: latencyMs }
  }
  if (type === 'http_errors') {
    if (!Number.isFinite(errorPercent) || errorPercent < 0 || errorPercent > 100) {
      throw new Error('Error rate must be between 0 and 100%')
    }
    return { type, error_rate: errorPercent / 100 }
  }
  return { type }
}
