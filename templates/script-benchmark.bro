% for value in load_entries:
${value}
% endfor

module Profiling;

## Note: this strategy relies on a daemon running that is able to record statistics about a particular process at any
## given point in time.  When the daemon receives a message, it will run a number of psutil calls against the bro
## process, then write the results to a log configured on the daemon itself.
## In this case, message passing happens through a FIFO (/tmp/benchmark.fifo by default)

global target: file;
global controller: file;
const fifo_path: string = "/tmp/benchmark.fifo";
redef profiling_file = open_log_file("prof");
redef profiling_interval = ${benchmark_output_delay}secs;
redef expensive_profiling_multiple = 1;

## Event to kick off a call to the daemon that will record various statistics about the running process.
## The actual call is a single ASCII line.  The first item is a command (in this case, 'record').  The remaining
## elements are arguments: the PID of the running bro process, the current network_time, and the current wall-clock time
## (used for estimating how much lag is present between sending an event to the daemon and that event being processed).
##
## As nice as it would be to just use piped_exec, there's a nasty bug floating around that makes bro crash pretty
## reliably after a few hundred thousand calls.  Rather than debugging that, this seemed like a straightforward
## alternative.
event benchmark_checkpoint() {
    local write_str = fmt("record %d %f %f\n", getpid(), network_time(), current_time());
    write_file(target, write_str);
    if(bro_is_terminating()) {
        return;
    }
    schedule ${benchmark_output_delay}secs { benchmark_checkpoint() };
}

## Event fired during initialization to schedule the first call out to the benchmark checkpoint process thingy
event bro_init() {
    target = open_for_append(fifo_path);
    set_buf(target, F);
    write_file(target, fmt("init\n"));
    schedule ${benchmark_output_delay}secs { benchmark_checkpoint() };
    set_buf(profiling_file, F);
}

## Event fired during shutdown to close the log file.
event bro_done() {
    local write_str = fmt("record %d %f %f\n", getpid(), network_time(), current_time());
    write_file(target, write_str);
    write_file(target, fmt("close\n"));
    close(target);
    # One last call here to record statistics at termination ...
}
