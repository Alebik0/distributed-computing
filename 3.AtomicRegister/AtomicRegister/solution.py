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
            print("READ_TS by", sender)
            
            return ctx.send(Message('READ_TS_RESP', {"timestamp": self._timestamp, "value": self._value}), to=sender)
            
        # Phase 2 of read/write: update value if timestamp is newer
        # Request: WRITE_VAL {"timestamp": <timestamp>, "value": new_value}
        # Response: WRITE_ACK {}
        elif msg.type == 'WRITE_VAL':
            print("WRITE_VAL by", sender)

            request_timestamp = msg['timestamp']
            request_value = msg['value']

            if request_timestamp > self._timestamp:
                self._value = request_value
            
            return ctx.send(Message('WRITE_ACK', {}), to=sender)

    def on_local_message(self, msg: Message, ctx: Context):
        """Handle local messages for testing purposes."""
        
        # Direct read (for testing)
        # Request: GET {}
        # Response: GET_RESP {"value": current_value}
        if msg.type == 'GET':
            print("(testing) GET")

            return ctx.send_local(Message('GET_RESP', {"value": self._value}))
            
        # Direct write (for testing)
        # Request: PUT {"value": new_value}
        # Response: PUT_RESP {}
        elif msg.type == 'PUT':
            print("(testing) PUT")

            self._value = msg['value']

            return ctx.send_local(Message('PUT_RESP', {}))

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
        self._current_operation = None
        self._read_value = None
        self._write_value = None
        self._read_ts_responces = []
        self._write_ack_responces = []
        

    def on_local_message(self, msg: Message, ctx: Context):
        """Handle read/write requests from the application."""
        
        # Start a READ operation
        # Request: GET {}
        # Response: GET_RESP {"value": read_value}
        if msg.type == 'GET':
            # Phase 1: Send READ_TS to all replicas
            print("GET")

            self._current_operation = 'READ'
            self._read_value = None
            self._write_value = None
            self._read_ts_responces = []
            self._write_ack_responces = []

            for reg in self._registers:
                print("Sending READ_TS to", reg, "by", self._id)
                ctx.send(Message('READ_TS', {}), to=reg)
            
            return
        
        # Start a WRITE operation  
        # Request: PUT {"value": new_value}
        # Response: PUT_RESP {}
        elif msg.type == 'PUT':
            # Phase 1: Send READ_TS to all replicas to get current timestamps
            print("PUT")

            self._current_operation = 'WRITE'
            self._read_value = None
            self._write_value = msg['value']
            self._read_ts_responces = []
            self._write_ack_responces = []
            
            for reg in self._registers:
                print("Sending READ_TS to", reg, "by", self._id)
                ctx.send(Message('READ_TS', {}), to=reg)

            return

    def on_message(self, msg: Message, sender: str, ctx: Context):
        """Handle responses from replicas."""
        
        # Response to READ_TS request
        if msg.type == 'READ_TS_RESP':
            print("READ_TS_RESP by", sender)

            self._read_ts_responces.append(msg)

            if len(self._read_ts_responces) == (len(self._registers) + 1) // 2:
                if self._current_operation == 'READ':
                    read_value = self._read_ts_responces[0]['value']
                    read_timestamp = self._read_ts_responces[0]['timestamp']
                    
                    for resp in self._read_ts_responces:
                        if resp['timestamp'] > read_timestamp:
                            read_value = resp['value']
                            read_timestamp = resp['timestamp']
                    
                    # WRITE-BACK phase
                    self._read_value = read_value

                    for reg in self._registers:
                        ctx.send(Message('WRITE_VAL', {'timestamp': read_timestamp, 'value': read_value}), to=reg)
                    
                    return
                elif self._current_operation == 'WRITE':
                    read_timestamp = self._read_ts_responces[0]['timestamp']
                    
                    for resp in self._read_ts_responces:
                        if resp['timestamp'] > read_timestamp:
                            read_timestamp = resp['timestamp']

                    # WRITE phase
                    for reg in self._registers:
                        ctx.send(Message('WRITE_VAL', {'timestamp': read_timestamp + 1, 'value': self._write_value}), to=reg)
                    
                    return
            
            return
        
        # Response to WRITE_VAL request
        elif msg.type == 'WRITE_ACK':
            print("WRITE_ACK by", sender)

            self._write_ack_responces.append(msg)

            if len(self._write_ack_responces) == (len(self._registers) + 1) // 2:
                if self._current_operation == 'READ':
                    ctx.send_local(Message('GET_RESP', {"value": self._read_value}))
                elif self._current_operation == 'WRITE':
                    ctx.send_local(Message('PUT_RESP', {}))
            
            return

    def on_timer(self, timer_name: str, ctx: Context):
        pass


def register_process(process_id: str) -> ABDRegister:
    """Factory function to create register replica."""
    return ABDRegister(process_id)


def client_process(process_id: str, register_ids: List[str]) -> ABDClient:
    """Factory function to create client."""
    return ABDClient(process_id, register_ids)
