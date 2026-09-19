`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 09/15/2026 03:18:26 AM
// Design Name: 
// Module Name: fifo_axi_stream
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module fifo_axi_stream

#(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16
)
(

	input  logic clk,
    input  logic rst_n,

    // Slave side (write side - receiving data)
    input  logic [DATA_WIDTH-1:0] s_axis_tdata,
    input  logic                  s_axis_tvalid,
    output logic                  s_axis_tready,

    // Master side (read side - sending data)
    output logic [DATA_WIDTH-1:0] m_axis_tdata,
    output logic                  m_axis_tvalid,
    input  logic                  m_axis_tready
    );
    
    logic full_i;
    logic empty_i;
    
    FIFO inst(.clk(clk),.reset(~rst_n),.wr_data(s_axis_tdata),.wr_en(s_axis_tvalid & s_axis_tready),.full(full_i), .rd_data(m_axis_tdata), .rd_en(m_axis_tready & m_axis_tvalid), .empty(empty_i));
    
    assign s_axis_tready = ~full_i;
    assign m_axis_tvalid = ~empty_i;
endmodule
