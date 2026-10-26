`timescale 1ns/1ps

// Base-die PNM controller: Fetch/Decode + Address Resolver + Memory Interface Unit
module pnm_base_die_controller #(
    parameter ADDR_W = 16,
    parameter HOP_W  = 8,
    parameter ACCESS_LATENCY = 4
)(
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start,
    input  wire [ADDR_W-1:0]     base_addr,
    input  wire [HOP_W-1:0]      max_hops,
    output reg                   done,
    output reg  [ADDR_W-1:0]     result_addr,
    output reg  [15:0]           cycle_count,
    output reg  [HOP_W-1:0]      hops_resolved,
    output reg                   mem_req,
    output reg  [ADDR_W-1:0]     mem_addr,
    input  wire                  mem_ack,
    input  wire [ADDR_W-1:0]     mem_rdata
);
    localparam S_IDLE=3'd0, S_DECODE=3'd1, S_ISSUE=3'd2, S_WAIT=3'd3, S_NEXTHOP=3'd4, S_DONE=3'd5;

    reg [2:0]        state;
    reg [ADDR_W-1:0] cur_addr;
    reg [HOP_W-1:0]  hop_cnt;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state<=S_IDLE; done<=0; mem_req<=0; mem_addr<=0; cur_addr<=0;
            hop_cnt<=0; cycle_count<=0; result_addr<=0; hops_resolved<=0;
        end else begin
            case (state)
                S_IDLE: begin
                    done <= 0; cycle_count <= 0;
                    if (start) begin cur_addr<=base_addr; hop_cnt<=0; state<=S_DECODE; end
                end
                S_DECODE: begin cycle_count<=cycle_count+1; state<=S_ISSUE; end
                S_ISSUE: begin
                    mem_req<=1; mem_addr<=cur_addr; cycle_count<=cycle_count+1; state<=S_WAIT;
                end
                S_WAIT: begin
                    cycle_count<=cycle_count+1;
                    if (mem_ack) begin mem_req<=0; cur_addr<=mem_rdata; state<=S_NEXTHOP; end
                end
                S_NEXTHOP: begin
                    cycle_count<=cycle_count+1;
                    hop_cnt<=hop_cnt+1; hops_resolved<=hop_cnt+1;
                    if (cur_addr==0 || (hop_cnt+1)>=max_hops) begin
                        result_addr<=cur_addr; state<=S_DONE;
                    end else state<=S_ISSUE;
                end
                S_DONE: begin done<=1; state<=S_IDLE; end
                default: state<=S_IDLE;
            endcase
        end
    end
endmodule

// Behavioral mock of an HBM bank access with fixed row-access latency
module mock_hbm_mem #(
    parameter ADDR_W = 16,
    parameter ACCESS_LATENCY = 4
)(
    input  wire              clk,
    input  wire              rst_n,
    input  wire              req,
    input  wire [ADDR_W-1:0] addr,
    output reg               ack,
    output reg  [ADDR_W-1:0] rdata
);
    reg [ADDR_W-1:0] mem [0:1023];
    reg [7:0] delay_cnt;
    reg busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ack<=0; busy<=0; delay_cnt<=0; end
        else begin
            ack <= 0;
            if (req && !busy) begin busy<=1; delay_cnt<=ACCESS_LATENCY; end
            else if (busy) begin
                if (delay_cnt==1) begin rdata<=mem[addr]; ack<=1; busy<=0; end
                delay_cnt <= delay_cnt - 1;
            end
        end
    end
endmodule
