"""MQTT publisher for Home Assistant integration."""

import json
import logging
from typing import Dict, Optional

import paho.mqtt.client as mqtt

from .modbus_client import MPPTData

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """MQTT publisher for publishing MPPT data to Home Assistant."""

    def __init__(
        self,
        broker: str,
        port: int,
        username: str,
        password: str,
        client_id: str,
        topic_prefix: str,
    ) -> None:
        """
        Initialize MQTTPublisher with connection parameters.

        Args:
            broker: MQTT broker address
            port: MQTT broker port
            username: MQTT username
            password: MQTT password
            client_id: MQTT client ID
            topic_prefix: Topic prefix for MQTT messages (e.g., "homeassistant")
        """
        self._broker = broker
        self._port = port
        self._username = username
        self._password = password
        self._client_id = client_id
        self._topic_prefix = topic_prefix
        self._connected = False
        self._device_id: Optional[str] = None  # Store device ID for state topics

        # Create paho-mqtt client instance (using latest callback API version)
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=self._client_id
        )
        self._client.username_pw_set(self._username, self._password)

        # Set up callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: any,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: any,
    ) -> None:
        """Callback for when the client connects to the broker."""
        if reason_code == 0:
            logger.info("MQTT connected successfully")
            self._connected = True
        else:
            logger.error(f"MQTT connection failed with code {reason_code}")
            self._connected = False

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: any,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: any,
    ) -> None:
        """Callback for when the client disconnects from the broker."""
        logger.warning(f"MQTT disconnected with code {reason_code}")
        self._connected = False

    def connect(self) -> bool:
        """
        Attempt MQTT connection to the broker.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Attempting MQTT connection to {self._broker}:{self._port}")

            # Reset connection state
            self._connected = False

            # Start the connection
            result = self._client.connect(self._broker, self._port, keepalive=60)

            if result != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"MQTT connection initiation failed with code {result}")
                return False

            # Start the network loop
            self._client.loop_start()

            # Wait for connection to be established (with timeout)
            import time

            timeout = 10  # 10 second timeout
            start_time = time.time()

            while not self._connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)  # Check every 100ms

            if self._connected:
                logger.info("MQTT connection established successfully")
                return True
            else:
                logger.error(
                    "MQTT connection timeout - connection not established within 10 seconds"
                )
                self._client.loop_stop()
                return False

        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        try:
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("MQTT connection closed")
        except Exception as e:
            logger.warning(f"Error during MQTT disconnect: {e}")
        finally:
            self._connected = False

    def is_connected(self) -> bool:
        """
        Check if connected to the MQTT broker.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    def publish_discovery(self, device_info: Dict[str, str]) -> bool:
        """
        Publish Home Assistant MQTT discovery messages for all sensors.

        Args:
            device_info: Dictionary with manufacturer, model, and serial_number

        Returns:
            True if all discovery messages published successfully, False otherwise
        """
        if not self._connected:
            logger.error("Cannot publish discovery: not connected to MQTT broker")
            return False

        try:
            serial = device_info.get("serial_number", "unknown")
            manufacturer = device_info.get("manufacturer", "Unknown")
            model = device_info.get("model", "Unknown")

            # Store device ID for use in publish_sensor_data
            device_id = f"fronius_{serial}"
            self._device_id = device_id

            # Device information shared by all sensors
            device = {
                "identifiers": [f"fronius_{serial}"],
                "name": f"{manufacturer} {model}",
                "manufacturer": manufacturer,
                "model": model,
                "serial_number": serial,
            }

            # Define all sensors (PV1/2 voltage, current, power + total power)
            sensors = [
                # PV1 sensors (MPPT1)
                {
                    "id": "pv1_voltage",
                    "name": "PV1 Voltage",
                    "unit": "V",
                    "device_class": "voltage",
                    "value_template": "{{ value_json.voltage }}",
                },
                {
                    "id": "pv1_current",
                    "name": "PV1 Current",
                    "unit": "A",
                    "device_class": "current",
                    "value_template": "{{ value_json.current }}",
                },
                {
                    "id": "pv1_power",
                    "name": "PV1 Power",
                    "unit": "W",
                    "device_class": "power",
                    "value_template": "{{ value_json.power }}",
                },
                # PV2 sensors (MPPT2)
                {
                    "id": "pv2_voltage",
                    "name": "PV2 Voltage",
                    "unit": "V",
                    "device_class": "voltage",
                    "value_template": "{{ value_json.voltage }}",
                },
                {
                    "id": "pv2_current",
                    "name": "PV2 Current",
                    "unit": "A",
                    "device_class": "current",
                    "value_template": "{{ value_json.current }}",
                },
                {
                    "id": "pv2_power",
                    "name": "PV2 Power",
                    "unit": "W",
                    "device_class": "power",
                    "value_template": "{{ value_json.power }}",
                },
                # Total power sensor
                {
                    "id": "total_power",
                    "name": "Total DC Power",
                    "unit": "W",
                    "device_class": "power",
                    "value_template": "{{ value_json.power }}",
                },
            ]

            # Publish discovery message for each sensor
            for sensor in sensors:
                sensor_id = sensor["id"]
                device_id = f"fronius_{serial}"

                # Discovery topic pattern: {prefix}/sensor/{device_id}/{sensor_id}/config
                discovery_topic = f"{self._topic_prefix}/sensor/{device_id}/{sensor_id}/config"

                # State topic pattern: {prefix}/sensor/{device_id}/{sensor_id}/state
                state_topic = f"{self._topic_prefix}/sensor/{device_id}/{sensor_id}/state"

                # Build discovery payload
                discovery_payload = {
                    "name": sensor["name"],
                    "unique_id": f"{device_id}_{sensor_id}",
                    "state_topic": state_topic,
                    "unit_of_measurement": sensor["unit"],
                    "device_class": sensor["device_class"],
                    "state_class": "measurement",
                    "value_template": sensor["value_template"],
                    "expire_after": 3600,  # Sensor becomes unavailable after 1 hour without data
                    "device": device,
                }

                # Publish discovery message
                result = self._client.publish(
                    discovery_topic, json.dumps(discovery_payload), qos=1, retain=True
                )

                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    logger.error(f"Failed to publish discovery for {sensor_id}: {result.rc}")
                    return False

                logger.debug(f"Published discovery for {sensor_id}")

            logger.info(f"Published discovery messages for {len(sensors)} sensors")
            return True

        except Exception as e:
            logger.error(f"Error publishing discovery messages: {e}")
            return False

    def publish_sensor_data(self, mppt_data: MPPTData) -> bool:
        """
        Publish MPPT sensor data to MQTT state topics.

        Args:
            mppt_data: MPPTData object containing readings from both MPPT channels

        Returns:
            True if all data published successfully, False otherwise
        """
        if not self._connected:
            logger.error("Cannot publish sensor data: not connected to MQTT broker")
            return False

        if not self._device_id:
            logger.error(
                "Cannot publish sensor data: device_id not set. " "Call publish_discovery() first."
            )
            return False

        try:
            device_id = self._device_id
            timestamp = mppt_data.timestamp.isoformat()

            # Publish PV1 data (MPPT1)
            pv1_data = [
                ("pv1_voltage", {"voltage": mppt_data.mppt1.voltage, "timestamp": timestamp}),
                ("pv1_current", {"current": mppt_data.mppt1.current, "timestamp": timestamp}),
                ("pv1_power", {"power": mppt_data.mppt1.power, "timestamp": timestamp}),
            ]

            # Publish PV2 data (MPPT2)
            pv2_data = [
                ("pv2_voltage", {"voltage": mppt_data.mppt2.voltage, "timestamp": timestamp}),
                ("pv2_current", {"current": mppt_data.mppt2.current, "timestamp": timestamp}),
                ("pv2_power", {"power": mppt_data.mppt2.power, "timestamp": timestamp}),
            ]

            # Publish total power
            total_power_data = [
                ("total_power", {"power": mppt_data.total_power, "timestamp": timestamp}),
            ]

            # Combine all sensor data
            all_sensor_data = pv1_data + pv2_data + total_power_data

            # Publish each sensor's data
            for sensor_id, payload in all_sensor_data:
                state_topic = f"{self._topic_prefix}/sensor/{device_id}/{sensor_id}/state"

                result = self._client.publish(state_topic, json.dumps(payload), qos=0, retain=False)

                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    logger.error(f"Failed to publish data for {sensor_id}: {result.rc}")
                    return False

            logger.debug(
                f"Published sensor data: PV1={mppt_data.mppt1.power}W, "
                f"PV2={mppt_data.mppt2.power}W, Total={mppt_data.total_power}W"
            )
            return True

        except Exception as e:
            logger.error(f"Error publishing sensor data: {e}")
            return False
