from unittest.mock import Mock

from src.zenoh.register_handlers import register_handlers


def test_register_handlers_declares_login_and_livekit_queries():
    handler = Mock()

    register_handlers(handler)

    assert handler.declare.call_count == 3
    paths = [call.args[0] for call in handler.declare.call_args_list]
    assert paths == [
        "user/login",
        "mower/*/livekit/consume",
        "mower/*/livekit/upload",
    ]
