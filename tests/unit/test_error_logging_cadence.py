"""
Tests for edge-triggered connection error logging.

These verify the logging strategy: an error condition is reported once at ERROR
when it starts, stays quiet (DEBUG) while it persists, and recovery is reported
once at INFO — so a sustained outage does not spam the log every cycle.
"""

import logging
from unittest.mock import Mock

from app.controller import ConnectionState, handle_modbus_connection, handle_mqtt_connection


class TestErrorLoggingCadence:
    """Verify start/end edge-triggered logging for connection failures."""

    def test_modbus_failure_logged_once_then_quiet(self, caplog):
        """A sustained Modbus outage logs ERROR once, then only DEBUG."""
        client = Mock()
        client.connect.return_value = False
        client.last_error = "connection refused"
        state = ConnectionState()

        with caplog.at_level(logging.DEBUG, logger="app.controller"):
            handle_modbus_connection(client, state)
            errors = [r for r in caplog.records if r.levelno == logging.ERROR]
            assert len(errors) == 1
            assert "connection refused" in errors[0].message
            assert state.modbus_failure_logged is True

            caplog.clear()
            for _ in range(5):
                handle_modbus_connection(client, state)

            assert [r for r in caplog.records if r.levelno == logging.ERROR] == []
            assert [r for r in caplog.records if r.levelno == logging.DEBUG] != []

    def test_modbus_recovery_logged_once_at_info(self, caplog):
        """Recovery after a failure logs a single INFO 'restored' message."""
        client = Mock()
        client.connect.return_value = False
        client.last_error = "connection refused"
        state = ConnectionState()
        handle_modbus_connection(client, state)  # latch failure state

        # Simulate the inverter coming back.
        client.connect.return_value = True
        client.verify_model_160.return_value = True
        client.read_device_info.return_value = None

        with caplog.at_level(logging.INFO, logger="app.controller"):
            caplog.clear()
            success, _ = handle_modbus_connection(client, state)

        assert success is True
        infos = [r for r in caplog.records if r.levelno == logging.INFO]
        assert any("restored" in r.message for r in infos)
        assert state.modbus_failure_logged is False

    def test_mqtt_failure_logged_once_then_quiet(self, caplog):
        """A sustained MQTT outage logs ERROR once, then only DEBUG."""
        publisher = Mock()
        publisher.connect.return_value = False
        publisher.last_error = "connection timeout"
        state = ConnectionState()
        config = Mock()

        with caplog.at_level(logging.DEBUG, logger="app.controller"):
            handle_mqtt_connection(publisher, state, config)
            errors = [r for r in caplog.records if r.levelno == logging.ERROR]
            assert len(errors) == 1
            assert "connection timeout" in errors[0].message
            assert state.mqtt_failure_logged is True

            caplog.clear()
            for _ in range(5):
                handle_mqtt_connection(publisher, state, config)

            assert [r for r in caplog.records if r.levelno == logging.ERROR] == []
            assert [r for r in caplog.records if r.levelno == logging.DEBUG] != []
