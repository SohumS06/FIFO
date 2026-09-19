`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 09/15/2026 02:46:35 AM
// Design Name: 
// Module Name: FIFO
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


module FIFO #(
	parameter DATA_WIDTH = 8,
	parameter DEPTH = 16
)
(

	input logic clk, reset, 
	input logic wr_en, rd_en,
	input logic [DATA_WIDTH-1:0] wr_data,
	
	output logic [DATA_WIDTH-1:0] rd_data,
	output logic full, empty

    );
    
    localparam PTR_WIDTH = $clog2(DEPTH) + 1;
    logic [DATA_WIDTH-1:0] memory[0:DEPTH-1];
    
    logic[PTR_WIDTH-1:0] wr_ptr, rd_ptr;
    
    always_ff @(posedge clk) begin
		if (reset) wr_ptr <= 0;
    	else if (wr_en) begin
    		memory[wr_ptr[PTR_WIDTH-2:0]] <= wr_data;
    		wr_ptr <= wr_ptr + 1;
		end
	end
	
	always_ff @(posedge clk) begin
		if (reset) rd_ptr <= 0;
    	else if (rd_en) begin
    		rd_data <= memory[rd_ptr[PTR_WIDTH-2:0]];
			rd_ptr <= rd_ptr + 1;
		end
	end
	
	assign full = (wr_ptr[PTR_WIDTH-2:0] == rd_ptr[PTR_WIDTH-2:0]) & (wr_ptr[PTR_WIDTH-1] != rd_ptr[PTR_WIDTH-1]);
	assign empty = (wr_ptr == rd_ptr);
endmodule
