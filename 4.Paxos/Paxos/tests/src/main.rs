mod solution;

use std::env;

use anysystem::{
    python::PyProcessFactory,
    test::{TestResult, TestSuite},
    Message, Process, System,
};
use assertables::assume;
use clap::Parser;
use env_logger::Builder;
use log::LevelFilter;
use rand::prelude::*;
use rand_pcg::Pcg64;
use solution::{Acceptor, Proposer};
use std::io::Write;

#[derive(Clone)]
struct TestConfig {
    impl_path: Option<String>,
    seed: u64,
    nodes: u64,
}

#[derive(Parser, Debug)]
#[clap(about, long_about = None)]
struct Args {
    #[clap(long = "impl", short)]
    impl_path: Option<String>,

    #[clap(long = "test", short)]
    test: Option<String>,

    #[clap(long, short, default_value = "3")]
    nodes: u64,

    #[clap(long, short, default_value = "123")]
    seed: u64,

    #[clap(long, short)]
    debug: bool,
}

fn build_system(config: &TestConfig) -> System {
    let mut sys = System::new(config.seed);

    let acceptor_names = (0..config.nodes)
        .map(|i| format!("acceptor-{}", i))
        .collect::<Vec<_>>();

    for i in 0..config.nodes {
        let node_name = format!("node-{}", i);
        let acceptor_name = format!("acceptor-{}", i);
        let proposer_name = format!("proposer-{}", i);

        let (acceptor, proposer): (Box<dyn Process>, Box<dyn Process>) = match &config.impl_path {
            Some(path) => {
                let acceptor =
                    Box::new(PyProcessFactory::new(&path, "Acceptor").build((), config.seed));
                let proposer = Box::new(
                    PyProcessFactory::new(&path, "Proposer")
                        .build((&proposer_name, acceptor_names.clone()), config.seed),
                );
                (acceptor, proposer)
            }
            None => (
                Box::new(Acceptor::new()),
                Box::new(Proposer::new(&proposer_name, acceptor_names.clone())),
            ),
        };

        sys.add_node(&node_name);
        sys.add_process(&acceptor_name, acceptor, &node_name);
        sys.add_process(&proposer_name, proposer, &node_name);
    }

    sys
}

