use anysystem::{Context, Message, Process};

#[derive(Clone)]
pub struct Acceptor {}

impl Acceptor {
    pub fn new() -> Self {
        Acceptor {}
    }
}

impl Process for Acceptor {
    fn on_message(&mut self, msg: Message, _from: String, ctx: &mut Context) -> Result<(), String> {
        // ...
        Ok(())
    }

    fn on_local_message(&mut self, msg: Message, ctx: &mut Context) -> Result<(), String> {
        // ...
        Ok(())
    }

    fn on_timer(&mut self, _timer: String, _ctx: &mut Context) -> Result<(), String> {
        // ...
        Ok(())
    }
}

#[derive(Clone)]
pub struct Proposer {}

impl Proposer {
    pub fn new(id: &str, acceptors: Vec<String>) -> Self {
        Proposer {}
    }
}

impl Process for Proposer {
    fn on_message(&mut self, msg: Message, _from: String, ctx: &mut Context) -> Result<(), String> {
        // ...
        Ok(())
    }

    fn on_local_message(&mut self, msg: Message, ctx: &mut Context) -> Result<(), String> {
        // ...
        Ok(())
    }

    fn on_timer(&mut self, _timer: String, _ctx: &mut Context) -> Result<(), String> {
        // ...
        Ok(())
    }
}
