
import logging
log = logging.getLogger(__name__)

import threading
import time
import sys
from datetime import datetime, timezone, timedelta

from opcua import Client
from baclink import opcuaCustomTools as oct
from baclink import config

node_to_variable = {}

class SubHandler:  
    def datachange_notification(self, node, val, data):
        log.debug(f"received datachange_notification on {node} with value {val}")
        opcVar = node_to_variable.get(node)
        if opcVar:
            opcVar.record_value(val)
        else:
            log.warning(f"Data change notification received on an unknown variable: {node}")


class OPCUAManager:
    def __init__(self, url, publisher=None, timeout=10):
        self.url = url
        self.timeout = timeout
        self.client = None
        self.client = Client(self.url)
        self.publisher = publisher
        self.stop_event = threading.Event()

    def stop(self):
        log.info("Stopping poll loop...")
        self.stop_event.set()

    def connect(self):
        try:
            self.client.connect()
            
        except Exception as e:
            log.error(f"error: {e}")
            log.error(f"Error connecting to OPC UA Server at {self.url}")
            raise RuntimeError("OPC UA Server connection failure")
    
    def _setup_subscriptions(self):
        self.subscriptions = []
        handler = SubHandler()
        sub = self.client.create_subscription(1000, handler)
        for var in self.variables:
            if var.update_method == oct.UpdateMethod.SUBSCRIBE:
                handle = sub.subscribe_data_change(var.node)
                self.subscriptions.append(handle)
                
        log.info(f"Subscribed to {len(self.subscriptions)} variables")

    def load_vars(self, init_vars:bool = True):

        var_count = 0 # track how many variables are monitored:
        if not init_vars:
            log.info("Loading variables from file")
            saved_vars = oct.load_config()
            if saved_vars is not None:
                log.info(f"Loaded {len(saved_vars)} variables from file")
            else:
                log.info("No saved variables found")
                saved_vars = [] # set saved_vars to empty list
        
        

            log.info("Loading variables from OPC UA server")
            objects = self.client.get_objects_node()
            if objects is None:
                log.warning("Count not verify connection to OPC UA server. Attemping reconnect")
                self.client.connect()
                objects = self.client.get_objects_node()
                try:
                    assert objects is not None
                except AssertionError:
                    log.error("Server reconnect failed. Aborting")
                    log.exception("OPC UA Server connection lost")
                    raise RuntimeError("OPC UA Server connection failure")
                    
            log.debug(f"Got objects... {objects.get_browse_name()}")
            programs_node = oct.find_node_by_browse_name(objects, "Programs")
            if not programs_node:
                raise RuntimeError("Could not find 'Programs' node")
            log.info("getting variables from OPC UA server")
            server_vars = oct.browse_variables(self.client, programs_node)
            log.info(f"Found {len(server_vars)} variables on server")

            log.debug(f"Checking for config nodes on server...")
            #check if all variables in saved_vars exist on server:
            for var in saved_vars:
                #check if node exists on server. If not, ignore it for udpates:
                
                try:
                    var.node = self.client.get_node(var.node_id)
                    log.debug(f"found node {var.node_id} in OPC UA server")
                    log.debug(f"checking node... {var.node.get_browse_name()}")
                    var_count += 1
                except Exception as e:
                    log.warning(f"Failed to get node {var.node_id}: {e}")
                    log.info(f"Could not get node for {var.path}. setting update to ignore")
                    var.node = None
                    var.update_method = oct.UpdateMethod.IGNORE
            
            #check for variables on server that are not in saved_vars:
            savedVarPaths = [savedVar.path for savedVar in saved_vars]
            for var in server_vars:
                if var.path not in savedVarPaths:
                    log.info(f"Variable {var.path} found on server but not found in config. Adding it to config")
                    var_count += 1
                    log.debug(f"var data type: {var.data_type}")
                    if var.data_type.lower() in config.SUBSCRIBE_DATA_TYPES:
                        var.update_method = oct.UpdateMethod.SUBSCRIBE
                    else:
                        var.update_method = oct.UpdateMethod.POLL
                    saved_vars.append(var)
                else:
                    log.debug(f"{var.path} found in config. no changes")
                    pass #var already in config. do nothing

            self.variables = saved_vars #update self.variables with saved_vars
            
        else:
            #reinitialize variables from the opc ua server
            log.info("Reading variables from OPC UA server")
            objects = self.client.get_objects_node()
            programs_node = oct.find_node_by_browse_name(objects, "Programs")
            if not programs_node:
                raise RuntimeError("Could not find 'Programs' node")
            self.variables = oct.browse_variables(self.client, programs_node)
            for var in self.variables:
                var_count += 1
                if var.data_type.lower() in config.SUBSCRIBE_DATA_TYPES:
                    var.update_method = oct.UpdateMethod.SUBSCRIBE
                else:
                    var.update_method = oct.UpdateMethod.POLL
        
        if self.publisher:
            self.publisher.register_variables(self.variables)
        else:
            log.info("No publisher. Variables not yet registered")
                
        log.info(f"{len(self.variables)} Variables loaded. Monitoring {var_count} variables")
        oct.save_config(self.variables) #save updated variable config
        for var in self.variables:
            node_to_variable[var.node] = var
        self._setup_subscriptions()

        
            
    def connected(self):
        """
        Check for active connection. returns True if connected, False otherwise.
        """
        try:
            #try reading the name of the root node to check connection
            self.client.get_root_node().get_browse_name()
            log.debug("Connected to OPC UA server")
            return True
        except Exception as e:
            log.warning(f"OPC UA connection lost: {e}")
            return False
    
    def poll_loop(self):
        """Poll Loop for OPC UA variables."""
        next_run_time = time.monotonic() #initialize run time
        init = True
        try:
            while not self.stop_event.is_set():
                next_run_time += config.UPDATE_INTERVAL_SECONDS #update next run time
                try:
                    if not self.connected():
                        log.warning("OPC UA connection lost.")
                        log.info("attempting OPC UA server reconnect.")
                        try:
                            self.connect()
                            self.load_vars()
                        except Exception as e:
                            log.error(f"Error reconnecting to OPC UA server: {e}")
                            raise RuntimeError("OPC UA Server not available")
                    
                    log.debug("Begin polling OPC UA variables")
                    for var in self.variables:
                        #determine whether the variable should be polled:

                        if var.update_method == oct.UpdateMethod.POLL:
                            get_value = True
                        elif var.update_method == oct.UpdateMethod.SUBSCRIBE:
                            if var.last_recorded_time is not None and \
                                var.last_recorded_time < datetime.now(timezone.utc) - timedelta(minutes=config.MAX_UPDATE_INTERVAL_MINUTES):
                                get_value = True
                            else:
                                get_value = False
                        else:
                            get_value = False

                        if get_value:
                            try:
                                log.debug(f"polling variable {var.path}")
                                value = var.node.get_value()
                                log.debug(f"got value {value} for variable {var.path}")
                                timestamp = var.node.get_data_value().SourceTimestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
                                log.debug(f"got timestamp {timestamp} for variable {var.path}")
                            except Exception as e:
                                value = f"Error: {e}"
                                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                                log.debug(f"Error getting value. using utc time: timestamp {timestamp} for variable {var.path}")
                            
                            var.record_value(value, timestamp)
                    log.info(f"Finished polling variables. publishing data.")
                    if self.publisher is not None:
                    #publish the data
                        if init:
                            self.publisher.publish_data(self.variables, init=True)
                            init = False
                        else:
                            self.publisher.publish_data(self.variables, init=False)
                    else:
                        log.warning("No publisher available. Skipping publishing.")
                except Exception:
                    log.exception(f"Unhandled exception in poll_loop")
                    self.stop_event.set()
                    break
                                
        # sleep for the remaining time until the next run time  
                sleep_duration = next_run_time - time.monotonic()
                if sleep_duration > 0:
                    log.info(f"Sleeping for {sleep_duration} seconds before next run time.")
                    self.stop_event.wait(timeout=sleep_duration)
                else:
                    log.warning(f"Loop overran the target interval by {abs(sleep_duration)} seconds. Resetting run_time")
                    next_run_time = time.monotonic() # reset to current time to avoid drift
        
        finally:
            log.debug(f"poll_loop exiting...")
            try:
                self.client.disconnect()
            except Exception:
                pass
            return