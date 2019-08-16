"""UGens.sc"""

import struct
import inspect
import operator

from . import functions as fn
from . import _global as _gl
from . import utils as utl
from . import _specialindex as _si
from . import graphparam as gpp
from . import builtins as bi


def late_imports():  # *** HACK
    '''Imports in cyclic conflict used only at runtime, hack test.'''
    import sys
    import sc3.ugens.trig  # BUG: general, how to avoid runnig ugens __init__.py or do the import * in ugens as ugs.
    import sc3.ugens.pan
    import sc3.ugens.infougens
    import sc3.ugens.filter
    import sc3.ugens.osc
    import sc3.ugens.testugens
    import sc3.ugens.line
    import sc3.ugens.demand
    import sc3.ugens.poll
    sys.modules[__name__].__dict__.update({'trg': sc3.ugens.trig})
    sys.modules[__name__].__dict__.update({'pan': sc3.ugens.pan})
    sys.modules[__name__].__dict__.update({'ifu': sc3.ugens.infougens})
    sys.modules[__name__].__dict__.update({'flr': sc3.ugens.filter})
    sys.modules[__name__].__dict__.update({'osc': sc3.ugens.osc})
    sys.modules[__name__].__dict__.update({'tsu': sc3.ugens.testugens})
    sys.modules[__name__].__dict__.update({'lne': sc3.ugens.line})
    sys.modules[__name__].__dict__.update({'dmd': sc3.ugens.demand})
    sys.modules[__name__].__dict__.update({'pll': sc3.ugens.poll})


