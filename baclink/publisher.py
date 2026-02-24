from abc import ABC, abstractmethod
import logging
log = logging.getLogger(__name__)

class Publisher(ABC):

    @abstractmethod
    def register_variables(self, variables):
        log.debug("registering variables")
        pass
    
    @abstractmethod
    def publish_data(self, variables, init: bool=False):
        """Called periodically by OPCUAManger."""
        pass