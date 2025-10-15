from anysystem import Process, Context, Message
from typing import List


class ABDRegister(Process):
    """
    Register replica - stores data with timestamps for ordering.
    
    In the ABD algorithm, each replica stores:
    - A value
    - A timestamp to ensure proper ordering
    """
    
    def __init__(self, process_id: str):
        self._id = process_id
        
        # Store the current value and its timestamp
        self._timestamp = 0  # Logical clock counter
        self._value = None  # Current value

    def on_message(self, msg: Message, sender: str, ctx: Context):
        """Handle messages from clients."""
        
        # Phase 1 of read/write: return current timestamp and value
        # Request: READ_TS {}
        # Response: READ_TS_RESP {"timestamp": <timestamp>, "value": current_value}
        if msg.type == 'READ_TS':
            # TODO: Send response with current timestamp and value
            pass
            
        # Phase 2 of read/write: update value if timestamp is newer
        # Request: WRITE_VAL {"timestamp": <timestamp>, "value": new_value}
        # Response: WRITE_ACK {}
        elif msg.type == 'WRITE_VAL':
            # TODO: Compare timestamps and update if newer, then send ACK
            pass

    def on_local_message(self, msg: Message, ctx: Context):
        """Handle local messages for testing purposes."""
        
        # Direct read (for testing)
        # Request: GET {}
        # Response: GET_RESP {"value": current_value}
        if msg.type == 'GET':
            # TODO: Return current value
            pass
            
        # Direct write (for testing)
        # Request: PUT {"value": new_value}
        # Response: PUT_RESP {}
        elif msg.type == 'PUT':
            # TODO: Update value with new timestamp
            pass

    def on_timer(self, timer_name: str, ctx: Context):
        pass


class ABDClient(Process):
    """
    Client - coordinates read/write operations using the ABD algorithm.
    
    The ABD algorithm works in two phases:
    1. Read phase: Get timestamps from majority of replicas
    2. Write phase: Write value to majority of replicas
    
    Both READ and WRITE operations use both phases!
    """
    
    def __init__(self, process_id: str, register_ids: List[str]):
        self._id = process_id
        self._registers = register_ids
        

    def on_local_message(self, msg: Message, ctx: Context):
        """Handle read/write requests from the application."""
        
        # Start a READ operation
        # Request: GET {}
        # Response: GET_RESP {"value": read_value}
        if msg.type == 'GET':
            # TODO: Start two-phase read operation
            # Phase 1: Send READ_TS to all replicas
            pass
        
        # Start a WRITE operation  
        # Request: PUT {"value": new_value}
        # Response: PUT_RESP {}
        elif msg.type == 'PUT':
            # TODO: Start two-phase write operation
            # Phase 1: Send READ_TS to all replicas to get current timestamps
            pass

    def on_message(self, msg: Message, sender: str, ctx: Context):
        """Handle responses from replicas."""
        
        # Response to READ_TS request
        if msg.type == 'READ_TS_RESP':
            # TODO: Collect responses, when have quorum proceed to phase 2
            pass
        
        # Response to WRITE_VAL request
        elif msg.type == 'WRITE_ACK':
            # TODO: Collect ACKs, when have quorum complete operation
            pass

    def on_timer(self, timer_name: str, ctx: Context):
        pass


def register_process(process_id: str) -> ABDRegister:
    """Factory function to create register replica."""
    return ABDRegister(process_id)


def client_process(process_id: str, register_ids: List[str]) -> ABDClient:
    """Factory function to create client."""
    return ABDClient(process_id, register_ids)
