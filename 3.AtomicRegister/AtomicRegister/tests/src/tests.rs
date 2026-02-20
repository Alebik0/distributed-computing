use rand::SeedableRng;
use rand_pcg::Pcg64;
use assertables::{assume, assume_eq};
use anysystem::test::TestResult;
use anysystem::{Message, System};
use crate::common::*;

pub fn test_single_write_read(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);
    let client = random_client(&sys, &mut rand);
    let value = random_string(8, &mut rand);
    
    check_put(&mut sys, &client, &value, 100)?;
    check_get(&mut sys, &client, Some(&value), 100)?;
    
    Ok(true)
}

pub fn test_write_write_read(config: &TestConfig) -> TestResult {
    for _ in 0..10 {
        let mut sys = build_system(config);
        
        let clients: Vec<String> = sys
            .process_names()
            .into_iter()
            .filter(|name| name.starts_with("client_"))
            .collect();
        
        let value1 = "first_value".to_string();
        let value2 = "second_value".to_string();
        
        check_put(&mut sys, &clients[0], &value1, 100)?;
        check_put(&mut sys, &clients[1], &value2, 100)?;
        check_get(&mut sys, &clients[2 % clients.len()], Some(&value2), 100)?;
    }
    Ok(true)
}

pub fn test_quorum_read(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);
    
    let value = random_string(8, &mut rand);
    let client = random_client(&sys, &mut rand);
    
    check_put(&mut sys, &client, &value, 100)?;
    
    let registers: Vec<String> = sys
        .process_names()
        .into_iter()
        .filter(|name| name.starts_with("register_"))
        .collect();
    let minority = registers.len() / 2;
    for i in 0..minority {
        sys.crash_node(&sys.proc_node_name(&registers[i]));
    }
    
    check_get(&mut sys, &client, Some(&value), 100)?;
    
    Ok(true)
}

pub fn test_quorum_write(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);
    
    let registers: Vec<String> = sys
        .process_names()
        .into_iter()
        .filter(|name| name.starts_with("register_"))
        .collect();
    
    let minority = registers.len() / 2;
    for i in 0..minority {
        sys.crash_node(&sys.proc_node_name(&registers[i]));
    }
    
    let client = random_client(&sys, &mut rand);
    let value = random_string(8, &mut rand);
    check_put(&mut sys, &client, &value, 100)?;
    
    check_get(&mut sys, &client, Some(&value), 100)?;
    
    Ok(true)
}

pub fn test_multiple_clients_concurrent_writes(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);
    
    let clients: Vec<String> = sys
        .process_names()
        .into_iter()
        .filter(|name| name.starts_with("client_"))
        .collect();
    
    let mut values = Vec::new();
    for (i, client) in clients.iter().enumerate() {
        let value = format!("value_from_client_{}", i);
        values.push(value.clone());
        sys.send_local_message(client, Message::json("PUT", &PutReqMessage { value: &value }));
    }
    
    for _ in 0..200 {
        sys.step();
    }
    
    for client in clients.iter() {
        let msgs = sys.read_local_messages(client);
        assume!(!msgs.is_empty(), format!("PUT_RESP not received by {}", client))?;
        assume_eq!(msgs[0].tip, "PUT_RESP")?;
    }
    
    let reader = random_client(&sys, &mut rand);
    check_get(&mut sys, &reader, None, 100)?;
    
    Ok(true)
}

