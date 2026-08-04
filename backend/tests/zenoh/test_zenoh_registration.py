from unittest.mock import Mock

from src.zenoh.register_handlers import register_handlers


def test_register_handlers_declares_login_query():
    handler = Mock()

    register_handlers(handler)

    handler.declare.assert_called_once()
    assert handler.declare.call_args.args[0] == "user/login"
