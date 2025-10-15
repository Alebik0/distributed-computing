use rand::Rng;
use serde::{Deserialize, Serialize};

use anysystem::python::PyProcessFactory;
use anysystem::System;

#[derive(Serialize)]
pub struct GetReqMessage {
}

#[derive(Deserialize)]
pub struct GetRespMessage {
    pub value: Option<String>,
}

#[derive(Serialize)]
pub struct PutReqMessage<'a> {
    pub value: &'a str,
}

#[derive(Deserialize)]
pub struct PutRespMessage {
}

#[derive(Copy, Clone)]
pub struct TestConfig<'a> {
    pub register_factory: &'a PyProcessFactory,
    pub client_factory: &'a PyProcessFactory,
    pub num_registers: u32,
    pub num_clients: u32,
    pub seed: u64,
}

pub fn build_system(config: &TestConfig) -> System {
    let mut sys = System::new(config.seed);
    sys.network().set_delays(0.01, 0.1);
    
    let mut register_names = Vec::new();
    for n in 0..config.num_registers {
        register_names.push(format!("register_{}", n));
    }
    
    for register_name in register_names.iter() {
        let proc = config
            .register_factory
            .build((register_name.clone(),), config.seed);
        
        let node_name = register_name.clone();
        sys.add_node(&node_name);
        sys.add_process(register_name, sugars::boxed!(proc), &node_name);
    }
    
    let mut client_names = Vec::new();
    for n in 0..config.num_clients {
        client_names.push(format!("client_{}", n));
    }
    
    for client_name in client_names.iter() {
        let proc = config
            .client_factory
            .build((client_name.clone(), register_names.clone()), config.seed);
        
        let node_name = client_name.clone();
        sys.add_node(&node_name);
        sys.add_process(client_name, sugars::boxed!(proc), &node_name);
    }
    
    sys
}

pub fn random_string(len: usize, rng: &mut impl Rng) -> String {
    const CHARSET: &[u8] = b"abcdefghijklmnopqrstuvwxyz0123456789";
    (0..len)
        .map(|_| {
            let idx = rng.gen_range(0..CHARSET.len());
            CHARSET[idx] as char
        })
        .collect()
}

pub fn random_client(sys: &System, rng: &mut impl Rng) -> String {
    let procs: Vec<String> = sys
        .process_names()
        .into_iter()
        .filter(|name| name.starts_with("client_"))
        .collect();
    procs[rng.gen_range(0..procs.len())].clone()
}