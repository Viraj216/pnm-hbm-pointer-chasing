`timescale 1ns/1ps

module tb_pnm_controller;
    parameter ADDR_W = 16;
    parameter ACCESS_LATENCY = 4;

    reg clk, rst_n, start;
    reg [ADDR_W-1:0] base_addr;
    reg [7:0] max_hops;
    wire done;
    wire [ADDR_W-1:0] result_addr;
    wire [15:0] cycle_count;
    wire [7:0] hops_resolved;
    wire mem_req;
    wire [ADDR_W-1:0] mem_addr;
    wire mem_ack;
    wire [ADDR_W-1:0] mem_rdata;

    pnm_base_die_controller #(.ADDR_W(ADDR_W), .HOP_W(8), .ACCESS_LATENCY(ACCESS_LATENCY)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .base_addr(base_addr), .max_hops(max_hops),
        .done(done), .result_addr(result_addr), .cycle_count(cycle_count), .hops_resolved(hops_resolved),
        .mem_req(mem_req), .mem_addr(mem_addr), .mem_ack(mem_ack), .mem_rdata(mem_rdata)
    );

    mock_hbm_mem #(.ADDR_W(ADDR_W), .ACCESS_LATENCY(ACCESS_LATENCY)) mem (
        .clk(clk), .rst_n(rst_n), .req(mem_req), .addr(mem_addr), .ack(mem_ack), .rdata(mem_rdata)
    );

    always #5 clk = ~clk;

    initial begin
        clk=0; rst_n=0; start=0; base_addr=16'h0001; max_hops=8'd10;

        mem.mem[16'h0001]=16'h0002;
        mem.mem[16'h0002]=16'h0003;
        mem.mem[16'h0003]=16'h0004;
        mem.mem[16'h0004]=16'h0005;
        mem.mem[16'h0005]=16'h0000;

        #12 rst_n=1;
        #10 start=1;
        #10 start=0;

        wait(done);
        $display("RESULT: hops_resolved=%0d result_addr=0x%0h total_cycles=%0d", hops_resolved, result_addr, cycle_count);
        #20 $finish;
    end

    always @(posedge clk) begin
        if (mem_ack)
            $display("t=%0t  HOP: addr=0x%0h -> next=0x%0h", $time, mem_addr, mem_rdata);
    end
endmodule
