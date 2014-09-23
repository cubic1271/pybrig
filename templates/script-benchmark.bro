@load instrumentation/instrumentation/collection.bro
@load instrumentation/instrumentation/function.bro
@load instrumentation/instrumentation/chains.bro

redef Instrumentation::collection_timeout = ${benchmark_output_delay};
redef Instrumentation::collection_log = "collection.out";
redef Instrumentation::function_profile_enable = T;
redef Instrumentation::function_profile_log = "profile.out";
redef Instrumentation::chain_profile_enable = T;
redef Instrumentation::chain_profile_log = "chains.out";

% for value in load_entries:
${value}
% endfor

module Profiling;

global target: file;
global controller: file;
redef profiling_file = open_log_file("prof");
redef profiling_interval = ${benchmark_output_delay}secs;
redef expensive_profiling_multiple = 1;

# Event to kick off a call to the daemon that will record various statistics about the running process.
# NOTE: Not used at the moment, so commenting this out for now ...
#event benchmark_checkpoint() {
#    if(bro_is_terminating()) {
#        return;
#    }
#    schedule ${benchmark_output_delay}secs { benchmark_checkpoint() };
#}

## Event fired during initialization to schedule the first call out to the benchmark checkpoint process thingy
event bro_init() {
#    schedule ${benchmark_output_delay}secs { benchmark_checkpoint() };
}

## Event fired during shutdown to close the log file.
event bro_done() { }

