import logging
import signal
from types import FrameType
from typing import Any, Optional

from django.core.management.base import BaseCommand
from grpc_health.v1 import health, health_pb2

from core.infrastructure.grpc.catalog_grpc_server import CATALOG_SERVICE_NAME, catalog_grpc_server
from core.infrastructure.security.allowed_peers import allowed_peers
from core.infrastructure.security.server_credentials import server_credentials

logger = logging.getLogger(__name__)

DEFAULT_PORT = 50058
DEFAULT_WORKERS = 8


class Command(BaseCommand):
    help = "Serve catalog.v1 over mTLS for read models that keep a copy of the catalogue."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--port", type=int, default=DEFAULT_PORT)
        parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
        parser.add_argument(
            "--pki-dir",
            default=None,
            help="Where ca.pem, tls.crt and tls.key live. Defaults to KINETIX_PKI_DIR.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        port: int = options["port"]
        workers: int = options["workers"]

        peers = allowed_peers()
        health_servicer = health.HealthServicer()
        server = catalog_grpc_server(peers, workers, health_servicer)

        bound = server.add_secure_port(f"0.0.0.0:{port}", server_credentials(options["pki_dir"]))
        if bound == 0:
            raise RuntimeError(f"could not bind port {port}")

        server.start()
        health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
        health_servicer.set(CATALOG_SERVICE_NAME, health_pb2.HealthCheckResponse.SERVING)
        logger.info(
            "catalog gRPC serving on %s with mTLS required; callers allowed: %s",
            bound,
            ",".join(sorted(peers)),
        )
        self.stdout.write(self.style.SUCCESS(f"catalog.v1 listening on {bound} (mTLS)"))

        def stop(signum: int, _frame: Optional[FrameType]) -> None:
            logger.info("signal %s received; draining", signum)
            health_servicer.enter_graceful_shutdown()
            server.stop(grace=10).wait()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        server.wait_for_termination()
