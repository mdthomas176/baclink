import logging

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

    import time
    import BAC0

    from BAC0.core.devices.local.models import (
        analog_input,
        character_string,
    )

    bacnet = BAC0.lite(
        ip="192.168.10.16/24",
        deviceId=199984,
        localObjName="MyDevice",
    )

    # Define objects,
    analog_input(
        name="TW1",
        description="Water temperature 1",
        properties={"units": "degreesCelsius"},
        presentValue=0.0,
    )

    character_string(
        name="Application_Status",
        description="Health",
        presentValue="Normal",
    )

    # Register all defined objects with the BACnet application,
    analog_input.add_objects_to_application(bacnet)

    def get_plc_value():
        # TODO: replace with your PLC read
        return 22.3

    while True:
        try:
            bacnet["TW1"].presentValue = float(get_plc_value())
            bacnet["Application_Status"].presentValue = "Normal"
        except Exception as e:
            bacnet["Application_Status"].presentValue = str(e)[:50]
        time.sleep(5)


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