% for value in load_entries:
${value}
% endfor

event bro_init() {
   fn_dump_mapping_info("${map_out}");
   fn_set_file("${trace_out}");
   fn_trace_components(T);
   fn_trace_packet_ts(T);
   fn_trace_use_lzf(T);
   fn_trace_papi_time(T);
   fn_trace_add(/.*/);
}
