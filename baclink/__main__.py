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

    import BAC0
    import time

    from BAC0.core.devices.local.models import (
        analog_input,
        binary_output,
        multistate_value,
        character_string,
        make_state_text,
    )

    # Start BAC0 - synchronous in this version, no async
    bacnet = BAC0.lite(ip="192.168.82.247/24", deviceId=199984, localObjName="Ecovie")

    # Override the default BAC0 branding
    bacnet.this_application.localDevice.description = "My PLC Gateway"
    bacnet.this_application.localDevice.modelName = "PDM3 BACnet Gateway"
    bacnet.this_application.localDevice.vendorName = "YourCompanyName"

    # Declare objects
    analog_input(
        name="TW1",
        description="Water temperature 1",
        properties={"units": "degreesCelsius"},
        presentValue=0.0,
    )
    binary_output(
        name="Night",
        description="Day/Night flag",
        properties={"inactiveText": "day", "activeText": "night"},
    )
    lang_states = make_state_text(["en", "fr"])
    multistate_value(
        name="Language",
        description="Language for requests",
        presentValue=1,
        properties={"stateText": lang_states},
    )
    status = character_string(
        name="Application_Status",
        description="Health/status",
        presentValue="Normal",
    )

    # Register all objects into the running application
    status.add_objects_to_application(bacnet)

    print("BACnet device running.")

    # Main loop
    while True:
        try:
            # Replace these with your actual PLC variable reads
            bacnet["TW1"].presentValue = 21.5
            bacnet["Night"].presentValue = False
            bacnet["Application_Status"].presentValue = "Normal"
        except Exception as e:
            bacnet["Application_Status"].presentValue = f"Error: {str(e)[:50]}"

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