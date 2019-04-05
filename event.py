"""Event.sc"""

import types


# NOTE: para putAll -> Event({**a, **b, **c, ...}) en vez de updates... (>= Python 3.5)


class Event(dict):
    default_parent_event = {}
    parent_events = {}
    partial_events = {}

    # BUG: tengo que ver la documentación, en update los parámetros actúan igual
    def __init__(self, *args, **kwargs): # know = always True
        super().__init__(*args, **kwargs)
        super().__setattr__('proto', self.pop('proto', None)) # BUG: se puede escribir la llave proto/parent luego pero siempre llama al atributo.
        super().__setattr__('parent', self.pop('parent', None))

    # NOTE: set/get/del es simplemente para implementar y las llamadas a super
    # __setattr__ son solo por know = always True, no se si realmente hace
    # alguna diferencia...
    def __setattr__(self, name, value):
        if hasattr(type(self), name):
            raise AttributeError(f"attribute '{name}' can't be used as key")
        self[name] = value

    # NOTE: https://docs.python.org/3/howto/descriptor.html#invoking-descriptors
    # NOTE: "Called when the default attribute access fails with an AttributeError"
    # NOTE: https://docs.python.org/3/reference/datamodel.html#object.__getattribute__
    # NOTE: https://docs.python.org/3/reference/datamodel.html#special-lookup
    # NOTE: https://docs.python.org/3/library/types.html#types.FunctionType
    # NOTE: VER: módulo types, porque usa types.MethodType to a bound instance method object,
    # NOTE: y es una manera de pasar self: "Define names for built-in types that aren't directly accessible as a builtin."
    def __getattr__(self, name):
        try:
            attr = self[name]
        except KeyError:
            attr = KeyError
        if attr is KeyError: # NOTE: así no tira excepción sobre excepción.
            msg = "'{}' has not attribute or key '{}'"
            raise AttributeError(msg.format(type(self).__name__, name))
        if isinstance(attr, types.FunctionType): # BUG: qué debería pasar con MethodType y los métodos estáticos? así implementado no es posible asingar métodos, en Python se puede asignar un método a otra clase pero self es la clase originaria del método, el méþodo se lleva la clase consigo, lo cual no sé si es bueno. VER value también
            # BUG: el problema es que por más que llame a Event.use, las variables con tilde siempre leen del entorno actual y puede cambiar
            return types.MethodType(attr, self) # NOTE: esta es la forma correcta para que pase self primero siempre (no se puede fácil con FunctionType), ahora, self siempre tiene que estar declarada también. Cuando se llama con at no se pasa self en SuperCollider.
        else:
            return attr

    def __delattr__(self, name):
        if hasattr(type(self), name):
            raise AttributeError(f"attribute '{name}' can't be deleted")
        del self[name]

    def __getitem__(self, key):
        try:
            value = super().__getitem__(key)
        except KeyError:
            if self.proto is not None:
                try:
                    value = super(type(self), self.proto).__getitem__(key)
                except KeyError:
                    if self.parent is not None: # proto and parent
                        try:
                            value = self.parent[key]
                        except KeyError:
                            value = KeyError
                    else: # proto and no parent
                        value = KeyError
            elif self.proto is None and self.parent is not None: # no proto and parent
                try:
                    value = self.parent[key]
                except KeyError:
                    value = KeyError
            else: # no proto and no parent
                value = KeyError
        if value is KeyError: # NOTE: así no tira excepción sobre excepción.
            raise KeyError(key)
        return value

    def __repr__(self):
        return f'{type(self).__name__}({super().__repr__()})'

    ### Event interface ###

    # NOTE: '''Para usar como decorador'''
    def add_function(self, func):
        self.__setattr__(func.__name__, func)

    # NOTE: value sirve porque las llaves se pueden llamar siendo funciones o valores según el dato de entrada/sobreescritura del usuario
    # BUG: en realidad esto es simplemente self.name() pero ignora la llamada y los argumentos si no es una función, distintas funciones pueden tener distintos nombres para los argumentos, eso no se ignora acá y tienen que tener valores por defecto.
    def value(self, name, *args, **kwargs):
        if name in self:
            if isinstance(self[name], types.FunctionType):
                return self[name](self, *args, **kwargs)
            else:
                return self[name]
        else:
            raise KeyError("'{type(self).__name__}' has not key '{name}'")

    # TODO

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def as_ugen_input(self, *_):
        return self.as_control_input()

    def as_control_input(self):
        pass # TODO ^this[ EventTypesWithCleanup.ugenInputTypes[this[\type] ] ];

    # TODO...


### Partial Events ###