class ChannelList(list, fn.AbstractFunction):
    '''List wrapper for multichannel expansion graph operations.'''

    def __init__(self, obj=None):
        if obj is None:
            super().__init__()
        elif isinstance(obj, (str, tuple)):
            super().__init__([obj])
        elif hasattr(obj, '__iter__'):
            super().__init__(obj)
        else:
            super().__init__([obj])


    ### AbstractFunction interface ###

    def compose_unop(self, selector):
        return utl.list_unop(selector, self, type(self))

    def compose_binop(self, selector, other):
        return utl.list_binop(selector, self, other, type(self))

    def rcompose_binop(self, selector, other):
        return utl.list_binop(selector, other, self, type(self))

    def compose_narop(self, selector, *args):
        return utl.list_narop(selector, self, *args, t=type(self))


    ### UGen convenience methods (keep in sync) ###

    def _multichannel_perform(self, selector, *args):
        # BUG: Only one level, only for sc builints?
        return type(self)(
            getattr(item, selector)(*args) if isinstance(item, UGen)\
            else getattr(bi, selector)(item, *args) for item in self)

    def dup(self, n=2):
        return ChannelList([self] * n)

    def madd(self, mul=1.0, add=0.0):
        return type(self)(MulAdd.new(i, mul, add) for i in self)

    # in SequenceableCollection L1148.

    def range(self, lo=0.0, hi=1.0):
        return self._multichannel_perform('range', lo, hi)

    def exprange(self, lo=0.01, hi=1.0):
        return self._multichannel_perform('exprange', lo, hi)

    def curverange(self, lo=0.0, hi=1.0, curve=-4):
        return self._multichannel_perform('curverange', lo, hi, curve)

    def unipolar(self, mul=1):
        return self._multichannel_perform('unipolar', mul)

    def bipolar(self, mul=1):
        return self._multichannel_perform('bipolar', mul)

    def clip(self, lo=0.0, hi=1.0):
        return self._multichannel_perform('clip', lo, hi)

    def fold(self, lo=0.0, hi=1.0):
        return self._multichannel_perform('fold', lo, hi)

    def wrap(self, lo=0.0, hi=1.0):
        return self._multichannel_perform('wrap', lo, hi)

    def min_nyquist(self):
        return type(self)(bi.min(item, ifu.SampleRate.ir * 0.5) for item in self)

    # degrad implemented with performUnaryOp, is not overridden here
    # raddeg implemented with performUnaryOp, is not overridden here

    def blend(self, other, frac=0.5):
        return self._multichannel_perform('blend', other, frac)

    def lag(self, time=0.1):
        return self._multichannel_perform('lag', time)

    def lag2(self, time=0.1):
        return self._multichannel_perform('lag2', time)

    def lag3(self, time=0.1):
        return self._multichannel_perform('lag3', time)

    def lagud(self, utime=0.1, dtime=0.1):
        return self._multichannel_perform('lagud', utime, dtime)

    def lag2ud(self, utime=0.1, dtime=0.1):
        return self._multichannel_perform('lag2ud', utime, dtime)

    def lag3ud(self, utime=0.1, dtime=0.1):
        return self._multichannel_perform('lag3ud', utime, dtime)

    def varlag(self, time=0.1, curvature=0, wrap=5, start=None):
        return self._multichannel_perform('varlag', time, curvature, wrap, start)

    def slew(self, up=1, down=1):
        return self._multichannel_perform('slew', up, down)

    def prune(self, min, max, type='minmax'):
        return self._multichannel_perform('prune', min, max, type)

    # snap is not implemented
    # softround is not implemented

    def linlin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._multichannel_perform('linlin', inmin, inmax, outmin,
                                          outmax, clip)

    def linexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._multichannel_perform('linexp', inmin, inmax, outmin,
                                          outmax, clip)

    def explin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._multichannel_perform('explin', inmin, inmax, outmin,
                                          outmax, clip)

    def expexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._multichannel_perform('expexp', inmin, inmax, outmin,
                                          outmax, clip)

    def lincurve(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        return self._multichannel_perform('lincurve', inmin, inmax, outmin,
                                          outmax, curve, clip)

    def curvelin(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        return self._multichannel_perform('curvelin', inmin, inmax, outmin,
                                          outmax, curve, clip)

    def bilin(self, incenter, inmin, inmax, outcenter, outmin, outmax,
              clip='minmax'):
        return self._multichannel_perform('bilin', incenter, inmin, inmax,
                                          outcenter, outmin, outmax, clip)

    def biexp(self, incenter, inmin, inmax, outcenter, outmin, outmax,
              clip='minmax'):
        return self._multichannel_perform('biexp', incenter, inmin, inmax,
                                          outcenter, outmin, outmax, clip)

    def moddif(self, that=0.0, mod=1.0):
        return self._multichannel_perform('moddif', that, mod)

    # in Array.sc

    # num_channels, no (is len, UGen don't really know about channels), TODO: ensure consistency.
    # source_ugen, no if not needed.

    # Synth debug

    def poll(self, trig=10, label=None, trig_id=-1):
        if label is None:
            label = [f'ChannelList UGen [{i}]' for i in range(len(self))]
        return pll.Poll.new(trig, self, label, trig_id)

    def dpoll(self, label=None, run=1, trig_id=-1):
        if label is None:
            label = [f'ChannelList UGen [{i}]' for i in range(len(self))]
        return dmd.Dpoll(self, label, run, trig_id)

    def check_bad_values(self, id=0, post=2):
        return self._multichannel_perform('check_bad_values', id, post)


    ### Override list methods ###

    def __add__(self, other): # +
        return self.compose_binop(operator.add, other)

    def __iadd__(self, other): # +=
        return self.compose_binop(operator.add, other)

    def __mul__(self, other): # *
        return self.compose_binop(operator.mul, other)

    def __rmul__(self, other):
        return self.rcompose_binop(operator.mul, other)

    def __imul__(self, other): # *=
        return self.compose_binop(operator.mul, other)

    def __lt__(self, other): # <
        return self.compose_binop(operator.lt, other)

    def __le__(self, other): # <=
        return self.compose_binop(operator.le, other)

    # def __eq__(self, other):
    #     return self.compose_binop(operator.eq, other)

    # def __ne__(self, other):
    #     return self.compose_binop(operator.ne, other)

    def __gt__(self, other): # >
        return self.compose_binop(operator.gt, other)

    def __ge__(self, other): # >=
        return self.compose_binop(operator.ge, other)


    def __repr__(self):
        return f'ChannelList({super().__repr__()})'


    ### UGen graph parameter interface ###

    # Same as UGenSequence, keep sync. Problem is that this being an
    # AbstractFunction makes it an UGenParameter so graph_param will no work.

    @property
    def rate(self):
        if len(self) == 1:
            return ugen_param(self[0]).rate
        else:
            return utl.list_min([gpp.ugen_param(item).rate or 'scalar'\
                                for item in self])  # lexicographic order

    def is_valid_ugen_input(self):
        return True if self else False

    def as_ugen_input(self, *ugen_cls):
        return type(self)(gpp.ugen_param(x).as_ugen_input(*ugen_cls)\
                          for x in self)

    def as_control_input(self):
        return type(self)(gpp.ugen_param(x).as_control_input() for x in self)

    def as_audio_rate_input(self, *ugen_cls):
        return type(self)(gpp.ugen_param(x).as_audio_rate_input(*ugen_cls)\
                          for x in self)

    def as_ugen_rate(self):
        if len(self) == 1:
            return gpp.ugen_param(self[0]).as_ugen_rate()
        lst = [gpp.ugen_param(x).as_ugen_rate() for x in self]
        if not lst or any(x is None for x in lst):
            return None
        return min(lst)  # minItem. Rates are in lexicographic order.

    def write_input_spec(self, file, synthdef):
        for item in self:
            gpp.ugen_param(item).write_input_spec(file, synthdef)


class UGen(fn.AbstractFunction):
    '''
    Subclasses should not use __init__ to implement graph logic, interface
    methods are _new1, _multi_new, _multi_new_list, _init_ugen, _init_outputs
    (from MultiOutUGen).
    '''

    _valid_rates = {'audio', 'control', 'demand', 'scalar'}

    def __init__(self):  # Do not override.
        self._inputs = ()  # Always tuple.
        self._rate = 'audio'
        # atributos de instancia privados
        self.synthdef = None # es _gl.current_synthdef luego de _add_to_synth
        self.synth_index = -1
        self.special_index = 0 # self.specialIndex = 0; # se obtiene de los símbolos, llama a _Symbol_SpecialIndex
        # topo sorting
        self._antecedents = None #set() # estos sets los inicializa SynthDef _init_topo_sort, _antecedents lo transforma en lista luego, por eso los dejo en none.
        self._descendants = None #list() # inicializa en set() y lo transforma en list() inmediatamente después de poblarlo
        self._width_first_antecedents = [] # se inicializa con SynthDef _width_first_ugens[:] que es un array
        # output_index TODO: VER DE NUEVO las propiedades y los métodos en general.
        # TODO: (sigue) tal vez convenga crea propiedades pero para esta clase sería mucho código.
        self.output_index = 0 # TODO: en UGen es un método, pero lo pasé a propiedad porque es una propiedad en OutputPorxy (!)

    @property
    def rate(self):
        return self._rate

    @property
    def inputs(self):
        return self._inputs

    @classmethod
    def _new1(cls, rate, *args):
        '''
        This method returns a single instance of the UGen, not multichannel
        expanded. It is called inside _multi_new_list, whenever a new single
        instance is needed.
        '''
        obj = cls()
        obj._rate = rate
        obj._add_to_synth()
        return obj._init_ugen(*args)

    @classmethod
    def _multi_new(cls, *args):
        return cls._multi_new_list(list(args))

    @classmethod
    def _multi_new_list(cls, args):
        '''
        These methods are responsible for multichannel expansion. They call
        UGen._new1(rate, *args) for each parallel combination. Most UGen.ar/kr
        methods delegate to UGen.multiNewList. The first argument is rate, then
        the rest of the arguments as in UGen._new1(rate, *args).
        '''
        # single channel, one ugen
        length = 0
        args = gpp.ugen_param(args).as_ugen_input(cls)
        for item in args:
            if isinstance(item, list):
                length = max(length, len(item))
        if length == 0:
            cls._check_valid_rate_name(args[0])
            return cls._new1(*args)
        # multichannel expansion
        new_args = [None] * len(args)
        results = [None] * length
        for i in range(length): # tener en cuenta sclang #[] y `()
            for j, item in enumerate(args):
                new_args[j] = item[i % len(item)]\
                              if isinstance(item, list)\
                              else item # hace la expansión multicanal
            cls._check_valid_rate_name(new_args[0])
            results[i] = cls._multi_new(*new_args)
        return ChannelList(results)

    @classmethod
    def _check_valid_rate_name(cls, string):
        # NOTE, VER: Agregada por mi en multi_new_list. Aunque el original comprueba si rate es simbol en new1. Pero las ugens que sobreescribne new1 sin llamar a super no hacen esa comprobación.
        if string not in cls._valid_rates:
            raise ValueError(f"{cls.__name__} invalid rate: '{string}'")

    def _init_ugen(self, *inputs):
        '''
        This method is called by _new1 that uses its return value. It must
        return self or ChannelList (cases of MultiOutUGen). Optimizations
        returning scalars or None (for no output) are usually returned by
        public UGen constructors (ar, kr, dr, ir or new).
        '''
        self._inputs = inputs
        return self

    @classmethod
    def new_from_desc(cls, rate, num_outputs, inputs, special_index):
        obj = cls()
        obj._rate = rate
        obj._inputs = tuple(inputs)
        obj.special_index = special_index
        return obj

    def __copy__(self):
        # // You can't really copy a UGen without disturbing the Synth.
        # // Usually you want the same object.
        return self


    ### Convenience methods (sync with ChannelList) ###

    def dup(self, n=2):
        return ChannelList([self] * n)

    def madd(self, mul=1.0, add=0.0):
        return MulAdd.new(self, mul, add)

    def range(self, lo=0.0, hi=1.0):
        if self.signal_range() == 'bipolar':
            mul = (hi - lo) * 0.5
            add = mul + lo
        else:
            mul = (hi - lo)
            add = lo
        return MulAdd.new(self, mul, add)

    def exprange(self, lo=0.01, hi=1.0):
        if self.signal_range() == 'bipolar':
            return self.linexp(-1, 1, lo, hi, None)
        else:
            return self.linexp(0, 1, lo, hi, None)

    def curverange(self, lo=0.0, hi=1.0, curve=-4):
        if self.signal_range() == 'bipolar':
            return self.lincurve(-1, 1, lo, hi, curve, None)
        else:
            return self.lincurve(0, 1, lo, hi, curve, None)

    def unipolar(self, mul=1):
        return self.range(0, mul)

    def bipolar(self, mul=1):
        return self.range(-mul, mul)

    def clip(self, lo=0.0, hi=1.0):
        if self.rate == 'demand':
            bi.max(lo, bi.min(hi, self))
        else:
            selector = trg.Clip._method_selector_for_rate(self.rate)
            return getattr(trg.Clip, selector)(self, lo, hi)

    def fold(self, lo=0.0, hi=0.0):
        if self.rate == 'demand':
            raise NotImplementedError('fold is not implemented for dr ugens')
        else:
            selector = trg.Fold._method_selector_for_rate(self.rate)
            return getattr(trg.Fold, selector)(self, lo, hi)

    def wrap(self, lo=0.0, hi=1.0):
        if self.rate == 'demand':
            raise NotImplementedError('wrap is not implemented for dr ugens')
        else:
            selector = trg.Wrap._method_selector_for_rate(self.rate)
            return getattr(trg.Wrap, selector)(self, lo, hi)

    def degrad(self):
        return self * (bi.pi / 180)

    def raddeg(self):
        return self * (180 / bi.pi)

    def blend(self, other, frac=0.5):
        if self.range == 'demand' or gpp.ugen_param(other).rate == 'demand':
            raise NotImplementedError('blend is not implemented for dr ugens')
        else:
            pan = bi.linlin(frec, 0.0, 1.0, -1.0, 1.0)
            if self.rate == 'audio':
                return pan.XFade2.ar(self, other, pan)
            if gpp.ugen_param(other).rate == 'audio':
                return pan.XFade2.ar(other, self, -pan)
            selector = pan.LinXFade2._method_selector_for_rate(self.rate)
            return getattr(pan.LinXFade2, selector)(self, other, pan)

    def min_nyquist(self):
        return bi.min(self, ifu.SampleRate.ir * 0.5)

    def lag(self, time=0.1):
        selector = flr.Lag._method_selector_for_rate(self.rate)
        return getattr(flr.Lag, selector)(self, time)

    def lag2(self, time=0.1):
        selector = flr.Lag2._method_selector_for_rate(self.rate)
        return getattr(flr.Lag2, selector)(self, time)

    def lag3(self, time=0.1):
        selector = flr.Lag3._method_selector_for_rate(self.rate)
        return getattr(flr.Lag3, selector)(self, time)

    def lagud(self, utime=0.1, dtime=0.1):
        selector = flr.LagUD._method_selector_for_rate(self.rate)
        return getattr(flr.LagUD, selector)(self, utime, dtime)

    def lag2ud(self, utime=0.1, dtime=0.1):
        selector = flr.Lag2UD._method_selector_for_rate(self.rate)
        return getattr(flr.Lag2UD, selector)(self, utime, dtime)

    def lag3ud(self, utime=0.1, dtime=0.1):
        selector = flr.Lag3UD._method_selector_for_rate(self.rate)
        return getattr(flr.Lag3UD, selector)(self, utime, dtime)

    def varlag(self, time=0.1, curvature=0, wrap=5, start=None):
        selector = flr.VarLag._method_selector_for_rate(self.rate)
        return getattr(flr.VarLag, selector)(self, time, curvature, wrap, start)

    def slew(self, up=1, down=1):
        selector = flr.Slew._method_selector_for_rate(self.rate)
        return getattr(flr.Slew, selector)(self, up, down)

    def prune(self, min, max, type='minmax'):
        if type == 'minmax':
            return self.clip(min, max)
        elif type == 'min':
            return self.max(min)
        elif type == 'max':
            return self.min(max)
        return self

    def snap(self, resolution=1.0, margin=0.05, strengh=1.0):  # NOTE: UGen/SimpleNumber, not in AbstractFunction
        selector = osc.Select._method_selector_for_rate(self.rate)
        diff = round(self, resolution) - self
        return getattr(osc.Select, selector)(abs(diff) < margin,
                                             [self, self + strengh * diff])

    def softround(self, resolution=1.0, margin=0.05, strengh=1.0):  # NOTE: UGen/SimpleNumber, not in AbstractFunction
        selector = osc.Select._method_selector_for_rate(self.rate)
        diff = round(self, resolution) - self
        return getattr(osc.Select, selector)(abs(diff) > margin,
                                             [self, self + strengh * diff])

    def linlin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        selector = lne.LinLin._method_selector_for_rate(self.rate)  # BUG: I see these can fail for ir/dr ugens however sclang implementation semantics is diverse and not clear.
        return getattr(lne.LinLin, selector)(self.prune(inmin, inmax, clip),
                                             inmin, inmax, outmin, outmax)

    def linexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        selector = lne.LinExp._method_selector_for_rate(self.rate)
        return getattr(lne.LinExp, selector)(self.prune(inmin, inmax, clip),
                                             inmin, inmax, outmin, outmax)

    def explin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return (bi.log(self.prune(inmin, inmax, clip) / inmin) /
                bi.log(inmax / inmin) * (outmax - outmin) + outmin)  # // no separate ugen yet

    def expexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return pow(outmax / outmin,
                   bi.log(self.prune(inmin, inmax, clip) / inmin) /
                   bi.log(inmax / inmin)) * outmin

    def lincurve(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        if isinstance(curve, (int, float)) and abs(curve) < 0.125:
            return self.linlin(inmin, inmax, outmin, outmax, clip)
        grow = bi.exp(curve)
        a = (outmax - outmin) / (1.0 - grow)
        b = outmin + a
        scaled = (self.prune(inmin, inmax, clip) - inmin) / (inmax - inmin)
        curved_res = b - a * pow(grow, scaled)
        if gpp.ugen_param(curve).rate == 'scalar':
            return curved_res
        else:
            selector = osc.Select._method_selector_for_rate(self.rate)
            return getattr(osc.Select, selector)(abs(curve) >= 0.125, [
                self.linlin(inmin, inmax, outmin, outmax, clip),
                curved_res])

    def curvelin(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        if isinstance(curve, (int, float)) and abs(curve) < 0.125:
            return self.linlin(inmin, inmax, outmin, outmax, clip)
        grow = bi.exp(curve)
        a = (inmax - inmin) / (1.0 - grow)
        b = inmin + a
        lin_res = (bi.log((b - this.prune(inmin, inmax, clip)) / a) *
                   (outmax - outmin) / curve + outmin)
        if gpp.ugen_param(curve).rate == 'scalar':
            return lin_res
        else:
            selector = osc.Select._method_selector_for_rate(self.rate)
            return getattr(osc.Select, selector)(abs(curve) >= 0.125, [
                self.linlin(inmin, inmax, outmin, outmax, clip),
                lin_res])

    def bilin(self, incenter, inmin, inmax, outcenter, outmin, outmax,
              clip='minmax'):
        selector = osc.Select._method_selector_for_rate(self.rate)  # BUG: in sclang the call is over the wrong class and doesn't uses _multi_new as above.
        return getattr(osc.Select, selector)(self < incenter, [
            self.linlin(incenter, inmax, outcenter, outmax, clip),
            self.linlin(inmin, incenter, outmin, outcenter, clip)])

    # biexp is not overridden

    def moddif(self, that=0.0, mod=1.0):
        selector = trg.ModDif._method_selector_for_rate(self.rate)
        return getattr(trg.ModDif, selector)(self, that, mod)

    def sanitize(self):
        selector = tsu.Sanitize._method_selector_for_rate(self.rate)  # BUG: in sclang the call is over the wrong class.
        return getattr(tsu.Sanitize, selector)(self)

    # Synth debug

    def poll(self, trig=10, label=None, trig_id=-1):
        return pll.Poll.new(trig, self, label, trig_id)

    def dpoll(self, label=None, run=1, trig_id=-1):
        return dmd.Dpoll.new(self, label, run, trig_id)

    def check_bad_values(self, id=0, post=2):
        selector = tsu.CheckBadValues._method_selector_for_rate(self.rate)
        getattr(tsu.CheckBadValues, selector)(self, id, post)
        # // add the UGen to the tree but keep self as the output
        return self

    # degreeToKey (I don't know why this method is important)


    # L284
    def signal_range(self):
        return 'bipolar'

    # @ { arg y; ^Point.new(this, y) } // dynamic geometry support # ??? no sé qué será ni por qué está acá en el medio...

    # L287
    def _add_to_synth(self):
        self.synthdef = _gl.current_synthdef
        if self.synthdef is not None:
            self.synthdef.add_ugen(self)

    # L292
    def _collect_constants(self): # pong
        for input in self.inputs:
            if isinstance(input, (int, float)):
                self.synthdef.add_constant(float(input))

    # L304
    # Estos métodos son interfaz pero creo que solo para las UGens, serían interfaz protejida
    def _check_inputs(self): # pong, se llama desde SynthDef _check_inputs(), lo reimplementan muchas sub-clases, es interfaz de UGen
        '''Returns error msg or None.'''
        return self._check_valid_inputs()

    def _check_valid_inputs(self):  # este método se usa acá y en otras ugens dentro de _check_inputs
        '''Returns error msg or None.'''
        for i, input in enumerate(self.inputs):
            if not gpp.ugen_param(input).is_valid_ugen_input():
                arg_name = self._arg_name_for_input_at(i)
                if arg_name is None: arg_name = i
                return f'arg: {arg_name} has bad input: {input}'
        return None

    def _check_n_inputs(self, n): # ídem anterior, deben ser interfaz protejida.
        if self.rate == 'audio':
            if n > len(self.inputs):
                n = len(self.inputs)
            for i in range(n):
                if gpp.ugen_param(self.inputs[i]).as_ugen_rate() != 'audio':
                    return (f'input {i} is not audio rate: {self.inputs[i]} '
                            f'{gpp.ugen_param(self.inputs[i]).as_ugen_rate()}')
        return self._check_valid_inputs() # comprueba is_valid_ugen_input no el rate.

    def _check_sr_as_first_input(self): # checkSameRateAsFirstInput ídem anterior, deben ser interfaz protejida
        if self.rate != gpp.ugen_param(self.inputs[0]).as_ugen_rate():
            return (f'first input is not {self.rate} rate: {self.inputs[0]} '
                    f'{gpp.ugen_param(self.inputs[0]).as_ugen_rate()}')
        return self._check_valid_inputs()

    def _arg_name_for_input_at(self, i): # se usa acá y en basicopugen dentro de checkValidInputs, ambas clases lo implementan.
        try:
            selector = type(self)._method_selector_for_rate(self.rate)
            method = getattr(type(self), selector)
            sig = inspect.signature(method)
            params = list(sig.parameters.values())
            arg_names = [x.name for x in params]
            if not arg_names: return None
            if i < len(arg_names):
                # if selector is '__init__': # TODO: *** __init__ SOLO PUEDE RETORNAR NONE Y _new1 RETORNA DISTINTAS COSAS. super().__init__() inicializa las propiedades desde _new1 *** No se puede usar __init__ (super(UGen, self).__init__() no me funciona) hay que usar new o dr para demand rate!!!!!
                #     return arg_names[i + 1] # TODO: VER ABAJO: 1 es arg_names_inputs_offset
                # else:
                #     return arg_names[i]
                return arg_names[i]
            else:
                return None # sclang at(i) retorna nil en vez de una excepción. No sé si eso está bien acá, porque claramente puede ser un error de índice si se pide algo que no existe, self.inputs no puede ser distinto.
        except AttributeError:
            return None

    # BUG: VER: Si este método es necesario en Python.
    # a = SinOsc.ar; a.class.class.findMethod(\ar).argNames; -> SymbolArray[ this, freq, phase, mul, add ]
    # arg_names como se extrae arriba omite el primer argumento que es self/cls, salvo para los métodos mágicos.
    # Si se usa __init__ como new de sclang *sí* se necesita offset. Los métodos mágicos devuelven self/cls. VER los métodos de clase.
    # Además, lo implementan muchas UGens (devuelven 2). Se usa solo en _arg_name_for_input_at, de UGen y BasicOpUGenself.
    # En todo caso sería una propiedad o un método?
    # def arg_names_inputs_offset(self): # lo implementan varias clases como intefaz, se usa solo acá y basicopugen en argNameForInputAt
    #     return 1

    @classmethod
    def _method_selector_for_rate(cls, rate):
        if rate == 'audio':
            if hasattr(cls, 'ar'):
                return 'ar'
        elif rate == 'control':
            if hasattr(cls, 'kr'):
                return 'kr'
        elif rate == 'scalar':
            if hasattr(cls, 'ir'):
                return 'ir'
            elif hasattr(cls, 'new'):
                return 'new'
        elif rate == 'demand':
            if hasattr(cls, 'dr'):
                return 'dr'
        # return None  # original behaviour
        raise AttributeError(f'{cls.__name__} as not {rate} rate constructor')

    def _dump_args(self):
        '''Used for error messages.'''
        msg = 'ARGS:\n'
        tab = ' ' * 4
        arg_name = None
        for i, input in enumerate(self.inputs):
            arg_name = self._arg_name_for_input_at(i)
            if arg_name is None: arg_name = str(i)
            msg += tab + arg_name + ' ' + str(input)
            msg += ' ' + type(self).__name__ + '\n'
        print(msg, end='')

    def _dump_name(self):
        '''Used for SynthDef.dump_ugens().'''
        return str(self.synth_index) + '_' + self.name()


    @classmethod # VER: la locación de este método, es una utilidad de clase.
    def _replace_zeroes_with_silence(cls, lst): # es recursiva y la usan Function-asBuffer, (AtkMatrixMix*ar), GraphBuilder-wrapOut, LocalOut*ar, Out*ar, XOut*ar.
        # // This replaces zeroes with audio rate silence.
        # // Sub collections are deep replaced.
        num_zeroes = lst.count(0.0)
        if num_zeroes == 0:
            return lst
        silent_channels = ChannelList(lne.Silent.ar(num_zeroes))
        pos = 0
        for i, item in enumerate(lst):
            if item == 0.0:
                lst[i] = silent_channels[pos]
                pos += 1
            elif isinstance(item, list):
                res = cls._replace_zeroes_with_silence(item)
                lst[i] = res
        return lst


    ### AbstractFunction interface ###

    def compose_unop(self, selector):
        selector = _si.sc_opname(selector.__name__)
        return UnaryOpUGen.new(selector, self)

    def compose_binop(self, selector, input):
        param = gpp.ugen_param(input)
        if param.is_valid_ugen_input():
            selector = _si.sc_opname(selector.__name__)
            return BinaryOpUGen.new(selector, self, input)
        else:
            return param.perform_binary_op_on_ugen(selector, self) # *** BUG: in scalng does not return?

    def rcompose_binop(self, selector, ugen):
        return BinaryOpUGen.new(selector, ugen, self)

    def compose_narop(self, selector, *args):
        raise NotImplementedError('UGen compose_narop is not supported')


    # L426
    # OC: Complex support
    #asComplex
    #performBinaryOpOnComplex

    # L431, el método if que no voy a poner...
    #if(self, trueugen, falseugen)

    # L470
    # Este método llama a los de abajo, reordené por orden de lectura.
    # Escribe a archivo, pero también generan el formato. VER con SynthDef
    def write_def(self, file):
        try:
            file.write(struct.pack('B', len(self.name()))) # 01 putPascalString, unsigned int8 -> bytes
            file.write(bytes(self.name(), 'ascii')) # 02 putPascalString
            file.write(struct.pack('b', self.rate_number())) # putInt8
            file.write(struct.pack('>i', self.num_inputs())) # putInt32
            file.write(struct.pack('>i', self.num_outputs())) # putInt32
            file.write(struct.pack('>h', self.special_index)) # putInt16
            # // write wire spec indices.
            for input in self.inputs:
                gpp.ugen_param(input).write_input_spec(file, self.synthdef)
            self.write_output_specs(file)
        except Exception as e:
            raise Exception('SynthDef: could not write def') from e

    # L467
    def name(self): # es ugen name
        return type(self).__name__

    def rate_number(self): #rateNumber # se usa en writeDef/Old y writeOutputSpec
        # El orden de los tres primeros no importa, pero en otra parte se usa la comparación lt/gt entre strings y este sería el orden lexicográfico.
        if self.rate == 'audio': return 2
        if self.rate == 'control': return 1
        if self.rate == 'demand': return 3
        return 0 # 'scalar'

    def num_inputs(self):
        return len(self.inputs)

    def num_outputs(self):
        return 1

    def write_output_spec(self, file):
        file.write(struct.pack('b', self.rate_number())) # putInt8

    def write_output_specs(self, file): # TODO: variación con 's' que llama a la sin 's', este método sería para las ugens con salidas múltiples, el nombre del método debería ser más descriptivo porque es fácil de confundir, además. # lo implementan AbstractOut, MultiOutUGen, SendPeakRMS, SendTrig y UGen.
        self.write_output_spec(file)

    ### Topo sort methods ###

    # L488
    def _init_topo_sort(self):  # pong
        for input in self.inputs:
            if isinstance(input, UGen):
                if isinstance(input, OutputProxy): # Omite los OutputProxy in pone las fuentes en _antecedents, ver BUG? abajo.
                    ugen = input.source_ugen # VER: source acá es solo propiedad de OutputProxy(es), no se implementa en otras clases.
                else:                        # OJO: SynthDesc-readUGenSpec llama a source dos veces, la primera sin checar. VER: source es un método/propiedad de varias clases, Array (que returns the source UGen from an Array of OutputProxy(s)) y Nil
                    ugen = input             # VER: source, Object (devuelve this), Nil (método vacío), OutputProxy (es propiedad) y Array, VER otras clases
                self._antecedents.add(ugen)
                ugen._descendants.add(self)
        for ugen in self._width_first_antecedents:
            self._antecedents.add(ugen)
            ugen._descendants.add(self)

    def _make_available(self):
        if len(self._antecedents) == 0:
            self.synthdef.available.append(self)

    def _remove_antecedent(self, ugen):
        self._antecedents.remove(ugen)
        self._make_available()

    def _arrange(self, out_stack):  # Name changed from schedule
        for ugen in reversed(self._descendants): # Hace reverseDo _descendants la inicializa en SynthDef _init_topo_sort como set, la puebla, la transforma en lista y la ordena.
            ugen._remove_antecedent(self)
        out_stack.append(self)

    def _optimize_graph(self):  # pong
        pass  # Empty.

    def _perform_dead_code_elimination(self):  # Se usa en _optimize_graph de BinaryOpUGen, PureMultiOutUGen, PureUGen y UnaryOpUGen.
        # TODO: Cuando quedan las synthdef solo con controles que no van a ninguna parte también se podrían optimizar?
        if len(self._descendants) == 0:
            #for input in self.inputs: # *** BUG EN SCLANG? NO ES ANTECEDENTS DONDE NO ESTÁN LOS OUTPUTPROXY? en sclang funciona por nil responde a casi todo devolviendo nil.
            for input in self._antecedents:
                if isinstance(input, UGen):
                    input._descendants.remove(self)
                    input._optimize_graph()
            self.synthdef.remove_ugen(self)
            return True
        return False

    # Interfaz/protocolo de UGen

    # TODO: REVISAR TODAS LAS CLASES Y EXT, ESTOS MÉTODOS SE USAN EN SynthDesc-read_ugen_spec2
    @classmethod
    def is_control_ugen(cls): # AudioControl y Control implementan y devuelve True, Object devuelve False, además en Object es método de instancia y no de clase como en las otras dos.
        return False

    @classmethod
    def is_input_ugen(cls): # implementan AbstractIn (true) y Object (false) ídem is_control_ugen()
        return False

    @classmethod
    def is_output_ugen(cls): # implementan AbstractOut (true) y Object (false) ídem is_control_ugen()
        return False

    # def is_ugen(self): # Object devuelve false, UGen, true. No se usa en ninguna parte, y no tiene sentido (se hace isinstance(esto, UGen))
    #     return True

    # def output_index(self): # es una propiedad de OutputProxy, es método constante acá. No tiene otra implementación en la librería estandar. Se usa solo UGen.writeInputSpec y SynthDesc.readUGenSpec se obtiene de las inputs.
    #     return 0

    def writes_to_bus(self): # la implementan algunas out ugens, se usa en SynthDesc.outputData
        return False

    def can_free_synth(self): # BUG: tiene ext canFreeSynth.sc y es método de instancia (BUG: lo usa EnvGen!). También es una función implementadas por muchas ugens (true), SequenceableCollection (revisa any), SynthDef (childre.canFreeSynth (seq col)) y Object (false). Es una propiedad solo en esta clase.
        return False
    # BUG: puede faltar algún otro que se use en otro lado.


    ### UGen graph parameter interface ###

    # def is_valid_ugen_input(self):  # BUG: sclang, is True already from AbstractFunction
    #     return True

    def as_ugen_input(self, *ugen_cls):
        return self

    def as_control_input(self):
        raise TypeError("UGen can't be set as control input")

    def as_audio_rate_input(self):
        if self.rate != 'audio':
            return xxx.K2A.ar(self)
        return self

    def as_ugen_rate(self): # BUG: en sclang es simplemente 'rate' aplicada a cualquier objeto...
        return self.rate

    # BUG: VER
    # def perform_binary_op_on_ugen(input, selector, thing):

    def write_input_spec(self, file, synthdef):
        file.write(struct.pack('>i', self.synth_index)) # putInt32
        file.write(struct.pack('>i', self.output_index)) # putInt32


# // UGen which has no side effect and can therefore be considered for
# // a dead code elimination. Read access to buffers/busses are allowed.
class PureUGen(UGen):
    def _optimize_graph(self):  # override
        self._perform_dead_code_elimination()


class MultiOutUGen(UGen):
    def __init__(self):
        self.channels = [] # Nueva propiedad # VER: se necesita antes de llamar a super().__init__() porque en UGen inicializa self.synth_index y llama al setter de esta sub-clase.
        super().__init__() # TODO: *** super().__init__() inicializa las propiedades correctamente desde _new1 *** VER métodos de UGen
        #self._synth_index = -1 # BUG: VER: en UGen synth_index es una propiedad sin setter/getter/deleter, Pero llama al setter solo si se llama desde subclase.

    @property
    def synth_index(self):
        return self._synth_index

    @synth_index.setter
    def synth_index(self, value):
        self._synth_index = value
        for output in self.channels:
            output.synth_index = value

    @synth_index.deleter
    def synth_index(self):
        del self._synth_index

    @classmethod
    def new_from_desc(cls, rate, num_outputs, inputs, special_index=None):
        obj = cls()
        obj._rate = rate
        obj._inputs = tuple(inputs)
        obj._init_outputs(num_outputs, rate)
        return obj

    def _init_outputs(self, num_channels, rate):
        '''
        Return value of this method is used as return value of _init_ugen
        in subclasses.
        '''
        if num_channels is None or num_channels < 1:
            raise Exception(
                f'{self.name()}: wrong number of channels ({num_channels})')
        self.channels = ChannelList(
            [OutputProxy.new(rate, self, i) for i in range(num_channels)])
        if num_channels == 1:
            return self.channels[0]
        return self.channels

    def num_outputs(self):
        return len(self.channels)

    def write_output_specs(self, file):
        for output in self.channels:
            output.write_output_spec(file)


class PureMultiOutUGen(MultiOutUGen):
    def _optimize_graph(self):  # override
        self._perform_dead_code_elimination()


class OutputProxy(UGen):
    # *** BUG: en el original declara <>name, pero no veo que se use acá, y no tiene subclases, tal vez sobreescribe UGen-name()?
    @classmethod
    def new(cls, rate, source_ugen, index):
        return cls._new1(rate, source_ugen, index)

    def _init_ugen(self, source_ugen, index):  # override
        self.source_ugen = source_ugen  # *** NOTE: OJO: source cambia a source_ugen, y puede no ser necesario inicializarla en init
        self.output_index = index
        self.synth_index = source_ugen.synth_index
        return self  # Must return self.

    def _add_to_synth(self):  # override # OutputProxy no se agrega a sí con add_ugen, por lo tanto no se puebla con _init_topo_sort y no se guarda en _antecedents. _init_topo_sort comprueba if isinstance(input, OutputProxy): y agrega source_ugen
        self.synthdef = _gl.current_synthdef

    def _dump_name(self):  # override
        return self.source_ugen._dump_name() + '['\
               + str(self.output_index) + ']'


### BasicOpUGens.sc ###


class BasicOpUGen(UGen):
    def __init__(self):
        super().__init__()
        self._operator = None

    # TODO: El método writeName está comentado en el original. Agregar comentado.

    @property
    def operator(self):
        return self._operator

    @operator.setter
    def operator(self, value):
        index, operator = _si.sc_spindex_opname(value)
        self._operator = operator
        self.special_index = index # TODO: en inout.py hace: self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
        if self.special_index < 0:
            # TODO: ver cuáles son los soportados por el servidor porque Symbol responde a muchos más.
            raise Exception(f"operator '{value}' applied to a UGen "
                            "is not supported by the server")

    @operator.deleter
    def operator(self):
        del self._operator

    #argNamesInputsOffset # VER: estos métodos no se cambian acá porque estoy usando *new* que no es __init__ en Python y no incluye this/self como primer argumento. sclang hace lo mismo que Python con new, argNames devuevle [this, ...] para Meta_Object*new
    #argNameForInputAt

    def _dump_args(self):  # override
        msg = 'ARGS:\n'
        tab = ' ' * 4
        msg += tab + 'operator: ' + self.operator + '\n'
        arg_name = None
        for i, input in enumerate(self.inputs):
            arg_name = self._arg_name_for_input_at(i)
            if not arg_name: arg_name = str(i)
            msg += tab + arg_name + ' ' + str(input)
            msg += ' ' + type(self).__name__ + '\n'
        print(msg, end='')

    def _dump_name(self):  # override
        return str(self.synth_index) + '_' + self.operator


class UnaryOpUGen(BasicOpUGen):
    @classmethod
    def new(cls, selector, a):
        return cls._multi_new('audio', selector, a)

    def _init_ugen(self, operator, input):  # override
        self.operator = operator
        self._rate = gpp.ugen_param(input).as_ugen_rate()
        self._inputs = (input,)
        return self  # Must return self.

    def _optimize_graph(self):  # override
        self._perform_dead_code_elimination()


class BinaryOpUGen(BasicOpUGen):
    @classmethod
    def _new1(cls, rate, selector, a, b):
        # OC: eliminate degenerate cases
        if selector == '*':
            if a == 0.0: return 0.0
            if b == 0.0: return 0.0
            if a == 1.0: return b
            if a == -1.0: return -b #.neg() # TODO: esto sería neg(b) si los operatores unarios se convierten en funciones.
            if b == 1.0: return a
            if b == -1.0: return -a #.neg() # TODO: ídem. Además, justo este es neg. UGen usa AbstractFunction __neg__ para '-'
        if selector == '+':
            if a == 0.0: return b
            if b == 0.0: return a
        if selector == '-':
            if a == 0.0: return b.neg() # TODO: Ídem -a, -b, VER
            if b == 0.0: return a
        if selector == '/':
            if b == 1.0: return a
            if b == -1.0: return a.neg()
        return super()._new1(rate, selector, a, b)

    @classmethod
    def new(cls, selector, a, b):
        return cls._multi_new('audio', selector, a, b)

    def _init_ugen(self, operator, a, b):  # override
        self.operator = operator
        self._rate = self._determine_rate(a, b)
        self._inputs = (a, b)
        return self  # Must return self.

    def _determine_rate(self, a, b):
        a_rate = gpp.ugen_param(a).as_ugen_rate()
        b_rate = gpp.ugen_param(b).as_ugen_rate()
        # Order matters.
        if a_rate == 'demand': return 'demand'
        if b_rate == 'demand': return 'demand'
        if a_rate == 'audio': return 'audio'
        if b_rate == 'audio': return 'audio'
        if a_rate == 'control': return 'control'
        if b_rate == 'control': return 'control'
        return 'scalar'

    def _optimize_graph(self):  # override
        # // this.constantFolding;
        if self._perform_dead_code_elimination():
            return self
        if self.operator == '+':
            self._optimize_add()
            return self
        if self.operator == '-':
            self._optimize_sub()
            return self

    def _optimize_add(self):
        # // create a Sum3 if possible
        optimized_ugen = self._optimize_to_sum3()
        # // create a Sum4 if possible
        if not optimized_ugen:
            optimized_ugen = self._optimize_to_sum4()
        # // create a MulAdd if possible.
        if not optimized_ugen:
            optimized_ugen = self._optimize_to_muladd()
        # // optimize negative additions
        if not optimized_ugen:
            optimized_ugen = self._optimize_addneg()

        if optimized_ugen:
            self.synthdef.replace_ugen(self, optimized_ugen)

    # L239
    def _optimize_to_sum3(self):
        a, b = self.inputs
        if gpp.ugen_param(a).as_ugen_rate() == 'demand'\
        or gpp.ugen_param(b).as_ugen_rate() == 'demand':
            return None

        if isinstance(a, BinaryOpUGen) and a.operator == '+'\
        and len(a._descendants) == 1:
            self.synthdef.remove_ugen(a)
            replacement = Sum3.new(a.inputs[0], a.inputs[1], b) # .descendants_(descendants);
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, a)
            return replacement

        # Ídem b... lo único que veo es que retornan y que la función debería devolver un valor comprobable para luego retornoar.
        if isinstance(b, BinaryOpUGen) and b.operator == '+'\
        and len(b._descendants) == 1:
            self.synthdef.remove_ugen(b)
            replacement = Sum3.new(b.inputs[0], b.inputs[1], a)
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, b)
            return replacement

        return None

    # L262
    def _optimize_to_sum4(self):
        a, b = self.inputs
        if gpp.ugen_param(a).as_ugen_rate() == 'demand'\
        or gpp.ugen_param(b).as_ugen_rate() == 'demand':
            return None

        if isinstance(a, Sum3) and len(a._descendants) == 1:
            self.synthdef.remove_ugen(a)
            replacement = Sum4.new(a.inputs[0], a.inputs[1], a.inputs[2], b)
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, a)
            return replacement

        if isinstance(b, Sum3) and len(b._descendants) == 1:
            self.synthdef.remove_ugen(b)
            replacement = Sum4.new(b.inputs[0], b.inputs[1], b.inputs[2], a)
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, b)
            return replacement

        return None

    # L197
    def _optimize_to_muladd(self):
        a, b = self.inputs

        if isinstance(a, BinaryOpUGen) and a.operator == '*'\
        and len(a._descendants) == 1:

            if MulAdd._can_be_muladd(a.inputs[0], a.inputs[1], b):
                self.synthdef.remove_ugen(a)
                replacement = MulAdd.new(a.inputs[0], a.inputs[1], b)
                replacement._descendants = self._descendants
                self._optimize_update_descendants(replacement, a)
                return replacement

            if MulAdd._can_be_muladd(a.inputs[1], a.inputs[0], b):
                self.synthdef.remove_ugen(a)
                replacement = MulAdd.new(a.inputs[1], a.inputs[0], b)
                replacement._descendants = self._descendants
                self._optimize_update_descendants(replacement, a)
                return replacement

        # does optimization code need to be optimized?
        if isinstance(b, BinaryOpUGen) and b.operator == '*'\
        and len(b._descendants) == 1:

            if MulAdd._can_be_muladd(b.inputs[0], b.inputs[1], a):
                self.synthdef.remove_ugen(b)
                replacement = MulAdd.new(b.inputs[0], b.inputs[1], a)
                replacement._descendants = self._descendants
                self._optimize_update_descendants(replacement, b)
                return replacement

            if MulAdd._can_be_muladd(b.inputs[1], b.inputs[0], a):
                self.synthdef.remove_ugen(b)
                replacement = MulAdd.new(b.inputs[1], b.inputs[0], a)
                replacement._descendants = self._descendants
                self._optimize_update_descendants(replacement, b)
                return replacement

        return None

    # L168
    def _optimize_addneg(self):
        a, b = self.inputs

        if isinstance(b, UnaryOpUGen) and b.operator == 'neg'\
        and len(b._descendants) == 1:
            # OC: a + b.neg -> a - b
            self.synthdef.remove_ugen(b)
            replacement = a - b.inputs[0]
            # // This is the first time the dependants logic appears. It's
            # // repeated below. We will remove 'self' from the synthdef, and
            # // replace it with 'replacement'. 'replacement' should then have
            # // all the same descendants as 'self'.
            replacement._descendants = self._descendants
            # // Drop 'self' and 'b' from all of replacement's inputs'
            # // descendant lists so that future optimizations decide correctly.
            self._optimize_update_descendants(replacement, b)
            return replacement

        if isinstance(a, UnaryOpUGen) and a.operator == 'neg'\
        and len(a._descendants) == 1:
            # OC: a.neg + b -> b - a
            self.synthdef.remove_ugen(a)
            replacement = b - a.inputs[0]
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, a)
            return replacement

        return None

    # L283
    def _optimize_sub(self):
        a, b = self.inputs

        if isinstance(b, UnaryOpUGen) and b.operator == 'neg'\
        and len(b._descendants) == 1:
            # OC: a - b.neg -> a + b
            self.synthdef.remove_ugen(b)
            replacement = BinaryOpUGen.new('+', a, b.inputs[0])
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, b)
            self.synthdef.replace_ugen(self, replacement)
            replacement._optimize_graph()  # // Not called from _optimize_add, no need to return ugen here.

        return None

    # L151
    # OC: 'this' = old ugen being replaced
    # replacement = this's replacement
    # deletedUnit = auxiliary unit being removed, not replaced
    def _optimize_update_descendants(self, replacement, deleted_unit):
        for input in replacement.inputs:
            if isinstance(input, UGen):
                if isinstance(input, OutputProxy):
                    input = input.source_ugen
                desc = input._descendants
                if desc is None: return # BUG, CREO QUE RESUELTO: add falla si desc es None, sclang reponde no haciendo nada.
                desc.append(replacement)
                if desc.count(self): # BUG, CREO QUE RESUELTO: remove falla si self no es descendiente, sclang reponde no haciendo nada.
                    desc.remove(self)
                if desc.count(deleted_unit): # BUG, CREO QUE RESUELTO: remove falla si deleted_unit no es descendiente, sclang reponde no haciendo nada.
                    desc.remove(deleted_unit)

    # L301
    def _constant_folding(self): # No sé si se usa este método, tal vez fue reemplazado porque está comentada la llamada arriba, pero no está comentado.
        pass # BUG, boring to copy


