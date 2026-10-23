from concurrent import futures
from typing import FrozenSet

import grpc
from catalog.v1 import catalog_pb2, catalog_pb2_grpc
from grpc_health.v1 import health, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

from core.infrastructure.grpc.catalog_servicer import CatalogServicer
from core.infrastructure.grpc.database_connection_interceptor import DatabaseConnectionInterceptor
from core.infrastructure.grpc.error_status_interceptor import ErrorStatusInterceptor
from core.infrastructure.grpc.request_id_interceptor import RequestIdInterceptor
from core.infrastructure.repositories import DjangoProductRepository
from core.infrastructure.security.peer_authorization_interceptor import PeerAuthorizationInterceptor

CATALOG_SERVICE_NAME: str = catalog_pb2.DESCRIPTOR.services_by_name["CatalogService"].full_name


def catalog_grpc_server(
    peers: FrozenSet[str],
    workers: int,
    health_servicer: health.HealthServicer,
) -> grpc.Server:
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=workers),
        interceptors=[
            RequestIdInterceptor(),
            PeerAuthorizationInterceptor(peers),
            ErrorStatusInterceptor(),
            DatabaseConnectionInterceptor(),
        ],
    )

    catalog_pb2_grpc.add_CatalogServiceServicer_to_server(CatalogServicer(DjangoProductRepository()), server)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    reflection.enable_server_reflection(
        (
            CATALOG_SERVICE_NAME,
            health.SERVICE_NAME,
            reflection.SERVICE_NAME,
        ),
        server,
    )

    return server
