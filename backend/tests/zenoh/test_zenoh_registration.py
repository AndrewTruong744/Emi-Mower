from unittest.mock import Mock

from src.zenoh.register_handlers import register_handlers


def test_register_handlers_declares_queries_and_telemetry_subscriber():
    query_handler = Mock()
    message_handler = Mock()

    register_handlers(query_handler, message_handler)

    assert query_handler.declare.call_count == 7
    paths = [call.args[0] for call in query_handler.declare.call_args_list]
    assert paths == [
        "user/login",
        "user/add_mower",
        "user/update_name",
        "mower/*/update_name",
        "user/update_email",
        "mower/*/livekit/consume",
        "mower/*/livekit/upload",
    ]
    message_handler.declare.assert_called_once()
    assert message_handler.declare.call_args.args[0] == "mower/*/telemetry"
