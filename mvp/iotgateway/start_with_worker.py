#!/usr/bin/env python3
import threading
import logging
import signal
import sys
import time
from app import app, logger as api_logger
from telemetry_worker import TelemetryWorker


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IoTGatewayService:
    def __init__(self):
        self.telemetry_worker = None
        self.api_thread = None
        self.worker_thread = None
        self.running = False
        

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.stop()
        sys.exit(0)
    
    def _run_api_server(self):
        try:
            api_logger.info("Starting IoT Gateway API server...")
            app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"API server error: {e}")
    
    def _run_telemetry_worker(self):
        try:
            self.telemetry_worker = TelemetryWorker()
            self.telemetry_worker.start()
        except Exception as e:
            logger.error(f"Telemetry worker error: {e}")
    
    def start(self):
        self.running = True
        logger.info("Starting IoT Gateway Service...")
        

        self.api_thread = threading.Thread(target=self._run_api_server, daemon=True)
        self.api_thread.start()
        logger.info("API server thread started")
        

        self.worker_thread = threading.Thread(target=self._run_telemetry_worker, daemon=True)
        self.worker_thread.start()
        logger.info("Telemetry worker thread started")
        

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
            self.stop()
    
    def stop(self):
        logger.info("Stopping IoT Gateway Service...")
        self.running = False
        

        if self.telemetry_worker:
            self.telemetry_worker.stop()
        
        logger.info("IoT Gateway Service stopped")

def main():
    logger.info("Initializing IoT Gateway Service with API and Telemetry Worker...")
    
    service = IoTGatewayService()
    
    try:
        service.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        service.stop()

if __name__ == '__main__':
    main() 