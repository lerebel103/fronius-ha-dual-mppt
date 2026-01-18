"""
Main controller for the Fronius Modbus to MQTT bridge application.

This module contains the core business logic for managing connections,
polling data, and handling errors.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

from .config import Config
from .modbus_client import ModbusClient
from .mqtt_publisher import MQTTPublisher

logger = logging.getLogger(__name__)


@dataclass
class ConnectionState:
    """Track connection states and retry counters."""

    modbus_connected: bool = False
    mqtt_connected: bool = False
    model_160_verified: bool = False
    device_info: Optional[dict] = None
    modbus_retry_count: int = 0
    mqtt_retry_count: int = 0
    model_160_retry_count: int = 0


def exponential_backoff(attempt: int, max_delay: int = 60) -> int:
    """
    Calculate exponential backoff delay.

    Args:
        attempt: Current attempt number (0-indexed)
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds (1s, 2s, 4s, 8s, ..., max 60s)
    """
    delay = min(2**attempt, max_delay)
    return delay


def handle_modbus_connection(
    modbus_client: ModbusClient, state: ConnectionState
) -> tuple[bool, Optional[float]]:
    """
    Handle Modbus connection and Model 160 verification.

    Args:
        modbus_client: The Modbus client instance
        state: Current connection state

    Returns:
        Tuple of (success, delay_seconds). If success is False, delay_seconds
        indicates how long to wait before retrying.
    """
    if state.modbus_connected:
        return True, None

    if modbus_client.connect():
        logger.info("Modbus connected successfully")
        state.modbus_connected = True
        state.modbus_retry_count = 0

        # Verify Model 160 after connection
        if modbus_client.verify_model_160():
            logger.info("Model 160 found and verified")
            state.model_160_verified = True
            state.model_160_retry_count = 0

            # Read device info from Model 1
            state.device_info = modbus_client.read_device_info()
            if state.device_info:
                logger.info(
                    f"Device identified: {state.device_info['manufacturer']} "
                    f"{state.device_info['model']} (S/N: {state.device_info['serial_number']})"
                )
            return True, None
        else:
            logger.warning("Model 160 not found, will retry")
            state.modbus_connected = False
            state.model_160_verified = False

            # Apply exponential backoff for Model 160 verification
            delay = exponential_backoff(state.model_160_retry_count)
            logger.info(f"Retrying Modbus connection in {delay} seconds...")
            state.model_160_retry_count += 1
            return False, delay
    else:
        # Connection failed, apply exponential backoff
        delay = exponential_backoff(state.modbus_retry_count)
        logger.error(f"Modbus connection failed, retrying in {delay} seconds...")
        state.modbus_retry_count += 1
        return False, delay


def handle_mqtt_connection(
    mqtt_publisher: MQTTPublisher, state: ConnectionState
) -> tuple[bool, Optional[float]]:
    """
    Handle MQTT connection and discovery message publishing.

    Args:
        mqtt_publisher: The MQTT publisher instance
        state: Current connection state

    Returns:
        Tuple of (success, delay_seconds). If success is False, delay_seconds
        indicates how long to wait before retrying.
    """
    if state.mqtt_connected:
        return True, None

    if mqtt_publisher.connect():
        logger.info("MQTT connected successfully")
        state.mqtt_connected = True
        state.mqtt_retry_count = 0

        # Publish discovery messages when MQTT connects
        if state.device_info:
            logger.info("Publishing MQTT discovery messages...")
            if mqtt_publisher.publish_discovery(state.device_info):
                logger.info("Discovery messages published successfully")
            else:
                logger.warning("Failed to publish some discovery messages")
        return True, None
    else:
        # Connection failed, apply exponential backoff
        delay = exponential_backoff(state.mqtt_retry_count)
        logger.error(f"MQTT connection failed, retrying in {delay} seconds...")
        state.mqtt_retry_count += 1
        return False, delay


def handle_data_polling(
    modbus_client: ModbusClient, mqtt_publisher: MQTTPublisher, state: ConnectionState
) -> None:
    """
    Handle MPPT data polling and publishing.

    Args:
        modbus_client: The Modbus client instance
        mqtt_publisher: The MQTT publisher instance
        state: Current connection state
    """
    if not (state.modbus_connected and state.model_160_verified):
        return

    # Poll MPPT data
    mppt_data = modbus_client.read_mppt_data()

    if mppt_data:
        # Publish to MQTT if connected
        if state.mqtt_connected:
            if not mqtt_publisher.publish_sensor_data(mppt_data):
                logger.warning("Failed to publish sensor data to MQTT")
                # Check if MQTT is still connected
                if not mqtt_publisher.is_connected():
                    logger.warning("MQTT connection lost, will attempt reconnection")
                    state.mqtt_connected = False
        else:
            logger.debug("MQTT not connected, skipping data publish")
    else:
        # Failed to read MPPT data, trigger Modbus reconnection
        logger.warning("Failed to read MPPT data, triggering Modbus reconnection")
        state.modbus_connected = False
        state.model_160_verified = False


def calculate_sleep_time(next_poll_time: float, poll_interval: int) -> tuple[float, float]:
    """
    Calculate sleep time and update next poll time to prevent drift.

    Args:
        next_poll_time: The scheduled time for the next poll
        poll_interval: The polling interval in seconds

    Returns:
        Tuple of (sleep_time, updated_next_poll_time)
    """
    current_time = time.time()
    sleep_time = next_poll_time - current_time

    if sleep_time < -poll_interval:
        # If we're more than one poll interval behind, reset the schedule
        logger.warning(f"Polling is {-sleep_time:.1f}s behind schedule, resetting timing")
        next_poll_time = current_time
        sleep_time = 0

    return sleep_time, next_poll_time + poll_interval


class FroniusBridgeController:
    """Main controller for the Fronius Modbus to MQTT bridge."""

    def __init__(self, config: Config):
        """
        Initialize the controller with configuration.

        Args:
            config: Application configuration
        """
        self.config = config
        self.modbus_client = ModbusClient(
            host=config.modbus_host,
            port=config.modbus_port,
            unit_id=config.modbus_unit_id,
            timeout=config.modbus_timeout,
        )
        self.mqtt_publisher = MQTTPublisher(
            broker=config.mqtt_broker,
            port=config.mqtt_port,
            username=config.mqtt_username,
            password=config.mqtt_password,
            client_id=config.mqtt_client_id,
            topic_prefix=config.mqtt_topic_prefix,
        )

    def run(self) -> None:
        """
        Run the main polling loop with resilient connection handling.
        """
        state = ConnectionState()

        # Track absolute time reference to prevent drift
        next_poll_time = time.time()

        try:
            while True:
                # Handle Modbus connection
                modbus_success, modbus_delay = handle_modbus_connection(self.modbus_client, state)
                if not modbus_success and modbus_delay:
                    next_poll_time = time.time() + modbus_delay
                    time.sleep(modbus_delay)
                    continue

                # Handle MQTT connection
                mqtt_success, mqtt_delay = handle_mqtt_connection(self.mqtt_publisher, state)
                if not mqtt_success and mqtt_delay:
                    next_poll_time = time.time() + mqtt_delay
                    time.sleep(mqtt_delay)
                    # Continue even if MQTT fails - we can still poll Modbus

                # Handle data polling
                handle_data_polling(self.modbus_client, self.mqtt_publisher, state)

                # Calculate sleep time and prevent drift
                sleep_time, next_poll_time = calculate_sleep_time(
                    next_poll_time, self.config.poll_interval
                )

                if sleep_time > 0:
                    time.sleep(sleep_time)

        finally:
            # Cleanup connections
            logger.info("Shutting down...")
            self.modbus_client.disconnect()
            self.mqtt_publisher.disconnect()
            logger.info("Shutdown complete")
