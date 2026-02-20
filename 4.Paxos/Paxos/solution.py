from anysystem import Context, Message, Process
from typing import List, Optional, Tuple, Dict, Any
import json


class Acceptor(Process):

    def __init__(self):
        pass

    def on_message(self, msg: Message, sender: str, ctx: Context):
        pass

    def on_local_message(self, msg: Message, ctx: Context):
        pass

    def on_timer(self, timer_name: str, ctx: Context):
        pass


class Proposer(Process):

    def __init__(self, process_id: str, acceptor_ids: List[str]):
        pass

    def on_local_message(self, msg: Message, ctx: Context):
        pass

    def on_message(self, msg: Message, sender: str, ctx: Context):
        pass

    def on_timer(self, timer_name: str, ctx: Context):
        pass