fn test(config: &TestConfig, mutator: fn(&mut System)) -> TestResult {
    let mut rand = Pcg64::seed_from_u64(config.seed);
    let mut sys = build_system(config);
    mutator(&mut sys);

    let initial_values = (0..config.nodes)
        .map(|_| format!(r#"{{"value": "{}"}}"#, rand.gen_range(0..1000000)))
        .collect::<Vec<_>>();

    for i in 0..config.nodes {
        sys.send_local_message(
            &format!("proposer-{}", i),
            Message::new("PROPOSE_REQUEST", &initial_values[i as usize]),
        );
    }
    sys.step_until_no_events();

    let mut values = Vec::new();
    for i in 0..config.nodes {
        let messages = sys.read_local_messages(&format!("proposer-{}", i));
        assume!(!messages.is_empty(), "No messages returned by the proposer")?;
        assume!(
            messages.len() == 1,
            format!("Wrong number of messages: {}", messages.len())
        )?;
        let m = &messages[0];
        assume!(
            m.tip == "PROPOSE_RESPONSE",
            format!("Wrong message type: {}", m.tip)
        )?;
        values.push(m.data.clone());
    }

    assume!(
        values.windows(2).all(|w| w[0] == w[1]),
        "Negotiated values differ"
    )?;

    let value = values[0].clone();

    assume!(
        initial_values.contains(&value),
        "Initial set of proposed values does not contain negotiated one"
    )?;

    values = Vec::new();
    for _ in 0..config.nodes {
        values.push(format!(r#"{{"value": "{}"}}"#, rand.gen_range(0..1000000)));
    }

    for i in 0..config.nodes {
        sys.send_local_message(
            &format!("proposer-{}", i),
            Message::new("PROPOSE_REQUEST", &values[i as usize]),
        );
    }
    sys.step_until_no_events();

    values = Vec::new();
    for i in 0..config.nodes {
        let messages = sys.read_local_messages(&format!("proposer-{}", i));
        assume!(!messages.is_empty(), "No messages returned by the proposer")?;
        assume!(
            messages.len() == 1,
            format!("Wrong number of messages: {}", messages.len())
        )?;
        let m = &messages[0];
        assume!(
            m.tip == "PROPOSE_RESPONSE",
            format!("Wrong message type: {}", m.tip)
        )?;
        values.push(m.data.clone());
    }

    assume!(values.iter().all(|v| *v == value), "Value changed")?;

    Ok(true)
}

fn test_basic(config: &TestConfig) -> TestResult {
    test(config, |_| {})
}

fn test_network_delay(config: &TestConfig) -> TestResult {
    test(config, |sys| sys.network().set_delays(1.0, 5.0))
}

fn test_message_loss(config: &TestConfig) -> TestResult {
    // Test with modest message loss that Paxos can handle with retries
    test(config, |sys| {
        sys.network().set_delays(0.5, 2.0);
        sys.network().set_drop_rate(0.05); // 5% message loss
    })
}

fn test_network_partition(config: &TestConfig) -> TestResult {
    if config.nodes < 2 {
        return Ok(false);
    }

    let mut rand = Pcg64::seed_from_u64(config.seed);
    let mut sys = build_system(config);

    let mut group = sys.nodes();
    group.sort();
    group.shuffle(&mut rand);
    if group.len() % 2 == 1 {
        let node = group.pop().unwrap();
        sys.network().disconnect_node(&node);
    }

    let binding = group.iter().map(|s| &**s).collect::<Vec<_>>();
    let (group1, group2) = binding.split_at(group.len() / 2);
    sys.network().make_partition(group1, group2);
    sys.network().set_delays(1.0, 5.0);

    let initial_values = (0..config.nodes)
        .map(|_| format!(r#"{{"value": "{}"}}"#, rand.gen_range(0..1000000)))
        .collect::<Vec<_>>();

    for i in 0..config.nodes {
        sys.send_local_message(
            &format!("proposer-{}", i),
            Message::new("PROPOSE_REQUEST", &initial_values[i as usize]),
        );
    }

    sys.steps(1000);

    for i in 0..config.nodes {
        let messages = sys.read_local_messages(&format!("proposer-{}", i));
        assume!(messages.is_empty(), "Unexpected message received")?;
    }

    sys.network().reset();

    for i in 0..config.nodes {
        sys.send_local_message(
            &format!("proposer-{}", i),
            Message::new("PROPOSE_REQUEST", &initial_values[i as usize]),
        );
    }

    sys.step_until_no_events();

    let mut values = Vec::new();
    for i in 0..config.nodes {
        let messages = sys.read_local_messages(&format!("proposer-{}", i));
        assume!(!messages.is_empty(), "No messages returned by the proposer")?;
        assume!(
            messages.len() == 1,
            format!("Wrong number of messages: {}", messages.len())
        )?;
        let m = &messages[0];
        assume!(
            m.tip == "PROPOSE_RESPONSE",
            format!("Wrong message type: {}", m.tip)
        )?;
        values.push(m.data.clone());
    }

    assume!(
        values.windows(2).all(|w| w[0] == w[1]),
        "Negotiated values differ"
    )?;

    let value = values[0].clone();

    assume!(
        initial_values.contains(&value),
        "Initial set of proposed values does not contain negotiated one"
    )?;

    Ok(true)
}

fn test_quorum(config: &TestConfig) -> TestResult {
    if config.nodes < 2 {
        return Ok(false);
    }

    let mut rand = Pcg64::seed_from_u64(config.seed);
    let mut sys = build_system(config);

    let mut group = sys.nodes();
    group.sort();
    group.shuffle(&mut rand);
    let binding = group.iter().map(|s| &**s).collect::<Vec<_>>();
    let (quorum, rest) = binding.split_at(group.len() / 2 + 1);
    sys.network().set_delays(1.0, 5.0);
    sys.network().make_partition(quorum, rest);
    sys.network().disconnect_node(quorum[0]);

    let initial_values = (0..config.nodes)
        .map(|_| format!(r#"{{"value": "{}"}}"#, rand.gen_range(0..1000000)))
        .collect::<Vec<_>>();

    for i in 0..config.nodes {
        sys.send_local_message(
            &format!("proposer-{}", i),
            Message::new("PROPOSE_REQUEST", &initial_values[i as usize]),
        );
    }

    sys.steps(1000);

    for i in 0..config.nodes {
        let messages = sys.read_local_messages(&format!("proposer-{}", i));
        assume!(messages.is_empty(), "Unexpected message received")?;
    }

    sys.network().reset();
    sys.network().make_partition(quorum, rest);

    for i in 0..config.nodes {
        sys.send_local_message(
            &format!("proposer-{}", i),
            Message::new("PROPOSE_REQUEST", &initial_values[i as usize]),
        );
    }

    sys.step_until_no_events();

    let mut values = Vec::new();
    for i in 0..config.nodes {
        let name = &format!("proposer-{}", i);
        let messages = sys.read_local_messages(name);
        if rest.contains(&&*sys.proc_node_name(name)) {
            assume!(messages.is_empty(), "Unexpected message received")?;
        } else {
            assume!(messages.len() <= 1)?;
            if messages.len() == 1 {
                let m = &messages[0];
                assume!(
                    m.tip == "PROPOSE_RESPONSE",
                    format!("Wrong message type: {}", m.tip)
                )?;
                values.push(m.data.clone());
            }
        }
    }

    assume!(values.len() > 0)?;
    assume!(
        values.windows(2).all(|w| w[0] == w[1]),
        "Negotiated values differ"
    )?;

    let value = values[0].clone();

    assume!(
        initial_values.contains(&value),
        "Initial set of proposed values does not contain negotiated one"
    )?;

    Ok(true)
}

fn test_dueling_proposers(config: &TestConfig) -> TestResult {
    // Test with exactly 2 proposers to maximize contention
    if config.nodes != 2 {
        return Ok(false);
    }

    let mut rand = Pcg64::seed_from_u64(config.seed);
    let mut sys = build_system(config);
    
    // Minimal delays to maximize race conditions
    sys.network().set_delays(0.1, 0.5);

    let initial_values = (0..config.nodes)
        .map(|_| format!(r#"{{"value": "{}"}}"#, rand.gen_range(0..1000000)))
        .collect::<Vec<_>>();

    // Both proposers start simultaneously
    for i in 0..config.nodes {
        sys.send_local_message(
            &format!("proposer-{}", i),
            Message::new("PROPOSE_REQUEST", &initial_values[i as usize]),
        );
    }
    sys.step_until_no_events();

    let mut values = Vec::new();
    for i in 0..config.nodes {
        let messages = sys.read_local_messages(&format!("proposer-{}", i));
        assume!(!messages.is_empty(), "No messages returned by the proposer")?;
        assume!(
            messages.len() == 1,
            format!("Wrong number of messages: {}", messages.len())
        )?;
        let m = &messages[0];
        assume!(
            m.tip == "PROPOSE_RESPONSE",
            format!("Wrong message type: {}", m.tip)
        )?;
        values.push(m.data.clone());
    }

    assume!(
        values.windows(2).all(|w| w[0] == w[1]),
        "Negotiated values differ"
    )?;

    let value = values[0].clone();

    assume!(
        initial_values.contains(&value),
        "Initial set of proposed values does not contain negotiated one"
    )?;

    Ok(true)
}

fn test_single_acceptor_failure(config: &TestConfig) -> TestResult {
    if config.nodes < 3 {
        return Ok(false);
    }

    let mut rand = Pcg64::seed_from_u64(config.seed);
    let mut sys = build_system(config);

    // Disconnect one acceptor completely
    let acceptor_index = rand.gen_range(0..config.nodes);
    let acceptor_to_fail = format!("acceptor-{}", acceptor_index);
    let failed_node = sys.proc_node_name(&acceptor_to_fail);
    sys.network().disconnect_node(&failed_node);

    let initial_values = (0..config.nodes)
        .map(|_| format!(r#"{{"value": "{}"}}"#, rand.gen_range(0..1000000)))
        .collect::<Vec<_>>();

    for i in 0..config.nodes {
        sys.send_local_message(
            &format!("proposer-{}", i),
            Message::new("PROPOSE_REQUEST", &initial_values[i as usize]),
        );
    }
    sys.step_until_no_events();

    let mut values = Vec::new();
    for i in 0..config.nodes {
        let proposer_name = format!("proposer-{}", i);
        let messages = sys.read_local_messages(&proposer_name);
        
        // Skip proposer on failed node (same node as failed acceptor)
        if sys.proc_node_name(&proposer_name) == failed_node {
            assume!(messages.is_empty(), "Unexpected message from failed proposer")?;
            continue;
        }
        
        assume!(!messages.is_empty(), "No messages returned by the proposer")?;
        assume!(
            messages.len() == 1,
            format!("Wrong number of messages: {}", messages.len())
        )?;
        let m = &messages[0];
        assume!(
            m.tip == "PROPOSE_RESPONSE",
            format!("Wrong message type: {}", m.tip)
        )?;
        values.push(m.data.clone());
    }

    assume!(values.len() > 0, "No successful proposers")?;
    assume!(
        values.windows(2).all(|w| w[0] == w[1]),
        "Negotiated values differ"
    )?;

    let value = values[0].clone();

    assume!(
        initial_values.contains(&value),
        "Initial set of proposed values does not contain negotiated one"
    )?;

    Ok(true)
}

fn test_late_joiner(config: &TestConfig) -> TestResult {
    if config.nodes < 2 {
        return Ok(false);
    }

    let mut rand = Pcg64::seed_from_u64(config.seed);
    let mut sys = build_system(config);

    let initial_values = (0..config.nodes)
        .map(|_| format!(r#"{{"value": "{}"}}"#, rand.gen_range(0..1000000)))
        .collect::<Vec<_>>();

    // First N-1 proposers start
    for i in 0..config.nodes - 1 {
        sys.send_local_message(
            &format!("proposer-{}", i),
            Message::new("PROPOSE_REQUEST", &initial_values[i as usize]),
        );
    }
    sys.step_until_no_events();

    // Check that first N-1 proposers reached consensus
    let mut values = Vec::new();
    for i in 0..config.nodes - 1 {
        let messages = sys.read_local_messages(&format!("proposer-{}", i));
        assume!(!messages.is_empty(), "No messages returned by the proposer")?;
        let m = &messages[0];
        values.push(m.data.clone());
    }

    assume!(
        values.windows(2).all(|w| w[0] == w[1]),
        "Initial proposers did not reach consensus"
    )?;

    let agreed_value = values[0].clone();

    // Now the late joiner proposes a different value
    sys.send_local_message(
        &format!("proposer-{}", config.nodes - 1),
        Message::new("PROPOSE_REQUEST", &initial_values[(config.nodes - 1) as usize]),
    );
    sys.step_until_no_events();

    // Late joiner should accept the already agreed value
    let messages = sys.read_local_messages(&format!("proposer-{}", config.nodes - 1));
    assume!(!messages.is_empty(), "No messages returned by late joiner")?;
    assume!(
        messages.len() == 1,
        format!("Wrong number of messages: {}", messages.len())
    )?;
    let m = &messages[0];
    assume!(
        m.tip == "PROPOSE_RESPONSE",
        format!("Wrong message type: {}", m.tip)
    )?;

    assume!(
        m.data == agreed_value,
        format!("Late joiner got different value: {} vs {}", m.data, agreed_value)
    )?;

    Ok(true)
}

fn main() {
    let args = Args::parse();

    if args.debug {
        Builder::new()
            .filter_level(LevelFilter::Debug)
            .format(|buf, record| writeln!(buf, "{}", record.args()))
            .init();
    }

    env::set_var("PYTHONPATH", "../");
    env::set_var("PYTHONUNBUFFERED", "1");

    let config = TestConfig {
        impl_path: args.impl_path,
        seed: args.seed,
        nodes: args.nodes,
    };

    let mut tests = TestSuite::new();
    tests.add("BASIC", test_basic, config.clone());
    tests.add("NETWORK DELAY", test_network_delay, config.clone());
    tests.add("MESSAGE LOSS", test_message_loss, config.clone());
    tests.add("NETWORK PARTITION", test_network_partition, config.clone());
    tests.add("QUORUM", test_quorum, config.clone());
    tests.add("DUELING PROPOSERS", test_dueling_proposers, config.clone());
    tests.add("SINGLE ACCEPTOR FAILURE", test_single_acceptor_failure, config.clone());
    tests.add("LATE JOINER", test_late_joiner, config.clone());

    if args.test.is_none() {
        tests.run();
    } else {
        tests.run_test(&args.test.unwrap().to_uppercase().replace('_', " "));
    }
}
