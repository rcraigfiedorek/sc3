"""From Patterns.sc"""

from ...base import builtins as bi
from ...base import stream as stm
from ...base import main as _libsc3
from .. import pattern as ptt
from .. import eventstream as est


class ValuePattern(ptt.Pattern):
    def __stream__(self):
        return est.PatternValueStream(self)


class Pvalue(ValuePattern):
    # This pattern is for special cases where common
    # values aren't or can't be embeded as streams.
    def __init__(self, value):
        self.value = value

    def __embed__(self, inval):
        return (yield from stm.embed(self.value, inval))

    # storeArgs


### Math patterns ###


class Pseries(ValuePattern):
    # // Arithmetic series.
    def __init__(self, start=0.0, step=1.0, length=float('inf')):
        self.start = start
        self.step = step
        self.length = length

    def __embed__(self, inval):
        cur = self.start  # value makes the pattern object to keep state
        length = self.length  # if the parameter is a stream.
        step_stream = stm.stream(self.step)
        outval = stepval = None
        try:
            for _ in bi.counter(length):
                stepval = step_stream.next(inval)
                outval = cur
                cur += stepval
                inval = yield outval
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Pgeom(ValuePattern):
    # // Geometric series.
    def __init__(self, start=1.0, grow=1.0, length=float('inf')):
        self.start = start
        self.grow = grow
        self.length = length

    def __embed__(self, inval):
        cur = self.start
        length = self.length
        grow_stream = stm.stream(self.grow)
        outval = growval = None
        try:
            for _ in bi.counter(length):
                growval = grow_stream.next(inval)
                outval = cur
                cur *= growval
                inval = yield outval
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Pbrown(ValuePattern):
    def __init__(self, lo=0.0, hi=1.0, step=0.125, length=float('inf')):
        self.lo = lo
        self.hi = hi
        self.step = step
        self.length = length

    def __embed__(self, inval):
        lo_stream = stm.stream(self.lo)
        hi_stream = stm.stream(self.hi)
        step_stream = stm.stream(self.step)
        try:
            loval = lo_stream.next(inval)
            hival = hi_stream.next(inval)
            stepval = step_stream.next(inval)
            current = bi.rrand(loval, hival)
            for _ in bi.counter(self.length):
                loval = lo_stream.next(inval)
                hival = hi_stream.next(inval)
                stepval = step_stream.next(inval)
                current = bi.fold(
                    self._calc_next(current, stepval), loval, hival)
                inval = yield current
        except stm.StopStream:
            pass
        return inval

    def _calc_next(self, current, step):
        return current + bi.xrand2(step)

    # storeArgs


class Pgbrown(Pbrown):
    def _calc_next(self, current, step):
        return current * (1 + bi.xrand2(step))


class Pwhite(ValuePattern):
    def __init__(self, lo=0.0, hi=1.0, length=float('inf')):
        self.lo = lo
        self.hi = hi
        self.length = length

    def __embed__(self, inval):
        lo_stream = stm.stream(self.lo)
        hi_stream = stm.stream(self.hi)
        hival = loval = None
        try:
            for _ in bi.counter(self.length):
                loval = lo_stream.next(inval)
                hival = hi_stream.next(inval)
                inval = yield bi.rrand(loval, hival)
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Pprob(ValuePattern):
    def __init__(self, distribution, lo=0.0, hi=1.0,
                 table_size=None, length=float('inf')):
        self.distribution = distribution
        self.lo = lo
        self.hi = hi
        # Patterns arguments should be constant after instantiation.
        self.table_size = table_size or max(64, len(distribution))
        self.table = bi.as_random_table(distribution, self.table_size)
        self.length = length

    def __embed__(self, inval):
        table = self.table
        lo_stream = stm.stream(self.lo)
        hi_stream = stm.stream(self.hi)
        lval = hval = None
        try:
            for _ in bi.counter(self.length):
                lval = lo_stream.next(inval)
                hval = hi_stream.next(inval)
                inval = yield (bi.table_rand(table) * (hval - lval)) + lval
        except stm.StopStream:
            pass
        return inval
