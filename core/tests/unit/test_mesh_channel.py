from core.infrastructure.grpc.mesh_channel import mesh_channel_options


def _options() -> dict[str, int]:
    return dict(mesh_channel_options())


class TestMeshChannelOptions:
    def test_a_vanished_peer_is_retried_in_seconds_not_minutes(self) -> None:
        assert _options()["grpc.max_reconnect_backoff_ms"] <= 10_000

    def test_the_first_retry_is_quick(self) -> None:
        assert _options()["grpc.initial_reconnect_backoff_ms"] <= 1_000

    def test_the_name_is_resolved_again_quickly(self) -> None:
        assert _options()["grpc.dns_min_time_between_resolutions_ms"] <= 5_000

    def test_a_dead_connection_surfaces_as_a_failure_rather_than_a_hang(self) -> None:
        options = _options()
        assert options["grpc.keepalive_time_ms"] > 0
        assert options["grpc.keepalive_timeout_ms"] > 0

    def test_keepalive_runs_while_the_service_is_idle(self) -> None:
        assert _options()["grpc.keepalive_permit_without_calls"] == 1

    def test_every_option_is_a_grpc_option(self) -> None:
        for name in _options():
            assert name.startswith("grpc.")