def _pe_pitch():
    pitch_event = Event(
        mtranspose = 0,
        gtranspose = 0.0,
        ctranspose = 0.0,
        octave = 5.0,
        root = 0.0,
        degree = 0,
        scale = (0, 2, 4, 5, 7, 9, 11), # NOTE: ESTO SÍ ES UNA TUPLA EN VEZ DE UNA LISTA?
        spo = 12.0, # NOTE steps per octave, steps_per_octave, stepsPerOctave. No sé.
        detune = 0.0,
        harmonic = 1.0,
        octave_ratio = 2.0
    )

    # **************************************************************************
    # NOTE: para esto usar el método value(key) (singular) con kwargs **********
    # BUG IMPORTANTE: el problema es la llamada con value que hace de las ******
    # BUG IMPORTANTE: llaves que pueden ser una función o un valor escalar. ****
    # BUG IMPORTANTE: Ver sustain, abajo, como otro ejemplo claro. *************
    # BUG IMPORTANTE: Y EL USO DE valueEnvir. SE PUEDE SOLUCIONAR CON MÉTODOS **
    # BUG IMPORTANTE: value(key) y value_envir(key) en Event, value_envir: *****
    # BUG IMPORTANTE: "evaluates a function, looking up unspecified arguments **
    # BUG IMPORTANTE: in currentEnvironment", completa los argumentos como si **
    # BUG IMPORTANTE: fueran kwargs, por nombre en vez de orden, ***************
    # BUG IMPORTANTE: y automáticamente. ***************************************
    # BUG IMPORTANTE: VER valueEnvir.scd y getMsgFunc. *************************
    # **************************************************************************

    @pitch_event.add_function
    def note(self):
        pass # BUG: TODO.

    @pitch_event.add_function
    def freq(self):
        pass # BUG: TODO.

    @pitch_event.add_function
    def midinote(self):
        pass # BUG: TODO.

    @pitch_event.add_function
    def detuned_freq(self):
        pass # BUG: TODO.

    @pitch_event.add_function
    def freq_to_note(self, freq):
        pass # BUG: TODO.

    @pitch_event.add_function
    def freq_to_scale(self, freq):
        pass # BUG: TODO.

    return pitch_event


def _pe_dur():
    dur_event = Event(
        tempo = None,
        dur = 1.0,
        stretch = 1.0,
        legato = 0.8,
        #sustain: #{ ~dur * ~legato * ~stretch }, # BUG IMPORTANTE: aunque e.sustain evalúa la función, usa e.use{ ~sustain.value } y necesita evaluar explícitamente, pero el problema es que value anda para todo y la función se puede reemplazar por un escalar.
        lag = 0.0,
        strum = 0.0,
        strum_ends_together = False
    )

    @dur_event.add_function
    def sustain(self):
        return self.dur * self.legato * self.stretch

    return dur_event


class AmpEvent(Event):
    pass
class ServerEvent(Event):
    pass
class BufferEvent(Event):
    pass
### BUG: este 'event' en realidad define la intefaz de las funciones MIDI
### BUG: que luego se llaman como Event Types de EventPlayer MidiEvent...
### BUG: Partial Events tal vez no sean realmente 'Events', sino parámetros
### BUG: (parciales) aplicados a los PlayerEvent Event Types. Pero ver Node,
### BUG: Server, Buffer, Amp, Dur, Pitch Events. Poruqe define componentes
### BUG: estáticos del servidor.
class MidiEvent(Event): # BUG: todo en mayúsculas no me convence...
    pass
class NodeEvent(Event):
    pass
class PlayerEvent(Event):
    pass


### Event Types ###

# BUG: son tipos de PlayerEvent en realidad, no sé por qué está hecho como está hecho.

class RestEvent(PlayerEvent):
    pass


class NoteEvent(PlayerEvent):
    pass


# // optimized version of type \note, about double as efficient.
# // Synth must have no gate and free itself after sustain.
# // Event supports no strum, no conversion of argument objects to controls
class GrainEvent(PlayerEvent):
    pass


class OnEvent(PlayerEvent):
    pass


class SetEvent(PlayerEvent):
    pass


class OffEvent(PlayerEvent):
    pass


class KillEvent(PlayerEvent):
    pass


class GroupEvent(PlayerEvent):
    pass


class ParGroupEvent(PlayerEvent):
    pass


class BusEvent(PlayerEvent):
    pass


class FadeBusEvent(PlayerEvent):
    pass


class GenEvent(PlayerEvent):
    pass


class LoadEvent(PlayerEvent):
    pass


class ReadEvent(PlayerEvent):
    pass


class AllocEvent(PlayerEvent):
    pass


class FreeEvent(PlayerEvent):
    pass


# class MidiEvent(PlayerEvent): ### **** BUG **** se repite con Partial Event ***
#     pass


class SetPropertiesEvent(PlayerEvent):
    pass


class MonoOffEvent(PlayerEvent):
    pass


class MonoSetEvent(PlayerEvent):
    pass


class MonoNoteEvent(PlayerEvent):
    pass


class SynthEvent(PlayerEvent): ### *** BUG *** por qué no sería NodeEvents que es un Partial Event
    pass


class GroupEvent(PlayerEvent): ### *** BUG *** por qué no sería NodeEvents que es un Partial Event
    pass


class TreeEvent(PlayerEvent):
    pass


### Parent Events ###


class DefaultEvent(Event):
    pass


### BUG: estos definen play, los de arriba definen la función que llama dentro
### BUG: play definido en PlayerEVent
class GroupEvent(Event): ### *** BUG *** se repite con Partial Event, tal vez por eso allá estén en mayúscula.
    pass


class SynthEvent(Event): ### *** BUG *** se repite con Partial Event, tal vez por eso allá estén en mayúscula.
    pass


# BUG: defaultParentEvent = parentEvents.default;
