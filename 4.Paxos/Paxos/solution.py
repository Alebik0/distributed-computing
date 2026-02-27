from anysystem import Context, Message, Process
from typing import List, Optional, Tuple, Dict


ProposalNumber = Tuple[int, str]


class Acceptor(Process):
    _proposal_number: Optional[ProposalNumber]
    _accepted_number: Optional[ProposalNumber]
    _accepted_value: Optional[str]

    def __init__(self):
        self._proposal_number = None
        self._accepted_number = None
        self._accepted_value = None

    def on_message(self, msg: Message, sender: str, ctx: Context):
        if msg.type == 'PREPARE':
            if self._proposal_number is None:
                self._proposal_number = msg['proposal_number']
            else:
                self._proposal_number = max(self._proposal_number, msg['proposal_number'])
            
            responce = Message('PROMISE', 
                               data={'proposal_number': msg['proposal_number'], 
                                     'accepted_number': self._accepted_number, 
                                     'accepted_value': self._accepted_value,
                                     "operation": msg['operation']})
            ctx.send(responce, to=sender)
        elif msg.type == 'ACCEPT':
            accepted_number = msg['accepted_number']
            accepted_value = msg['accepted_value']
            
            if self._proposal_number is None or accepted_number >= self._proposal_number:
                self._proposal_number = accepted_number
                self._accepted_number = accepted_number
                self._accepted_value = accepted_value

            ctx.send(Message("ACCEPTED", {'accepted_number': self._accepted_number, 'accepted_value': self._accepted_value, "operation": msg['operation']}), to=sender)

    def on_local_message(self, msg: Message, ctx: Context):
        pass


    def on_timer(self, timer_name: str, ctx: Context):
        pass


class Proposer(Process):
    _process_id: str
    _acceptor_ids: List[str]
    _counter: int
    _promise_quorum: Dict[int, Tuple[ProposalNumber, ProposalNumber, str]]
    _accepted_quorum: Dict[int, Tuple[ProposalNumber, str]]
    _chosen_value: Dict[int, Tuple[ProposalNumber, str]]

    def __init__(self, process_id: str, acceptor_ids: List[str]):
        self._process_id = process_id
        self._acceptor_ids = acceptor_ids
        self._counter = 0
        self._promise_quorum = {}
        self._accepted_quorum = {}
        self._chosen_value = {}

    def _make_proposal_number(self) -> ProposalNumber:
        return (self._counter, self._process_id)
    
    def propose_request_handle(self, value: str, ctx: Context):
        self._counter += 1

        proposal_number, proposal_value = self._make_proposal_number(), value

        self._promise_quorum[self._counter] = []
        self._accepted_quorum[self._counter] = []
        self._chosen_value[self._counter] = (proposal_number, proposal_value)

        for acceptor_id in self._acceptor_ids:
            ctx.send(Message('PREPARE', {'proposal_number': proposal_number, "operation": self._counter}), to=acceptor_id)

    def on_local_message(self, msg: Message, ctx: Context):
        if msg.type == 'PROPOSE_REQUEST':
            self.propose_request_handle(msg['value'], ctx)

    def on_message(self, msg: Message, sender: str, ctx: Context):
        if msg.type == 'PROMISE':
            self._promise_quorum[msg['operation']].append((msg['proposal_number'], msg['accepted_number'], msg['accepted_value']))

            if len(self._promise_quorum[msg['operation']]) == (len(self._acceptor_ids) + 1) // 2:
                # Build up quorum
                chosen_accepted_number = None
                chosen_accepted_value = None

                for proposal_number, accepted_number, accepted_value in self._promise_quorum[msg['operation']]:
                    if accepted_number is not None and \
                            (chosen_accepted_number is None or chosen_accepted_number < accepted_number):
                        chosen_accepted_number = accepted_number
                        chosen_accepted_value = accepted_value
                
                if chosen_accepted_number is None:
                    chosen_accepted_number, chosen_accepted_value = self._chosen_value[msg['operation']]
                else:
                    self._chosen_value[msg['operation']] = chosen_accepted_number, chosen_accepted_value

                for acceptor_id in self._acceptor_ids:
                    message = Message('ACCEPT', 
                                      data={'accepted_number': chosen_accepted_number,
                                            'accepted_value': chosen_accepted_value,
                                            "operation": msg['operation']})
                    ctx.send(message, to=acceptor_id)
        elif msg.type == 'ACCEPTED':
            self._accepted_quorum[msg['operation']].append((msg['accepted_number'], msg['accepted_value']))

            if len(self._accepted_quorum[msg['operation']]) == (len(self._acceptor_ids) + 1) // 2:
                # Build up quorum
                for accepted_number, accepted_value in self._accepted_quorum[msg['operation']]:
                    if accepted_number is None or accepted_number > list(self._chosen_value[msg['operation']][0]):
                        # Restart
                        return self.propose_request_handle(self._chosen_value[msg['operation']][1], ctx)
                
                return ctx.send_local(Message('PROPOSE_RESPONSE', {'value': self._chosen_value[msg['operation']][1]}))

    def on_timer(self, timer_name: str, ctx: Context):
        pass
