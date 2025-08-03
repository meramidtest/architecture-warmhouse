#!/usr/bin/env python3
import time
import json
import uuid
import random
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List
import pika
import os
from models import Database, DeviceManager


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelemetryWorker:
    def __init__(self):

        self.db = Database()
        self.device_manager = DeviceManager(self.db)
        

        self.rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port = int(os.environ.get('RABBITMQ_PORT', '5672'))
        self.rabbitmq_user = os.environ.get('RABBITMQ_USER', 'guest')
        self.rabbitmq_password = os.environ.get('RABBITMQ_PASSWORD', 'guest')
        self.telemetry_topic = 'telemetry'
        

        self.interval = 2
        self.running = False
        

        self.connection = None
        self.channel = None
        self._connect_to_rabbitmq()
    
    def _connect_to_rabbitmq(self):
        try:
            credentials = pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password)
            parameters = pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                credentials=credentials
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            

            self.channel.exchange_declare(exchange=self.telemetry_topic, exchange_type='topic', durable=True)
            
            logger.info(f"Connected to RabbitMQ at {self.rabbitmq_host}:{self.rabbitmq_port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
    
    def _generate_device_telemetry(self, device: Dict[str, Any]) -> Dict[str, Any]:
        device_type = device['type'].lower()
        base_telemetry = {}
        

        if 'temperature' in device_type or 'sensor' in device_type:
            base_telemetry = {
                'temperature': round(random.uniform(18.0, 30.0), 1),
                'humidity': round(random.uniform(30.0, 70.0), 1),
                'unit': 'celsius'
            }
        elif 'light' in device_type or 'bulb' in device_type:
            base_telemetry = {
                'status': random.choice(['on', 'off']),
                'brightness': random.randint(0, 100),
                'color': random.choice(['white', 'red', 'blue', 'green'])
            }
        elif 'door' in device_type or 'lock' in device_type:
            base_telemetry = {
                'status': random.choice(['locked', 'unlocked']),
                'battery_level': random.randint(20, 100),
                'last_access': datetime.utcnow().isoformat() + 'Z'
            }
        elif 'camera' in device_type:
            base_telemetry = {
                'status': 'recording',
                'resolution': '1080p',
                'motion_detected': random.choice([True, False]),
                'storage_used': random.randint(10, 90)
            }
        else:

            base_telemetry = {
                'status': random.choice(['online', 'offline']),
                'battery_level': random.randint(10, 100),
                'signal_strength': random.randint(-80, -20)
            }
        

        base_telemetry.update({
            'uptime': random.randint(3600, 86400),
            'firmware_version': '1.0.0'
        })
        
        return base_telemetry
    
    def _create_telemetry_event(self, device: Dict[str, Any], telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        telemetry_types = ['sensor_reading', 'status_update', 'device_metrics']
        

        telemetry_type = 'sensor_reading'
        if 'status' in telemetry_data:
            telemetry_type = 'status_update'
        elif 'uptime' in telemetry_data or 'firmware_version' in telemetry_data:
            telemetry_type = 'device_metrics'
        
        return {
            'telemetry_id': str(uuid.uuid4()),
            'device_id': device['device_id'],
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'type': telemetry_type,
            'value': telemetry_data
        }
    
    def _create_telemetry_batch(self, device_telemetry_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not device_telemetry_events:
            return None
        

        device_groups = {}
        for event in device_telemetry_events:
            device_id = event['device_id']
            if device_id not in device_groups:
                device_groups[device_id] = []
            device_groups[device_id].append({
                'telemetry_id': event['telemetry_id'],
                'type': event['type'],
                'timestamp': event['timestamp'],
                'value': event['value']
            })
        

        largest_device_id = max(device_groups.keys(), key=lambda k: len(device_groups[k]))
        telemetry_data = device_groups[largest_device_id]
        
        return {
            'batch_id': str(uuid.uuid4()),
            'device_id': largest_device_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'count': len(telemetry_data),
            'telemetry_data': telemetry_data
        }
    
    def _publish_telemetry_event(self, telemetry_event: Dict[str, Any]):
        if not self.channel:
            logger.warning("No RabbitMQ channel available, skipping telemetry publish")
            return
        
        try:
            message = {
                'messageType': 'telemetryReceived',
                'payload': telemetry_event
            }
            
            self.channel.basic_publish(
                exchange=self.telemetry_topic,
                routing_key='telemetry.received',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=2
                )
            )
            
            logger.debug(f"Published telemetry event for device {telemetry_event['device_id']}")
            
        except Exception as e:
            logger.error(f"Failed to publish telemetry event: {e}")
    
    def _publish_telemetry_batch(self, telemetry_batch: Dict[str, Any]):
        if not self.channel or not telemetry_batch:
            return
        
        try:
            message = {
                'messageType': 'telemetryBatch',
                'payload': telemetry_batch
            }
            
            self.channel.basic_publish(
                exchange=self.telemetry_topic,
                routing_key='telemetry.batch',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=2
                )
            )
            
            logger.debug(f"Published telemetry batch with {telemetry_batch['count']} events")
            
        except Exception as e:
            logger.error(f"Failed to publish telemetry batch: {e}")
    
    def _collect_and_publish_telemetry(self):
        try:

            devices = self.device_manager.get_all_devices()
            
            if not devices:
                logger.info("No devices registered, skipping telemetry collection")
                return
            
            logger.info(f"Collecting telemetry from {len(devices)} devices")
            
            telemetry_events = []
            
            for device in devices:
                try:

                    telemetry_data = self._generate_device_telemetry(device)
                    

                    self.device_manager.update_device_telemetry(device['device_id'], telemetry_data)
                    

                    telemetry_event = self._create_telemetry_event(device, telemetry_data)
                    telemetry_events.append(telemetry_event)
                    

                    self._publish_telemetry_event(telemetry_event)
                    
                except Exception as e:
                    logger.error(f"Failed to process telemetry for device {device['device_id']}: {e}")
            

            if len(telemetry_events) > 1 and random.randint(1, 3) == 1:
                telemetry_batch = self._create_telemetry_batch(telemetry_events)
                if telemetry_batch:
                    self._publish_telemetry_batch(telemetry_batch)
            
            logger.info(f"Successfully processed telemetry for {len(telemetry_events)} devices")
            
        except Exception as e:
            logger.error(f"Error in telemetry collection: {e}")
    
    def start(self):
        self.running = True
        logger.info(f"Starting telemetry worker with {self.interval}s interval")
        
        while self.running:
            try:
                self._collect_and_publish_telemetry()
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping worker...")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}")
                time.sleep(self.interval)
    
    def stop(self):
        self.running = False
        
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        
        logger.info("Telemetry worker stopped")

def main():
    logger.info("Initializing IoT Gateway Telemetry Worker...")
    
    worker = TelemetryWorker()
    
    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Shutting down telemetry worker...")
        worker.stop()
    except Exception as e:
        logger.error(f"Fatal error in telemetry worker: {e}")
        worker.stop()

if __name__ == '__main__':
    main() 