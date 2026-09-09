class MetricsUnavailable(RuntimeError):
    """This process could not read the metrics it was asked to serve.

    Raised only where render_metrics.py checks it: the merge directory is missing, unreadable or
    not a directory, prometheus_client failed on the files, or the rendered body carries no
    kinetix_build_info sample and therefore came from no worker at all. MetricsView turns it into
    503, because a 200 with no samples reads as "zero requests" on every dashboard built on it.
    """