pub fn test_write_read_conflict(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    
    let clients: Vec<String> = sys
        .process_names()
        .into_iter()
        .filter(|name| name.starts_with("client_"))
        .collect();
    
    assume!(clients.len() >= 2, "Need at least 2 clients")?;
    
    let client1 = &clients[0];
    let client2 = &clients[1];
    
    let value1 = "initial_value".to_string();
    check_put(&mut sys, client1, &value1, 100)?;
    
    let value2 = "updated_value".to_string();
    sys.send_local_message(client1, Message::json("PUT", &PutReqMessage { value: &value2 }));
    sys.send_local_message(client2, Message::json("GET", &GetReqMessage {}));
    
    for _ in 0..150 {
        sys.step();
    }
    
    let put_msgs = sys.read_local_messages(client1);
    assume!(!put_msgs.is_empty(), "PUT_RESP not received by client1")?;
    
    let get_msgs = sys.read_local_messages(client2);
    assume!(!get_msgs.is_empty(), "GET_RESP not received by client2")?;
    
    let data: GetRespMessage = serde_json::from_str(&get_msgs[0].data).unwrap();
    assume!(
        data.value == Some(value1) || data.value == Some(value2),
        "Read should return either old or new value"
    )?;
    
    Ok(true)
}

pub fn test_many_concurrent_operations(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    
    let clients: Vec<String> = sys
        .process_names()
        .into_iter()
        .filter(|name| name.starts_with("client_"))
        .collect();
    
    for i in 0..10 {
        let client = &clients[i % clients.len()];
        if i % 2 == 0 {
            let value = format!("value_{}", i);
            sys.send_local_message(client, Message::json("PUT", &PutReqMessage { value: &value }));
        } else {
            sys.send_local_message(client, Message::json("GET", &GetReqMessage {}));
        }
    }
    
    for _ in 0..300 {
        sys.step();
    }
    
    let mut total_responses = 0;
    for client in clients.iter() {
        let msgs = sys.read_local_messages(client);
        total_responses += msgs.len();
    }
    
    assume!(total_responses >= 10, "Not all operations completed")?;
    
    Ok(true)
}

pub fn test_cascading_writes(config: &TestConfig) -> TestResult {
    for _ in 0..10 {
        let mut sys = build_system(config);
        let mut rand = Pcg64::seed_from_u64(config.seed);
        
        let clients: Vec<String> = sys
            .process_names()
            .into_iter()
            .filter(|name| name.starts_with("client_"))
            .collect();
        
        let mut last_value = "initial".to_string();
        check_put(&mut sys, &clients[0], &last_value, 100)?;
        
        for i in 1..clients.len() {
            check_get(&mut sys, &clients[i], Some(&last_value), 100)?;
            
            last_value = format!("value_from_client_{}", i);
            check_put(&mut sys, &clients[i], &last_value, 100)?;
        }
        
        let final_reader = random_client(&sys, &mut rand);
        check_get(&mut sys, &final_reader, Some(&last_value), 100)?;
    }
    Ok(true)
}

pub fn test_unreliable_network_with_quorum_failure(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);
    
    sys.network().set_delays(1., 4.);
    
    let client = random_client(&sys, &mut rand);
    let value = random_string(8, &mut rand);
    
    check_put(&mut sys, &client, &value, 800)?;
    
    let registers: Vec<String> = sys
        .process_names()
        .into_iter()
        .filter(|name| name.starts_with("register_"))
        .collect();
    let minority = registers.len() / 2;
    for i in 0..minority {
        sys.crash_node(&sys.proc_node_name(&registers[i]));
    }
    
    check_get(&mut sys, &client, Some(&value), 800)?;
    
    Ok(true)
}

