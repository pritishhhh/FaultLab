import { describe, expect, it } from 'vitest'
import { buildFault } from './logic'

describe('fault configuration', () => {
  it('converts percentages and preserves latency', () => {
    expect(buildFault('http_errors', 0, 5)).toEqual({ type: 'http_errors', error_rate: .05 })
    expect(buildFault('latency', 300, 0)).toEqual({ type: 'latency', latency_ms: 300 })
  })
  it('rejects unsupported timeout and error values', () => {
    expect(() => buildFault('timeout', 100, 0)).toThrow()
    expect(() => buildFault('http_errors', 0, 101)).toThrow()
  })
})
