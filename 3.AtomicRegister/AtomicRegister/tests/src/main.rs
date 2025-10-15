mod common;
mod tests;

use std::env;
use std::io::Write;

use clap::Parser;
use env_logger::Builder;
use log::LevelFilter;

use anysystem::python::PyProcessFactory;
use anysystem::test::TestSuite;

use crate::common::TestConfig;
use crate::tests::*;

#[derive(Parser, Debug)]
#[clap(about, long_about = None)]
struct Args {
    #[clap(long = "impl", short = 'i', default_value = "../solution.py")]
    impl_path: String,

    #[clap(long = "test", short)]
    test: Option<String>,

    #[clap(long, short)]
    debug: bool,

    #[clap(long, short, default_value = "123")]
    seed: u64,
}

fn main() {
    let args = Args::parse();
    if args.debug {
        Builder::new()
            .filter_level(LevelFilter::Debug)
            .format(|buf, record| writeln!(buf, "{}", record.args()))
            .init();
    }
    if args.impl_path.ends_with(".py") {
        env::set_var("PYTHONPATH", "../");
    }
    env::set_var("PYTHONHASHSEED", args.seed.to_string());
    
    let register_factory = PyProcessFactory::new(&args.impl_path, "register_process");
    let client_factory = PyProcessFactory::new(&args.impl_path, "client_process");
    
    let config = TestConfig {
        register_factory: &register_factory,
        client_factory: &client_factory,
        num_registers: 3,
        num_clients: 2,
        seed: args.seed,
    };
    
    let mut tests = TestSuite::new();

    tests.add("SINGLE WRITE-READ", test_single_write_read, config);
    tests.add("WRITE-WRITE-READ", test_write_write_read, config);
    tests.add("QUORUM READ", test_quorum_read, config);
    tests.add("QUORUM WRITE", test_quorum_write, config);
    tests.add("MULTIPLE CLIENTS CONCURRENT WRITES", test_multiple_clients_concurrent_writes, config);
    tests.add("WRITE READ CONFLICT", test_write_read_conflict, config);
    tests.add("MANY CONCURRENT OPERATIONS", test_many_concurrent_operations, config);
    tests.add("CASCADING WRITES", test_cascading_writes, config);
    tests.add("UNRELIABLE NETWORK WITH QUORUM FAILURE", test_unreliable_network_with_quorum_failure, config);
    tests.add("LINEARIZABILITY WITH FAILURES", test_linearizability_with_failures, config);
    tests.add("TWO PHASE READ NECESSITY", test_two_phase_read_necessity, config);
    tests.add("TWO PHASE WRITE NECESSITY", test_two_phase_write_necessity, config);
    tests.add("PARTIAL REPLICA UPDATES REQUIRE WRITE BACK", test_partial_replica_updates_require_write_back, config);

    if args.test.is_none() {
        tests.run();
    } else {
        tests.run_test(&args.test.unwrap().to_uppercase().replace('_', " "));
    }
}