class MulAdd(UGen):
    @classmethod
    def new(cls, input, mul=1.0, add=0.0):
        params = gpp.ugen_param([input, mul, add])
        rate = params.as_ugen_rate()
        args = params.as_ugen_input(cls)
        return cls._multi_new_list([rate] + args)

    @classmethod
    def _new1(cls, rate, input, mul, add):
        # OC: eliminate degenerate cases
        if mul == 0.0: return add
        minus = mul == -1.0
        nomul = mul == 1.0
        noadd = add == 0.0
        if nomul and noadd: return input
        if minus and noadd: return input.neg() # *** BUG: ES POSIBLE QUE PUEDA NO SER UNA UGEN, habría que agregar el método a gpp.ugen_param.
        if noadd: return input * mul
        if minus: return add - input
        if nomul: return input + add

        if cls._can_be_muladd(input, mul, add):
            return super()._new1(rate, input, mul, add)
        if cls._can_be_muladd(mul, input, add):
            return super()._new1(rate, mul, input, add)
        return (input * mul) + add

    def _init_ugen(self, input, mul, add):  # override
        self._inputs = (input, mul, add)
        self._rate = gpp.ugen_param(self.inputs).as_ugen_rate()
        return self  # Must return self.

    @classmethod
    def _can_be_muladd(cls, input, mul, add):
        # // see if these inputs satisfy the constraints of a MulAdd ugen.
        in_rate = gpp.ugen_param(input).as_ugen_rate()
        if in_rate == 'audio':
            return True
        mul_rate = gpp.ugen_param(mul).as_ugen_rate()
        add_rate = gpp.ugen_param(add).as_ugen_rate()
        if in_rate == 'control'\
        and (mul_rate == 'control' or mul_rate == 'scalar')\
        and (add_rate == 'control' or add_rate == 'scalar'):
            return True
        return False


