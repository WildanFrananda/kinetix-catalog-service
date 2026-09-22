import logging
import signal
from concurrent import futures
from types import FrameType
from typing import Any, Optional

import grpc
from catalog.v1 import catalog_pb2, catalog_pb2_grpc
from django.core.management.base import BaseCommand
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

from core.infrastructure.grpc.catalog_servicer import CatalogServicer
from core.infrastructure.repositories import DjangoProductRepository
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

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=workers))

        catalog_pb2_grpc.add_CatalogServiceServicer_to_server(
            CatalogServicer(DjangoProductRepository()), server
        )

        health_servicer = health.HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

        reflection.enable_server_reflection(
            (
                catalog_pb2.DESCRIPTOR.services_by_name["CatalogService"].full_name,
                health.SERVICE_NAME,
                reflection.SERVICE_NAME,
            ),
            server,
        )

        bound = server.add_secure_port(
            f"0.0.0.0:{port}", server_credentials(options["pki_dir"])
        )
        if bound == 0:
            raise RuntimeError(f"could not bind port {port}")

        server.start()
        health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
        health_servicer.set(
            catalog_pb2.DESCRIPTOR.services_by_name["CatalogService"].full_name,
            health_pb2.HealthCheckResponse.SERVING,
        )
        logger.info("catalog gRPC serving on %s with mTLS required", bound)
        self.stdout.write(self.style.SUCCESS(f"catalog.v1 listening on {bound} (mTLS)"))

        def stop(signum: int, _frame: Optional[FrameType]) -> None:
            logger.info("signal %s received; draining", signum)
            health_servicer.enter_graceful_shutdown()
            server.stop(grace=10).wait()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        server.wait_for_termination()
