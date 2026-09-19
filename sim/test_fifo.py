import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random


DEPTH = 16

@cocotb.test()
async def test_reset_empty(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # TODO: drive reset high, wait a clock edge or two, then release reset
    dut.reset.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    assert dut.empty.value == 1

    await RisingEdge(dut.clk)


    

    dut.wr_data.value = 0x85
    dut.wr_en.value = 1

    await RisingEdge(dut.clk)

    dut.wr_en.value = 0
    dut.rd_en.value = 1


    await RisingEdge(dut.clk)

    dut.rd_en.value = 0

    await RisingEdge(dut.clk)

    assert dut.empty.value == 1
    assert dut.rd_data.value == 0x85

    await RisingEdge(dut.clk)
    for i in range(DEPTH):
        await do_write(dut, i
        )

    await RisingEdge(dut.clk)
    assert dut.full.value == 1
    await RisingEdge(dut.clk)

    for i in range(DEPTH):
        data = await do_read(dut)
        assert data == i

    assert dut.empty.value == 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_scoreboard_random(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # Reset
    dut.reset.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    expected_queue = []   # the reference model

    for cycle in range(300):
        do_write = random.choice([True, False]) and len(expected_queue) < DEPTH
        do_read  = random.choice([True, False]) and len(expected_queue) > 0

        wr_data = random.randint(0, 255) if do_write else 0

        dut.wr_en.value = 1 if do_write else 0
        dut.wr_data.value = wr_data
        dut.rd_en.value = 1 if do_read else 0

        await RisingEdge(dut.clk)
        dut.wr_en.value = 0
        dut.rd_en.value = 0

        if do_write:
            expected_queue.append(wr_data)

        if do_read:
            expected = expected_queue.pop(0)
            await RisingEdge(dut.clk)
            dut.rd_en.value = 0  # already 0, harmless
            actual = int(dut.rd_data.value)
            assert actual == expected, f"cycle {cycle}: expected {expected}, got {actual}"

        await Timer(1, units="ns")
        assert dut.empty.value == (len(expected_queue) == 0), f"cycle {cycle}: empty mismatch"
        assert dut.full.value == (len(expected_queue) == DEPTH), f"cycle {cycle}: full mismatch"

    dut.wr_en.value = 0
    dut.rd_en.value = 0




async def do_write(dut, data):
    dut.wr_data.value = data
    dut.wr_en.value = 1
    await RisingEdge(dut.clk)
    dut.wr_en.value = 0

async def do_read(dut):
    dut.rd_en.value = 1
    await RisingEdge(dut.clk)
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)
    return dut.rd_data.value





