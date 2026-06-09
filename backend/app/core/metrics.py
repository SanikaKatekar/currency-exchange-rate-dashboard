"""
Prometheus metrics exposed at ``/metrics``.

Overview:
    Defines counters and histograms used to observe API latency, cache behavior,
    retry activity, offline fallback usage, and circuit breaker events.

Metrics:
    REQUEST_LATENCY: Histogram of API endpoint latency in seconds.
    CACHE_HITS: Counter of FX cache hits.
    CACHE_MISSES: Counter of FX cache misses.
    RETRIES: Counter of Frankfurter HTTP retry attempts.
    FALLBACKS: Counter of offline fallback activations.
    CIRCUIT_OPENS: Counter of circuit breaker open events.
"""

from prometheus_client import Counter, Histogram

REQUEST_LATENCY: Histogram = Histogram(
    "fx_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"],
)
CACHE_HITS: Counter = Counter("fx_cache_hits_total", "FX cache hits")
CACHE_MISSES: Counter = Counter("fx_cache_misses_total", "FX cache misses")
RETRIES: Counter = Counter("fx_retries_total", "FX API retry attempts")
FALLBACKS: Counter = Counter("fx_fallbacks_total", "Offline fallback activations")
CIRCUIT_OPENS: Counter = Counter("fx_circuit_opens_total", "Circuit breaker open events")
