import logging
from baclink.opcua_connect import OPCUAManager
from baclink.opcua_publisher import bacnetPublisher
from baclink import config
from baclink.bacnet_publisher import BACnetPublisher
import time

logging.basicConfig(
    level=logging.DEBUG,  # minimum level to capture
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),              # console
        logging.FileHandler("baclink.log") # file
    ]
)

def main():
    logging.info("Starting baclink...")

    publisher = BACnetPublisher(
        ip="192.168.82.247/24",
        device_id=199984,
        device_name="Ecovie"
    )

    opcuaLink = OPCUAManager(config.OPCUA_SERVER_URL, publisher=publisher)

    opcuaLink.connect()
    opcuaLink.load_vars()

    import threading
    poll_thread = threading.Thread(target=opcuaLink.poll_loop, daemon=True)
    poll_thread.start()

    logging.info("OPC UA polling started in background thread.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down.")
    
    opcuaLink.poll_loop()


    


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,  # minimum level to capture
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),              # console
            logging.FileHandler("baclink.log") # file
        ]
    )


    

    main()