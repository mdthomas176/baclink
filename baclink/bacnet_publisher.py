import logging
from .publisher import Publisher
import BAC0
log = logging.getLogger(__name__)

class BACnetPublisher(Publisher):

    def __init__(self, ip, device_id, device_name):
        import BAC0

        log.info("Starting bacnet stack")

        self.bacnet = BAC0.lite(
            ip=ip,
            deviceId=device_id,
            localObjName=device_name,
        )

        # Override the default BAC0 branding
        self.bacnet.this_application.localDevice.description = "My PLC Gateway"
        self.bacnet.this_application.localDevice.modelName = "PDM3 BACnet Gateway"
        self.bacnet.this_application.localDevice.vendorName = "YourCompanyName"

        self.objects={}

    def register_variables(self, variables):

        from BAC0.core.devices.local.models import(
            analog_input,
            binary_output,
            multistate_value,
            character_string,
            make_state_text,
        )

        log.info("Registering bacnet objects")

        for var in variables:
            log.debug(f"Register data type {var.data_type}")

            try:
                if var.data_type.lower() in ["float", "double", "int32", "int16", "uint32"]:
                    analog_input(
                        name=var.tagID,
                        description=var.path,
                    )
                
                elif var.data_type.lower() in ["bool", "boolean"]:
                    binary_output(
                        name=var.tagID,
                        description=var.path,
                    )

                else:
                    pass
    
            
            except Exception:
                log.exception(f"Failed creating bacnet object for {var.path}")
        
        status = character_string(
            name="Application_Status",
            description="Health/status",
            presentValue="Normal",
        )

        # Register all objects into the running application
        status.add_objects_to_application(self.bacnet)

    
    def publish_data(self, variables, init=False):
        
        for var in variables:
            log.debug(f"Updating {var.tagID}")
            changes = var.drain_changes()
            if not changes:
                log.debug(f"No changes for {var.tagID}")
                continue
            
            latest_value = changes[-1]["value"]

            try:
                self.bacnet[var.tagID].presentValue = latest_value
                log.debug(f"Updated {var.tagID} -> {latest_value}")
            except KeyError:
                log.warning(f"{var.tagID} not in bacnet")
            except Exception:
                log.exception(f"Failed updating bacnet value for {var.tagID}")
