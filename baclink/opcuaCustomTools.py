import threading
from opcua import Client, ua, Node
import logging
import os

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import json
from datetime import timezone, datetime

log = logging.getLogger(__name__)

def find_node_by_browse_name(start_node, target_name):
    """
    Recursively search for a node by its browse name.
    Returns the first match found.
    """
    for child in start_node.get_children():
        browse_name = child.get_browse_name().Name
        if browse_name == target_name:
            log.info(f"Found node: {target_name}")
            return child
        if child.get_node_class() == ua.NodeClass.Object:
            result = find_node_by_browse_name(child, target_name)
            if result:
                return result

def browse_variables(client, node, path=""):
    """
    Recursively search for all variables under the given node.
    Returns list of tuples (full_path, child)
    """
    variables = []
    for child in node.get_children():
        try:
            child_node_class = child.get_node_class()
            child_browse_name = child.get_browse_name().Name
            full_path = f"{path}/{child_browse_name}"
            if child_node_class == ua.NodeClass.Variable:
                log.info(f"Found variable at: {full_path}")
                try:
                    typeNodeid = child.get_data_type()
                    data_type = client.get_node(typeNodeid).get_display_name().Text
                    log.debug(f"data_type: {data_type}")
                    tagID = data_type + "." + '.'.join(full_path.split('/')[2:])
                    log.debug(f"tagID: {tagID}")
                    opcVar = OPCVariable(
                        node_id = child.nodeid.to_string(),
                        path=full_path,
                        data_type=data_type,
                        tagID = tagID,
                        update_method=UpdateMethod.POLL
                    )
                    opcVar.node = child
                    variables.append(opcVar)
                except Exception as e:
                    log.warning(f"Failed to registering variable at {full_path}: {e}")
                
            elif child_node_class in (ua.NodeClass.Object, ua.NodeClass.View):
                # Recurse into objects
                variables.extend(browse_variables(client, child, full_path))
        except Exception as e:
            log.warning(f"Failed to browse child. Nodeid: {child.nodeid.to_string()}. Error: {e}")
    return variables

class UpdateMethod(Enum):
    POLL = "poll"
    SUBSCRIBE = "subscribe"
    IGNORE = "ignore"

@dataclass
class OPCVariable:
    node_id: str
    path: str
    data_type: str
    tagID: str
    update_method: UpdateMethod


    #node is set later, not during init
    node: Optional[Node] = field(default=None, init=False, repr=False, compare=False)

    def __init__(self, node_id: str, path: str, data_type: str, tagID: str, update_method: UpdateMethod):
        self.node_id = node_id
        self.path = path
        self.data_type = data_type
        self.tagID = tagID
        self.update_method = update_method
        self.node = None
        self.change_buffer = []
        self.lock = threading.Lock()
        self.last_recorded_time = None

    def record_value(self, value, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # convert the value to a string if it's not already
        try:
            json.dumps(value)
            serializable_value = value
        except Exception as e:
            log.warning(f"Value {value} is not JSON serializable. Using string representation instead.")
            serializable_value = str(value)
        finally:
            with self.lock:
                log.debug(f"Adding value to buffer for variable {self.tagID}: {value}")
                self.change_buffer.append({
                    "value": serializable_value,
                    "time": timestamp
                })
            self.last_recorded_time = datetime.now(timezone.utc)
            log.debug(f"last_recorded_time: {self.last_recorded_time}")
    
    def drain_changes(self):
        with self.lock:
            drained = self.change_buffer[:]
            self.change_buffer.clear()
            self.last_published_time = datetime.now(timezone.utc)
            return drained
    
        
    def to_dict(self):
        return {
            "node_id": self.node_id,
            "path": self.path,
            "data_type": self.data_type,
            "tagID": self.tagID,
            "update_method": self.update_method.value,
        }

    
    @classmethod
    def from_dict(cls, data):
        data["update_method"] = UpdateMethod(data["update_method"]) # restore enum
        return cls(**data)

def save_config(opc_vars, filename="vars/opc_vars.json"):
    log.info(f"Saving variables to {filename}")
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump([var.to_dict() for var in opc_vars], f, indent=2)
    except Exception as e:
        log.warning(f"Error generating file: {e}")

def load_config(filename="vars/opc_vars.json"):
    log.info(f"Reading variables from {filename}")
    try:
        with open(filename, "r") as f:
            data = json.load(f)
        return [OPCVariable.from_dict(item) for item in data]
    except FileNotFoundError as e:
        log.info("Variable file {filename} not found.")
        return None
    except Exception as e:
        log.warning(f"Error reading file: {e}")
        return None
            
if __name__ == "__main__":
    # Example test code (you can customize this)
    client = Client("opc.tcp://localhost:4840")
    try:
        client.connect()
        root = client.get_root_node()
        print("Connected. Searching from root...")
        #node = search_children(root, "MyTargetDisplayName")
        #if node:
        #    print("Found:", node)
        #else:
        #    print("Not found.")
    finally:
        client.disconnect()