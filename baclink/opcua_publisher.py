import ssl
import json
import time
from baclink import config

import logging
log = logging.getLogger(__name__)

from abc import ABC, abstractmethod

class Publisher(ABC):
    @abstractmethod
    def publish(self, data: dict):
        pass

class mqttPublisher:
    
    # Callbacks
    def on_connect(self, client, userdata, flags, reasonCode):
        log.info(f"Connected with result code {reasonCode}")

    def on_publish(self, client, userdata, mid):
        log.info(f"Message {mid} published")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            log.warning("Unexepected disconnection from MQTT broker.")
        else:
            log.info("Disconnected from MQTT broker.")

    def on_loop_stop(self, client, userdata, rc):
        log.info(f"mqtt loop stopped.")

    def mqttConnect(self):
        #configure tls context:
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = True

            context.load_verify_locations(cafile=config.CA_PATH)
            context.load_cert_chain(certfile=config.CERT_PATH, keyfile=config.KEY_PATH)
            self.client.tls_set_context(context=context)
            self.client.tls_insecure_set(False)
            log.debug("tls set")

            self.client.connect(config.ENDPOINT, config.PORT, keepalive=60)
            log.debug(f"connected to aws mqtt broker at {config.ENDPOINT}, port {config.PORT}")
            log.debug("Starting MQTT loop")
            self.client.loop_start()
            log.debug("Started MQTT loop")
            log.info(f"Connected to aws mqtt broker at {config.ENDPOINT}")

        except Exception as e:
            log.error(f"Error connecting to mqtt broker: {e}")
            raise ConnectionError(f"Failed to connect to mqtt broker")
            #raise RuntimeError("Failed to connect to mqtt broker")

    def __init__(self):
        import paho.mqtt.client as mqtt

        try:
            self.client = mqtt.Client(client_id=config.CLIENT_ID)
            self.client.on_connect = self.on_connect
            self.client.on_publish = self.on_publish
            self.client.on_disconnect = self.on_disconnect

            self.client.enable_logger(log)

            self.mqttConnect()
        except ConnectionError:
            log.warning(f"Failed to connect to mqtt broker")
        except Exception as e:
            log.exception(f"Exception initializing mqtt Publisher: {e}")
            #raise RuntimeError("Failed to initialize mqtt Publisher")

    def mqttPacketFormat(self, tagID, time, value, Q=1):
        packet = {
            "ID": tagID,
            "T" : time,
            "Q" : Q,
            "V" : value
        }
        log.debug(f"created packet: {packet}")
        return packet

    def generate_payload(self, variables):
        payload = []
        log.debug(f"generating payload")
        for var in variables:
            log.debug(f"appending {var.tagID} to payload")
            changes = var.drain_changes()
            log.debug(f"found {len(changes)} changes")
            for change in changes:
                log.debug(f"appending change {change} to payload")
                payload.append(
                    self.mqttPacketFormat(
                        tagID=var.tagID,
                        time=change['time'],
                        value=change['value'],
                        Q=1
                    )
                )
        
        return payload
    
    def try_publish_payload(self, topic, payload_list):
        if not self.client.is_connected():
            log.warning("MQTT client is not connected. Skipping publish.")
            return None  # Skip publish

        try:
            log.debug(f"{payload_list}")
            payload_str = json.dumps(payload_list)
            payload_bytes = payload_str.encode('utf-8')

            log.info(f"payload size: {len(payload_bytes)} bytes")

            if len(payload_bytes) > config.MAX_MQTT_PAYLOAD_SIZE:
                log.warning(f"Payload size {len(payload_bytes)} exceeds max {config.MAX_MQTT_PAYLOAD_SIZE}. Skipping publish.")
                return None  # Skip publish
            
            result = self.client.publish(topic, payload_str)
            return result
        
        except Exception as e:
            log.exception(f"Unhandled exception in mqttPublisher.try_publish_payload")
        return None  # Return
    
    
    
    def publish_data(self, variables, init=False):
        
        try:           
            payload = self.generate_payload(variables)
            if not payload:
                log.warning("No changes to publish")
            else:
                if init:
                    log.info(f"Publishing initial payload to station data topic with{len(payload)} values")
                    result = self.try_publish_payload(topic=config.TOPIC_STATION, payload_list=payload)
                    time.sleep(5) #wait for station data to publish.

                log.info(f"publishing payload to live data with {len(payload)} changes")
                self.try_publish_payload(topic=config.TOPIC_LIVE, payload_list=payload)

        except Exception as e:
            log.exception(f"unhandled exception in mqttPublisher.publish_data: {e}")

class bacnetPublisher:
    def __init__(self, ip_addr: str, deviceId, localObjName:str):
        import BAC0
        from BAC0.core.devices.local.models import (
            analog_input,
            binary_output,
            multistate_value,
            character_string,
            make_state_text,
        )
        self.address = ip_addr
        self.deviceId = deviceId
        self.localObjName=localObjName
        BAC0.log_level("silence")
    
    def register_objects(self, variables):
        for var in variables:
            if var.data_type in ['Float']:
                analog_input(
                    name=var.path,
                    description=var.path,
                    
                )

    def publish_data(self, variables, init=False):
        log.info("publish data")


# influxdb_publisher
class influxdbPublisher:
    def __init__(self, url, token, org, bucket):
        from influxdb_client import InfluxDBClient, Point
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api()
        self.bucket = bucket

    def publish(self, data: dict):
        log.info(f"Publishing payload to live data")
        try:
            point = Point(data['measurement']).tag(data['tags']).field(data['field'], data["value"])
        except KeyError as e:
            log.exception(f"Missing influx data in payload {data}: {e}")
        except Exception as e:
            log.exception(f"Unhandled exception in influxdbPublisher.publish: {e}")
            
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        
    def publish_data(self, variables, init=False):
        if init:
            log.info(f"Publishing initial payload to station data topic with{len(variables)} values")
            self.client.write_points(variables)
        else:
            log.info(f"publishing payload to live data with {len(variables)} changes")
            self.client.write_points(variables)