class Sum3(UGen):
    @classmethod
    def new(cls, in0, in1, in2):
        return cls._multi_new(None, in0, in1, in2)

    @classmethod
    def _new1(cls, dummy_rate, in0, in1, in2):
        if in2 == 0.0: return in0 + in1
        if in1 == 0.0: return in0 + in2
        if in0 == 0.0: return in1 + in2

        arg_list = [in0, in1, in2]
        rate = gpp.ugen_param(arg_list).as_ugen_rate()
        arg_list.sort(key=lambda x: gpp.ugen_param(x).as_ugen_rate()) # NOTE: no sé para qué ordena.

        return super()._new1(rate, *arg_list)


class Sum4(UGen):
    @classmethod
    def new(cls, in0, in1, in2, in3):
        return cls._multi_new(None, in0, in1, in2, in3)

    @classmethod
    def _new1(cls, in0, in1, in2, in3):
        if in0 == 0.0: return Sum3._new1(None, in1, in2, in3)
        if in1 == 0.0: return Sum3._new1(None, in0, in2, in3)
        if in2 == 0.0: return Sum3._new1(None, in0, in1, in3)
        if in3 == 0.0: return Sum3._new1(None, in0, in1, in2)

        arg_list = [in0, in1, in2, in3]
        rate = gpp.ugen_param(arg_list).as_ugen_rate()
        arg_list.sort(key=lambda x: gpp.ugen_param(x).as_ugen_rate()) # NOTE: no sé para qué ordena.

        return super()._new1(rate, *arg_list)
