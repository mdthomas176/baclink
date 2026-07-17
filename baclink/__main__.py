import logging
from baclink.opcua_connect import OPCUAManager
#from baclink.opcua_publisher import bacnetPublisher
from baclink import config
from baclink.bacnet_publisher import BACnetPublisher
import time

class SuppressBAC0Filter(logging.Filter):
    def filter(self, record):
        return not record.name.startswith("BAC0_Root")

logging.basicConfig(
    level=logging.INFO,  # minimum level to capture
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),              # console
        logging.FileHandler("baclink.log") # file
    ]
)

for name in ["opcua"]:
    logging.getLogger(name).setLevel(logging.WARNING)

def main():
    logging.info("Starting baclink...")

    publisher = BACnetPublisher(
        config.BACNET_ADDRESS,
        device_id=config.BACNET_DEVICE_ID,
        device_name=config.BACNET_DEVICE_NAME
    )

    opcuaLink = OPCUAManager(config.OPCUA_SERVER_URL, publisher=publisher)

    opcuaLink.connect()
    opcuaLink.load_vars()

    import threading
    poll_thread = threading.Thread(target=opcuaLink.poll_loop, daemon=True)
    poll_thread.start()

    logging.info("OPC UA polling started in background thread.")


    logging.info("suppressing BAC0 logging")
    for handler in logging.getLogger().handlers:
        handler.addFilter(SuppressBAC0Filter())

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shut down requested.")
        opcuaLink.stop()
        #opcuaLink.join()
    
    opcuaLink.poll_loop()


    


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,  # minimum level to capture
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),              # console
            logging.FileHandler("baclink.log") # file
        ]
    )

    

    main()