pub fn test_linearizability_with_failures(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);
    
    sys.network().set_delays(1., 4.);
    
    let client = random_client(&sys, &mut rand);
    
    check_put(&mut sys, &client, "v1", 500)?;
    
    let registers: Vec<String> = sys
        .process_names()
        .into_iter()
        .filter(|name| name.starts_with("register_"))
        .collect();
    let minority = registers.len() / 2;
    for i in 0..minority {
        sys.crash_node(&sys.proc_node_name(&registers[i]));
    }
    
    check_put(&mut sys, &client, "v2", 800)?;
    
    for _ in 0..3 {
        check_get(&mut sys, &client, Some("v2"), 800)?;
    }
    
    Ok(true)
}
pub fn test_two_phase_read_necessity(config: &TestConfig) -> TestResult {
    for _ in 0..10 {
        let mut sys = build_system(config);
        
        sys.network().set_delays(2., 5.);
        
        let clients: Vec<String> = sys
            .process_names()
            .into_iter()
            .filter(|name| name.starts_with("client_"))
            .collect();
        
        assume!(clients.len() >= 2, "Need at least 2 clients")?;
        
        let client1 = &clients[0];
        let client2 = &clients[1];
        
        check_put(&mut sys, client1, "v1", 500)?;
        
        let registers: Vec<String> = sys
            .process_names()
            .into_iter()
            .filter(|name| name.starts_with("register_"))
            .collect();
        let minority = registers.len() / 2;
        for i in 0..minority {
            sys.crash_node(&sys.proc_node_name(&registers[i]));
        }
        
        check_put(&mut sys, client2, "v2", 500)?;
        
        
        check_get(&mut sys, client1, Some("v2"), 500)?;
        
        check_get(&mut sys, client1, Some("v2"), 500)?;
        check_get(&mut sys, client2, Some("v2"), 500)?;
    }
    Ok(true)
}
pub fn test_two_phase_write_necessity(config: &TestConfig) -> TestResult {
    for _ in 0..10 {
        let mut sys = build_system(config);
        
        sys.network().set_delays(1., 4.);
        
        let clients: Vec<String> = sys
            .process_names()
            .into_iter()
            .filter(|name| name.starts_with("client_"))
            .collect();
        
        assume!(clients.len() >= 2, "Need at least 2 clients")?;
        
        let client1 = &clients[0];
        let client2 = &clients[1];
        
        check_put(&mut sys, client1, "v1", 500)?;
        
        check_put(&mut sys, client2, "v2", 500)?;
        
        check_get(&mut sys, client1, Some("v2"), 500)?;
        check_get(&mut sys, client2, Some("v2"), 500)?;
    }
    Ok(true)
}

pub fn test_partial_replica_updates_require_write_back(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    
    sys.network().set_delays(2., 5.);
    
    let clients: Vec<String> = sys
        .process_names()
        .into_iter()
        .filter(|name| name.starts_with("client_"))
        .collect();
    
    let client = &clients[0];
    
    check_put(&mut sys, client, "v1", 800)?;
    
    check_put(&mut sys, client, "v2", 800)?;
    
    check_put(&mut sys, client, "v3", 800)?;
    
    for _ in 0..3 {
        check_get(&mut sys, client, Some("v3"), 800)?;
    }
    
    check_get(&mut sys, &clients[1 % clients.len()], Some("v3"), 800)?;
    
    Ok(true)
}
fn check_get(
    sys: &mut System,
    proc: &str,
    expected: Option<&str>,
    max_steps: u32,
) -> TestResult {
    sys.send_local_message(proc, Message::json("GET", &GetReqMessage {}));
    let res = sys.step_until_local_message_max_steps(proc, max_steps);
    assume!(res.is_ok(), format!("GET_RESP is not returned by {}", proc))?;
    let msgs = res.unwrap();
    let msg = msgs.first().unwrap();
    assume_eq!(msg.tip, "GET_RESP")?;
    let data: GetRespMessage = serde_json::from_str(&msg.data).unwrap();
    
    if let Some(exp) = expected {
        assume_eq!(data.value, Some(exp.to_string()))?;
    }
    
    Ok(true)
}
fn check_put(sys: &mut System, proc: &str, value: &str, max_steps: u32) -> TestResult {
    sys.send_local_message(proc, Message::json("PUT", &PutReqMessage { value }));
    let res = sys.step_until_local_message_max_steps(proc, max_steps);
    assume!(res.is_ok(), format!("PUT_RESP is not returned by {}", proc))?;
    let msgs = res.unwrap();
    let msg = msgs.first().unwrap();
    assume_eq!(msg.tip, "PUT_RESP")?;
    Ok(true)
}
