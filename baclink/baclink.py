import BAC0
import time

from BAC0.core.devices.local.models import (
    analog_input,
    binary_output,
    multistate_value,
    character_string,
    make_state_text,
)


class baclinkPublisher:
    def __init__(self, ip_addr: str, deviceId, localObjName:str):
        self.address = ip_addr
        self.deviceId = deviceId
        self.localObjName=localObjName

        self.connect()
        
    def connect(self):
        self.bacnet = BAC0.lite(ip=self.address, deviceId=self.deviceId, localObjName=self.localObjName)
        
        self.bacnet.this_application.localDevice.description = "My PLC Gateway"
        self.bacnet.this_application.localDevice.modelName = "PDM3 BACnet Gateway"
        self.bacnet.this_application.localDevice.vendorName = "YourCompanyName"

        self.register_objects()

    
    def register_objects(self):
        #loop through objects from opcua server. 
        #based on type, declare the right object


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
        status.add_objects_to_application(self.bacnet)

        print("BACnet device running.")


    def update_objects(self):

        # Main loop
        while True:
            try:
                # Replace these with your actual PLC variable reads
                self.bacnet["TW1"].presentValue = 21.5
                self.bacnet["Night"].presentValue = False
                self.bacnet["Application_Status"].presentValue = "Normal"
            except Exception as e:
                self.bacnet["Application_Status"].presentValue = f"Error: {str(e)[:50]}"

            time.sleep(5)
