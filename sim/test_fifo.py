import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random


DEPTH = 16

@cocotb.test()
async def test_reset_empty(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

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
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

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

        await Timer(1, unit="ns")
        assert dut.empty.value == (len(expected_queue) == 0), f"cycle {cycle}: empty mismatch"
        assert dut.full.value == (len(expected_queue) == DEPTH), f"cycle {cycle}: full mismatch"

    dut.wr_en.value = 0
    dut.rd_en.value = 0


@cocotb.test()
async def test_back_to_back_streaming(dut):
    """Fill the FIFO with gapless writes, then drain it with gapless reads.

    Also doubles as the fill-then-drain scenario for the waveform script,
    since it isolates the full/empty toggling cleanly.
    """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.reset.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    assert dut.empty.value == 1
    assert dut.full.value == 0

    # Gapless writes: wr_en stays high for DEPTH consecutive cycles.
    dut.wr_en.value = 1
    for i in range(DEPTH):
        dut.wr_data.value = i
        await RisingEdge(dut.clk)
    dut.wr_en.value = 0
    await Timer(1, unit="ns")

    assert dut.full.value == 1
    assert dut.empty.value == 0

    # Gapless reads: rd_en stays high for DEPTH consecutive cycles.
    results = []
    dut.rd_en.value = 1
    for _ in range(DEPTH):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        results.append(int(dut.rd_data.value))
    dut.rd_en.value = 0

    assert results == list(range(DEPTH)), f"streamed read mismatch: {results}"
    assert dut.empty.value == 1
    assert dut.full.value == 0


@cocotb.test()
async def test_simultaneous_read_write(dut):
    """rd_en and wr_en asserted on the same cycle while neither full nor empty."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.reset.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    expected_queue = []

    # Preload a couple of entries so the FIFO has margin on both sides
    # once simultaneous read/write starts.
    for v in (0x11, 0x22):
        await do_write(dut, v)
        expected_queue.append(v)

    for v in (0x33, 0x44, 0x55, 0x66):
        dut.wr_data.value = v
        dut.wr_en.value = 1
        dut.rd_en.value = 1
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")

        # The read uses rd_ptr as it stood before this cycle, so it pulls
        # out whatever was already queued ahead of this cycle's new write.
        expected_head = expected_queue.pop(0)
        assert int(dut.rd_data.value) == expected_head
        expected_queue.append(v)

        assert dut.full.value == 0
        assert dut.empty.value == 0

    dut.wr_en.value = 0
    dut.rd_en.value = 0

    while expected_queue:
        data = await do_read(dut)
        assert data == expected_queue.pop(0)
    assert dut.empty.value == 1


@cocotb.test()
async def test_pointer_wraparound(dut):
    """Run several full fill/drain cycles so wr_ptr/rd_ptr wrap past the buffer."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.reset.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    # PTR_WIDTH = clog2(DEPTH)+1, so the MSB wraps every 2*DEPTH increments.
    # Three full rounds pushes the pointers past that boundary twice.
    for rnd in range(3):
        for i in range(DEPTH):
            await do_write(dut, (rnd * DEPTH + i) & 0xFF)
        await Timer(1, unit="ns")
        assert dut.full.value == 1

        for i in range(DEPTH):
            data = await do_read(dut)
            assert data == (rnd * DEPTH + i) & 0xFF
        assert dut.empty.value == 1


@cocotb.test()
async def test_write_when_full_overrun(dut):
    """Document the (unprotected) behavior of asserting wr_en while full.

    This RTL has no guard against writing while full: it silently overwrites
    the oldest, not-yet-read entry and advances wr_ptr anyway, which also
    makes `full` falsely deassert even though data was just lost.
    """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.reset.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    for i in range(DEPTH):
        await do_write(dut, i)
    await Timer(1, unit="ns")
    assert dut.full.value == 1

    await do_write(dut, 0xAA)
    await Timer(1, unit="ns")
    assert dut.full.value == 0, "overrun write silently clears full instead of being blocked"

    first = await do_read(dut)
    assert first == 0xAA, "overrun write overwrote the oldest unread entry"


@cocotb.test()
async def test_read_when_empty_underrun(dut):
    """Document the (unprotected) behavior of asserting rd_en while empty.

    Nothing blocks rd_en while empty: rd_ptr still advances past wr_ptr,
    which makes `empty` falsely deassert even though no valid data exists.
    """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.reset.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)

    assert dut.empty.value == 1

    dut.rd_en.value = 1
    await RisingEdge(dut.clk)
    dut.rd_en.value = 0
    await Timer(1, unit="ns")

    assert dut.empty.value == 0, "underrun read desyncs the pointers and clears empty"


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





