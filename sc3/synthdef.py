"""
SynthDef...

Ver qué métdos se llaman desde las UGens y cómo se relacionan.
Buscar la manera de ir probando los resultados parciales y comprobando
junto con sclang. Prestar atención a los métodos que son de ancestros
y que actúan como protocolo incorporado en la librería de sclang incluso
desde Object.

Luego poner synthdef, ugen, binopugen y todas las ugens que actúan como
tipos básicos en un subpaquete que se llame synthgraph. Las ugens concretas
irían a parte en otro paquete llamado ugens... Pero después ver cómo se
pueden importar las cosas como conjuntos de paquetes tal vez compuestos
de subconjuntos de los elemnentos de los paquetes... suena complicado.
"""

import inspect
import warnings
import io
import struct
import pathlib

from . import _global as _gl
from . import inout as scio
from . import utils as ut
from . import ugens as ug
from . import server as sv
from . import platform as pt
from . import systemactions as sa
from . import synthdesc as ds # cíclico


class SynthDef():
    synthdef_dir = pt.Platform.user_app_support_dir() / 'synthdefs'
    synthdef_dir.mkdir(exist_ok=True) # // Ensure exists

    @classmethod
    def dummy(cls, name):
        # TODO: VER. Es Object:*prNew. Se usa para SynthDesc:read_synthdef2
        # // creates a new instance that can hold up to maxSize
        # // indexable slots. the indexed size will be zero.
        # // to actually put things in the object you need to
        # // add them.
        # https://stackoverflow.com/questions/6383914/is-there-a-way-to-instantiate-a-class-without-calling-init
        # BUG: peligroso, ver el link de arriba. Tal vez sea mejor agregar un parámetro 'dummy' a __init__(). Aunque no hay herencia en este caso hay que ver qué cosas no se inicializan pero funcionan como propiedades necesarias.
        # BUG: Aunque creo que sclang crea un objeto totalmente vacío, ver si lo métodos son 'slots', pero le pasa name como argumento y en object prNew arg es maxSize = 0.
        # BUG: tengo que ver qué hace realmente prNew con el parámetro name, parece que no lo usa...
        # BUG: haciendo d = SynthDef.prNew("nombre"); d.dump; el valor "nombre" no está asignado a name, parece que sí crea los slots de las variables de instancia y le asigna el valor por defecto a d = SynthDef.prNew("nombre"), el resto es nil.
        # ***** LE AGREGUÉ TODAS LAS PROPIEDADES, EN tODO CASO QUEDA IGUAL A UN OBJETO VACÍO (tener en cuenta que no hereda) ***
        obj = cls.__new__(cls)

        obj.name = name
        obj.func = None
        obj.variants = dict()
        obj.metadata = dict()
        obj.desc = None

        obj.controls = None
        obj.control_names = []
        obj.all_control_names = []
        obj.control_index = 0
        obj.children = []

        obj.constants = dict()
        obj.constant_set = set()
        obj.max_local_bufs = None

        obj.available = []
        obj._width_first_ugens = []
        obj._rewrite_in_progress = False

        return obj

    #*new L35
    #rates y prependeargs pueden ser anotaciones de tipo, ver variantes y metadata, le constructor hace demasiado...
    def __init__(self, name, graph_func, rates=None,
                 prepend_args=None, variants=None, metadata=None): # rates y prepend args pueden ser anotaciones, prepargs puede ser un tipo especial en las anotaciones, o puede ser otro decorador?
        self.name = name
        self.func = None # la inicializa en build luego de finishBuild de lo contrario no funciona wrap
        self.variants = variants or {} # # BUG: comprobar tipo, no es un valor que se genere internamente. No sé por qué está agrupada como propiedad junto con las variables de topo sort
        self.metadata = metadata or {}
        self.desc = None # *** Aún no vi dónde inicializa

        #self.controls = None # inicializa en initBuild, esta propiedad la setean las ugens mediante _gl.current_synthdef agregando controles
        self.control_names = [] # en sclang se inicializan desde nil en addControlNames, en Python tienen que estar acá porque se pueden llamar desde wrap
        self.all_control_names = [] # en sclang se inicializan desde nil en addControlNames
        self.control_index = 0 # lo inicializa cuando declara la propiedad y lo reinicializa al mismo valor en initBuild
        self.children = [] # Array.new(64) # esta probablemente sea privada pero se usa para ping pong

        #self.constants = dict() # inicializa en initBuild
        #self.constant_set = set() # inicializa en initBuild
        #self.max_local_bufs = None # inicializa en initBuild, la usa LocalBus*new1 y checka por nil

        # topo sort
        self.available = [] # la inicializan las ugens con .makeAvailable() creando el array desde nil, initTopoSort la vuelve a nil.
        self._width_first_ugens = [] # se puebla desde nil con WidthFirstUGen.addToSynth (solo para IFFT)
        self._rewrite_in_progress = False # = la inicializa a True en optimizeGraph L472 y luego la vuelve a nil, pero es mejor que sea false por los 'if'

        self._build(graph_func, rates or [], prepend_args or [])

    # BUG: este es un método especial en varios tipos de clases tengo
    # que ver cuál es el alcance global dentro de la librería,
    # tal vez sea para serialización, no se usa en SynthDef/UGen.
    #def store_args(self):
    #    return (self.name, self.func) # una tupla en vez de una lista (array en sclang)

    # construye el grafo en varios pasos, init, build, finish y va
    # inicializando las restantes variables de instancia según el paso.
    # Tal vez debería ponerlas todas a None en __init__
    def _build(self, graph_func, rates, prepend_args):
        with _gl.def_build_lock:
            try:
                _gl.current_synthdef = self
                self._init_build()
                self._build_ugen_graph(graph_func, rates, prepend_args)
                self._finish_build()
                self.func = graph_func # inicializa func que junto con name son las primeras propiedades.
                _gl.current_synthdef = None
            except Exception as e:
                _gl.current_synthdef = None
                raise e

    # L53
    @classmethod
    def wrap(cls, func, rates=None, prepend_args=None): # TODO: podría ser, además, un decorador en Python pero para usar dentro de una @synthdef o graph_func
        if _gl.current_synthdef is not None:
            return _gl.current_synthdef._build_ugen_graph(
                func, rates or [], prepend_args or [])
        else:
            msg = 'SynthDef wrap should be called inside a SynthDef graph function'
            raise Exception(msg)

    # L69
    def _init_build(self):
        #UGen.buildSynthDef = this; Ahora se hace como _gl.current_synthdef con un lock.
        self.constants = dict() # o {} crea un diccionario en Python
        self.constant_set = set() # será constantS_set?
        self.controls = []
        self.control_index = 0 # reset this might be not necessary
        self.max_local_bufs = None # la usa LocalBus*new1 y checka por nil.
        #inicializa todo en lugares separados cuando podría no hacerlo? VER.

    def _build_ugen_graph(self, graph_func, rates, prepend_args):
        # OC: save/restore controls in case of *wrap
        save_ctl_names = self.control_names # aún no se inicializó self.control_names usando new, es para wrap que se llama desde dentro de otra SynthDef ya en construcción.
        self.control_names = [] # None # no puede ser None acá
        self.prepend_args = prepend_args # Acá es una lista, no hay asArray.
        self._args_to_controls(graph_func, rates, len(self.prepend_args))
        result = graph_func(*(prepend_args + self._build_controls())) # usa func.valueArray(prepend_args ++ this.buildControls) buildControls tiene que devolver una lista.
        self.control_names = save_ctl_names
        return result

    #addControlsFromArgsOfFunc (llamada desde buildUGenGraph)
    def _args_to_controls(self, func, rates, skip_args=0):
        # var def, names, values,argNames, specs;
        if not inspect.isfunction(func):
            raise TypeError('@synthdef only apply to functions')

        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        arg_names = [x.name for x in params] # list(map(lambda x: x.name, params))
        if len(arg_names) < 1: return None

        # OC: OK what we do here is separate the ir, tr and kr rate arguments,
        # create one Control ugen for all of each rate,
        # and then construct the argument array from combining
        # the OutputProxies of these two Control ugens in the original order.
        names = arg_names[skip_args:]
        arg_values = [x.default for x in params] # list(map(lambda x: x.default, params))
        values = [x if x != inspect.Signature.empty else None for x in arg_values] # any replace method?
        values = values[skip_args:] # **** VER, original tiene extend, no se si es necesario acá (o allá), len(names) debería ser siempre igual a len(values), se puede aplicar "extend" como abajo, pero VER!
                                    # **** VER, puede ser que hace extend por si el valor de alguno de los argumentos es un array no literal.
                                    # **** def.prototypeFrame DEVUELVE NIL EN VEZ DE LOS ARRAY NO LITERALES!
                                    # **** Además, ver cómo es en Python porque no tendría las mismas restricciones que sclang
        values = self._apply_metadata_specs(names, values) # convierte Nones en ceros o valores por defecto
        rates += [0] * (len(names) - len(rates)) # VER: sclang extend, pero no trunca
        rates = [x if x is not None else 0.0 for x in rates]

        for i, name in enumerate(names):
            prefix = name[:2]
            value = values[i]
            lag = rates[i]

            msg = 'Lag value {} for {} arg {} will be ignored'
            # pero realmente me gustaría sacar los nombres x_param y reemplazarlos por anotaciones, es lo mismo y mejor, aunque se usan las anotaciones para otra cosa.
            if (lag == 'ir') or (prefix == 'i_'):
                if isinstance(lag, (int, float)) and lag != 0:
                    warnings.warn(msg.format(lag, 'i-rate', name))
                self.add_ir(name, value)
            elif (lag == 'tr') or (prefix == 't_'):
                if isinstance(lag, (int, float)) and lag != 0:
                    warnings.warn(msg.format(lag, 'trigger', name))
                self.add_tr(name, value)
            elif (lag == 'ar') or (prefix == 'a_'):
                if isinstance(lag, (int, float)) and lag != 0:
                    warnings.warn(msg.format(lag, 'audio', name))
                self.add_ar(name, value)
            else:
                if lag == 'kr': lag = 0.0
                self.add_kr(name, value, lag)

    # método agregado
    def _apply_metadata_specs(self, names, values):
        # no veo una forma conscisa como en sclang
        new_values = []
        if 'specs' in self.metadata:
            specs = self.metadata['specs']
            for i, value in enumerate(values):
                if value is not None:
                    new_values.append(value)
                else:
                    if names[i] in specs:
                        spec = xxx.as_spec(specs[names[i]]) # BUG: as_spec devuelve un objeto ControlSpec o None, implementan Array, Env, Nil, Spec y Symbol  **** FALTA no está hecha la clase Spec ni la función para los strings!
                    else:
                        spec = xxx.as_spec(names[i])
                    if spec is not None:
                        new_values.append(spec.default()) # BUG **** FALTA no está hecha la clase Spec/ControlSpec, no sé si default es un método
                    else:
                        new_values.append(0.0)
        else:
            new_values = [x if x is not None else 0.0 for x in values]
        return new_values # values no la reescribo acá por ser mutable

    # OC: Allow incremental building of controls.
    # estos métodos los usa solamente NamedControls desde afuera y no es subclase de SynthDef ni de UGen
    # BUG, BUG: de cada parámetro value hace value.copy, ver posibles consecuencias...
    def add_non_control(self, name, values): # lo cambio por _add_nc _add_non? este método no se usa en ninguna parte de la librería estandar
        self.add_control_name(scio.ControlName(name, None, 'noncontrol', # IMPLEMENTAR CONTROLNAME
            values, len(self.control_names))) # values hace copy *** VER self.controls/control_names no pueden ser None

    def add_ir(self, name, values): # *** VER dice VALUES en plural, pero salvo que se pase un array como valor todos los que calcula son escalares u objetos no iterables.
        self.add_control_name(scio.ControlName(name, len(self.controls), 'scalar', # *** VER self.controls/control_names no pueden ser None
            values, len(self.control_names))) # values *** VER el argumento de ControlName es defaultValue que puede ser un array para expansión multicanal de controles, pero eso puede pasar acá saliendo de los argumentos?

    def add_tr(self, name, values):
        self.add_control_name(scio.ControlName(name, len(self.controls), 'trigger', # *** VER self.controls/control_names no pueden ser None
            values, len(self.control_names))) # values hace copy, *** VER ControlName hace expansión multicanal como dice la documentación???

    def add_ar(self, name, values):
        self.add_control_name(scio.ControlName(name, len(self.controls), 'audio', # *** VER self.controls/control_names no pueden ser None
            values, len(self.control_names))) # values hace copy

    def add_kr(self, name, values, lags): # acá también dice lags en plural pero es un valor simple como string (symbol) o number según interpreto del código anterior.
        self.add_control_name(scio.ControlName(name, len(self.controls), 'control', # *** VER self.controls/control_names no pueden ser None
            values, len(self.control_names), lags)) # *** VER values y lag hacen copy

    # este también está expuesto como variente de la interfaz, debe ser el original.
    # el problema es que son internos de la implementación de la librería, no deberían ser expuestos al usuario.
    def add_control_name(self, cn): # lo llama también desde las ugens mediante _gl.current_synthdef, e.g. audiocontrol
        self.control_names.append(cn)
        self.all_control_names.append(cn)

    # L178
    def _build_controls(self): # llama solo desde _build_ugen_graph, retorna una lista
        nn_cns = [x for x in self.control_names if x.rate == 'noncontrol']
        ir_cns = [x for x in self.control_names if x.rate == 'scalar']
        tr_cns = [x for x in self.control_names if x.rate == 'trigger']
        ar_cns = [x for x in self.control_names if x.rate == 'audio']
        kr_cns = [x for x in self.control_names if x.rate == 'control']

        arguments = [0] * len(self.control_names)
        values = []
        index = None
        ctrl_ugens = None
        lags = None
        valsize = None

        for cn in nn_cns:
            arguments[cn.arg_num] = cn.default_value

        def build_ita_controls(ita_cns, ctrl_class, method):
            nonlocal arguments, values, index, ctrl_ugens
            if ita_cns:
                values = []
                for cn in ita_cns:
                    values.append(cn.default_value)
                index = self.control_index
                ctrl_ugens = getattr(ctrl_class, method)(ut.flat(values)) # XControl.xr(values.flat)
                ctrl_ugens = ut.as_list(ctrl_ugens) # .asArray
                ctrl_ugens = ut.reshape_like(ctrl_ugens, values) # .reshapeLike(values);
                for i, cn in enumerate(ita_cns):
                    cn.index = index
                    index += len(ut.as_list(cn.default_value))
                    arguments[cn.arg_num] = ctrl_ugens[i]
                    self._set_control_names(ctrl_ugens[i], cn)
        build_ita_controls(ir_cns, scio.Control, 'ir')
        build_ita_controls(tr_cns, scio.TrigControl, 'kr')
        build_ita_controls(ar_cns, scio.AudioControl, 'ar')

        if kr_cns:
            values = []
            lags = []
            for cn in kr_cns:
                values.append(cn.default_value)
                valsize = len(ut.as_list(cn.default_value))
                if valsize > 1:
                    lags.append(ut.wrap_extend(ut.as_list(cn.lag), valsize))
                else:
                    lags.append(cn.lag)
            index = self.control_index # TODO: esto puede ir abajo si los kr no cambian el índice.

            if any(x != 0 for x in lags):
                ctrl_ugens = scio.LagControl.kr(ut.flat(values), lags) # LagControl.kr(values.flat, lags) //.asArray.reshapeLike(values);
            else:
                ctrl_ugens = scio.Control.kr(ut.flat(values)) # Control.kr(values.flat)
            ctrl_ugens = ut.as_list(ctrl_ugens) # .asArray
            ctrl_ugens = ut.reshape_like(ctrl_ugens, values) # .reshapeLike(values);

            for i, cn in enumerate(kr_cns):
                cn.index = index
                index += len(ut.as_list(cn.default_value))
                arguments[cn.arg_num] = ctrl_ugens[i]
                self._set_control_names(ctrl_ugens[i], cn)

        self.control_names = [x for x in self.control_names
                              if x.rate != 'noncontrol']
        return arguments

    # L263
    def _set_control_names(self, ctrl_ugens, cn):
        if isinstance(ctrl_ugens, list):
            for ctrl_ugen in ctrl_ugens: # TODO:, posible BUG? Este loop me da la pauta de que no soporta más que un nivel de anidamiento? (!) Qué pasaba si hay más de un nivel acá?
                ctrl_ugen.name = cn.name
        else:
            ctrl_ugens.name = cn.name

    # L273
    def _finish_build(self):
        # estos métodos delegan en el homónimo de UGen (el ping pong)
        self._add_copies_if_needed() # ping, solo se usa para PV_Chain ugens, es un caso muy particular.
        self._optimize_graph() # llama a _init_topo_sort, _topological_sort hace lo mismo acá abajo, hace todo dos veces, parece. Y llama a self._index_ugens()
        self._collect_constants() # este método está en L489 pegado a optimizeGraph dentro de la lógica de topo sort, cambiado a orden de lectura
        self._check_inputs() # OC: Will die on error.

        # OC: re-sort graph. reindex.
        self._topological_sort() # llama a _init_topo_sort()
        self._index_ugens()
        # UGen.buildSynthDef = nil; esto lo pasé a SynthDef, está en try/except de _build

    def _add_copies_if_needed(self):
        # OC: could also have PV_UGens store themselves in a separate collection
        for child in self._width_first_ugens: # _width_first_ugens aún no lo inicializó porque lo hace en WithFirstUGen.addToSynth (solo para IFFT) en este caso, es una lista que agrego en __init__.
            if isinstance(child, xxx.PV_ChainUGen):
                child._add_copies_if_needed() # pong

    # L468
    # OC: Multi channel expansion causes a non optimal breadth-wise
    # ordering of the graph. The topological sort below follows
    # branches in a depth first order, so that cache performance
    # of connection buffers is optimized.

    # L472
    def _optimize_graph(self): # ping pong privato
        self._init_topo_sort()

        self._rewrite_in_progress = True # Comprueba en SynthDef:add_ugen que se llama desde las ugen, la variable es privada de SynthDef. No me cierra en que caso se produce porque si ugen.optimize_graph quiere agregar una ugen no fallaría?
        for ugen in self.children[:]: # ***** Hace children.copy.do porque modifica los valores de la lista sobre la que itera. VER RECURSIVIDAD: SI MODIFICA UN VALOR ACCEDIDO POSTERIORMENTE None.optimize_graph FALLA??
            ugen.optimize_graph() # pong, las ugens optimizadas se deben convertir en None dentro de la lista self.children, pasa en UGen.performDeadCodeElimination y en las opugens.
        self._rewrite_in_progress = False

        # OC: Fixup removed ugens.
        old_size = len(self.children)
        self.children = [x for x in self.children if x is not None] #children.removeEvery(#[nil]);  *** por qué no es un reject?
        if old_size != len(self.children):
            self._index_ugens()

    def _init_topo_sort(self): # ping # CAMBIADO A ORDEN DE LECTURA (sería orden de llamada?)
        self.available = []
        for ugen in self.children:
            ugen.antecedents = set()
            ugen.descendants = set()
        for ugen in self.children:
            # OC: This populates the descendants and antecedents.
            ugen.init_topo_sort() # pong
        for ugen in reversed(self.children):
            ugen.descendants = list(ugen.descendants) # VER: lo convierte en lista (asArray en el original) para ordenarlo y lo deja como lista. ugen.init_topo_sort() es la función que puebla el conjunto.
            ugen.descendants.sort(key=lambda x: x.synth_index) # VER: pero que pasa con antecedents? tal vez no se usa para hacer recorridos?
            # OC: All ugens with no antecedents are made available.
            ugen.make_available()

    def _index_ugens(self): # CAMBIADO A ORDEN DE LECTURA
        for i, ugen in enumerate(self.children):
            ugen.synth_index = i

    # L489
    def _collect_constants(self): # ping
        for ugen in self.children:
            ugen._collect_constants() # pong

    # L409
    def _check_inputs(self): # ping
        first_err = None
        for ugen in self.children: # *** Itera sobre self.children por enésima vez.
            err = ugen.check_inputs() # pong, en sclang devuelve nil o un string, creo que esos serían todos los casos según la lógica de este bloque.
            if err: # *** HACER *** EN SCLANG ES ASIGNA A err Y COMPRUEBA notNil, acá puede ser none, pero ver qué retornan de manera sistemática, ver return acá abajo.
                # err = ugen.class.asString + err;
                # err.postln;
                # ugen.dumpArgs; # *** OJO, no es dumpUGens
                if first_err is None: first_err = err
        if first_err:
            #"SynthDef % build failed".format(this.name).postln;
            raise Exception(first_err)
        return True # porque ugen.check_inputs() retorna nil y acá true

    def _topological_sort(self):
        self._init_topo_sort()
        ugen = None
        out_stack = []
        while len(self.available) > 0:
            ugen = self.available.pop()
            ugen.schedule(out_stack) # puebla out_stack. ugen.schedule() se remueve de los antecedentes, se agrega a out_stack y devuelve out_stack. Acá no es necesaria la reasignación.
        self.children = out_stack
        self._cleanup_topo_sort()

    def _cleanup_topo_sort(self):
        for ugen in self.children:
            ugen.antecedents = set()
            ugen.descendants = set()
            ugen.width_first_antecedents = [] # *** ÍDEM, OJO: no es SynthDef:_width_first_ugens, los nombres son confusos.

    # L428
    # OC: UGens do these.
    # Métodos para ping pong
    def add_ugen(self, ugen): # lo usan UGen y WithFirstUGen implementando el método de instancia addToSynth
        if not self._rewrite_in_progress:
            ugen.synth_index = len(self.children)
            ugen.width_first_antecedents = self._width_first_ugens[:] # with1sth antec/ugens refieren a lo mismo en distintos momentos, la lista es parcial para la ugen agregada.
            self.children.append(ugen)

    def remove_ugen(self, ugen): # # lo usan UGen y BinaryOpUGen para optimizaciones
        # OC: Lazy removal: clear entry and later remove all None entries # Tiene un typo, dice enties
        self.children[ugen.synth_index] = None

    def replace_ugen(self, a, b): # lo usa BinaryOpUGen para optimizaciones
        if not isinstance(b, ug.UGen):
            raise Exception('replace_ugen assumes a UGen')

        b.width_first_antecedents = a.width_first_antecedents
        b.descendants = a.descendants
        b.synth_index = a.synth_index
        self.children[a.synth_index] = b

        for item in self.children: # tampoco usa el contador, debe ser una desprolijidad después de una refacción, uso la i para el loop interno
            if item is not None:
                for i, input in enumerate(item.inputs):
                    if input is a:
                        aux = list(item.inputs) # TODO: hasta ahora es el único lugar donde se modifica ugen.inputs
                        aux[i] = b
                        item.inputs = tuple(aux)

    def add_constant(self, value): # lo usa UGen:collectConstants
        if value not in self.constant_set:
            self.constant_set.add(value) # es un set, como su nombre lo indica, veo que se usa por primera vez
            self.constants[value] = len(self.constants) # value lo setea UGen.collectConstants, el único método que llama a este y agrega las input de las ugens que son números (value es float)
                                                        # value (float) es la llave, el valor de la llave es el índice de la constante almacenada en la synthdef en el momento de la inserción.
                                                        # collect_constants es un método ping/pong (synthdef/ugen), se llama desde SynthDef._finish_build, antes de _check_inputs y re-sort
                                                        # es simplemente un conjunto de constantes que almacena como datos reusables de las synthdef cuyo valor se accede por el índice aquí generado con len.

    # L535
    # Método utilitario de SynthDef, debe ser original para debuguing.
    def dump_ugens(self): # no se usa, no está documentado, pero es ÚTIL! se puede hacer hasta acá y pasar a las ugens (pero hay que hacer addUGen, etc., acá)
        #ugen_name = None # esta no la usa, es un descuido del programador
        print(self.name)
        for ugen in self.children: # tampoco terminó usando el índice
            inputs = None
            if ugen.inputs is not None:
                inputs = [x.dump_name() if isinstance(x, ug.UGen)
                          else x for x in ugen.inputs] # ugen.inputs.collect {|in| if (in.respondsTo(\dumpName)) { in.dumpName }{ in }; }; # Las únicas clases que implementan dumpName son UGen, BasicOpUGen y OutputProxy, sería interfaz de UGen, sería if is UGen
            print([ugen.dump_name(), ugen.rate, inputs])

    # L549
    # OC: make SynthDef available to all servers
    def add(self, libname=None, completion_msg=None, keep_def=True):
        self.as_synthdesc(libname or 'global', keep_def) # BUG: puede que sea self.desc que parece que no se usa? en sclang declara y no usa la variable local desc. La cuestión es que este método hay que llamarlo para agregar la desc a la librería. Otra cosa confusa.
        if libname is None:
            servers = sv.Server.all_booted_servers() # BUG: no está probado o implementado
        else:
            servers = ds.SynthDescLib.get_lib(libname).servers
        for server in servers:
            self.do_send(server) # , completion_msg(server)) # BUG: completion_msg no se usa/recibe en do_send # BUG: no sé por qué usa server.value() en sclang

    # L645
    def as_synthdesc(self, libname='global', keep_def=True): # Subido, estaba abajo, lo usa add.
        stream = io.BytesIO(self.as_bytes()) # TODO: El problema es que esto depende de server.send_msg (interfaz osc)
        libname = libname or 'global'
        lib = ds.SynthDescLib.get_lib(libname) # BUG: no está probado
        desc = lib.read_desc_from_def(stream, keep_def, self, self.metadata) # BUG: no está probado
        return desc

    # L587
    def do_send(self, server): #, completion_msg): # BUG: parece que no existe un argumento que reciba completionMsg
        buffer = self.as_bytes()
        if len(buffer) < (65535 // 4): # BUG: acá hace dividido 4, en clumpBundles hace > 20000, en bytes se puede mandar más, ver que hace scsynth.
            server.send_msg('/d_recv', buffer) # BUG: completion_msg) ninunga función send especifica ni documenta parece tener un completionMsg, tampoco tiene efecto o sentido en las pruebas que hice
        else:
            if server.is_local:
                msg = 'SynthDef {} too big for sending. Retrying via synthdef file'
                warnings.warn(msg.format(self.name))
                self.write_def_file(SynthDef.synthdef_dir)
                server.send_msg('/d_load', str(SynthDef.synthdef_dir / (self.name + '.scsyndef'))) # BUG: , completionMsg)
            else:
                msg = 'SynthDef {} too big for sending'
                warnings.warn(msg.format(self.name))

    def as_bytes(self):
        stream = io.BytesIO() #(b' ' * 256) # tamaño prealocado pero en sclang este no es un tamaño fijo de retorno sino una optimización para el llenado, luego descarta lo que no se usó.
        write_def([self], stream) # Es Array-writeDef, hace asArray que devuelve [ a SynthDef ] porque Array-writeDef puede escribir varias synthdef en un def file. Tiene que ser una función para list abajo.
        return stream.getbuffer() # TODO: ver si hay conversiones posteriores. Arriba en as_synthdesc lo vuevle a convertir en CollStream...
                                             # el método asBytes se usa para enviar la data en NRT también, como array.
                                             # En do_send, arriba, está la llamada server.send_msg('/d_recv', self.as_bytes()), en sclang tiene que ser un array, ver implementación.
                                             # En sclang retorna un array de bytes (Int8Array)
                                             # En liblo, es un blob (osc 'b') que se mapea a una lista de int(s) (python2.x) o bytes (python3.x)
                                             # stream = bytearray(stream.getbuffer())
                                             # return [bytes(x) for x in stream] ?? pero esto no funciona con io.BytesIO(stream)

    def write_def_file(self, dir, overwrite=True, md_plugin=None):
        if ('shouldNotSend' not in self.metadata)\
        or ('shouldNotSend' in self.metadata and not self.metadata['shouldNotSend']): # BUG: ver condición, sclang usa metadata.tryPerform(\at, \shouldNotSend) y tryPerform devuelve nil si el método no existe. Supongo que synthdef.metadata *siempre* tiene que ser un diccionario y lo único que hay que comprobar es que la llave exista y -> # si shouldNotSend no existe TRUE # si shouldNotSend existe y es falso TRUE # si shouldNotSend existe y es verdadero FALSO
            dir = dir or SynthDef.synthdef_dir # TODO: ver indentación, parece que se puede pero tal vez no sea muy PEP8
            dir = pathlib.Path(dir) # dir puede ser str
            file_existed_before = pathlib.Path(dir / (self.name + '.scsyndef')).exists()
            self.write_def_after_startup(self.name, dir, overwrite)
            if overwrite or not file_existed_before:
                desc = self.as_synthdesc()
                desc.metadata = self.metadata
                ds.SynthDesc.populate_metadata_func(desc) # BUG: (populate_metadata_func) aún no sé quién asigna la función a esta propiedad
                desc.write_metadata(dir / self.name, md_plugin) # BUG: No está implementada del todo, faltan dependencias.

    def write_def_after_startup(self, name, dir, overwrite=True): # TODO/BUG/WHATDA, este método es sclang Object:writeDefFile
        def defer_func():
            nonlocal name
            if name is None:
                raise Exception('missing SynthDef file name')
            else:
                name = pathlib.Path(dir / (name + '.scsyndef'))
                if overwrite or not name.exists():
                    with open(name, 'wb') as file:
                        ds.AbstractMDPlugin.clear_metadata(name) # BUG: No está implementado
                        write_def([self], file)
        # // make sure the synth defs are written to the right path
        sa.StartUp.defer(defer_func) # BUG: No está implementada

    def write_def(self, file):
        try:
            file.write(struct.pack('B', len(self.name))) # 01 putPascalString, unsigned int8 -> bytes
            file.write(bytes(self.name, 'ascii')) # 02 putPascalString

            self.write_constants(file)

            # //controls have been added by the Control UGens
            file.write(struct.pack('>i', len(self.controls))) # putInt32
            for item in self.controls:
                file.write(struct.pack('>f', item)) # putFloat

            allcns_tmp = [x for x in self.all_control_names
                          if x.rate != 'noncontrol'] # reject
            file.write(struct.pack('>i', len(allcns_tmp))) # putInt32
            for item in allcns_tmp:
                # comprueba if (item.name.notNil) # TODO: posible BUG? (ver arriba _set_control_names). Pero no debería poder agregarse items sin no son ControlNames. Arrays anidados como argumentos, de más de un nivel, no están soportados porque fallar _set_control_names según analicé.
                #if item.name: # TODO: y acá solo comprueba que sea un string no vacío, pero no comprueba el typo ni de name ni de item.
                if not isinstance(item, scio.ControlName): # TODO: test para debugear luego.
                    raise Exception('** Falla Test ** SynthDef self.all_control_names contiene un objeto no ControlName')
                elif not item.name: # ídem.
                    raise Exception('** Falla Test ** SynthDef self.all_control_names contiene un ControlName con name vacío = {}'.format(item.name))
                file.write(struct.pack('B', len(item.name))) # 01 putPascalString, unsigned int8 -> bytes
                file.write(bytes(item.name, 'ascii')) # 02 putPascalString
                file.write(struct.pack('>i', item.index))

            file.write(struct.pack('>i', len(self.children))) # putInt32
            for item in self.children:
                item.write_def(file)

            file.write(struct.pack('>h', len(self.variants))) # putInt16
            if len(self.variants) > 0:
                allcns_map = dict()
                for cn in allcns_tmp:
                    allcns_map[cn.name] = cn

                for varname, pairs in self.variants.items():
                    varname = self.name + '.' + varname
                    if len(varname) > 32:
                        msg = "variant '{}' name too log, not writing more variants"
                        warnings.warn(msg.format(varname))
                        return False

                    varcontrols = self.controls[:]
                    for cname, values in pairs.items():
                        if allcns_map.keys().isdisjoint([cname]):
                            msg = "control '{}' of variant '{}' not found, not writing more variants"
                            warnings.warn(msg.format(cname, varname))
                            return False

                        cn = allcns_map[cname]
                        values = ut.as_list(values)
                        if len(values) > len(ut.as_list(cn.default_value)):
                            msg = "control: '{}' of variant: '{}' size mismatch, not writing more variants"
                            warnings.warn(msg.format(cname, varname))
                            return False

                        index = cn.index
                        for i, val in enumerate(values):
                            varcontrols[index + i] = val

                    file.write(struct.pack('B', len(varname))) # 01 putPascalString, unsigned int8 -> bytes
                    file.write(bytes(varname, 'ascii')) # 02 putPascalString
                    for item in varcontrols:
                        file.write(struct.pack('>f', item)) # putFloat
            return True
        except Exception as e:
            raise Exception('SynthDef: could not write def') from e

    def write_constants(self, file):
        size = len(self.constants)
        arr = [None] * size
        for value, index in self.constants.items():
            arr[index] = value
        file.write(struct.pack('>i', size)) # putInt32
        for item in arr:
            file.write(struct.pack('>f', item)) # putFloat

    # // Only write if no file exists
    def write_once(self, dir, md_plugin): # Nota: me quedo solo con el método de instancia, usar el método de clase es equivalente a crear una instancia sin llamar a add u otro método similar.
        self.write_def_file(dir, False, md_plugin) # TODO: ver la documentación, este método es obsoleto.

    # L561
    @classmethod
    def remove_at(cls, name, libname='global'): # TODO: Este método lo debe usar en SynthDesc.sc. Ojo que hay mil métodos removeAt.
        lib = ds.SynthDescLib.get_lib(libname)
        lib.remove_at(name)
        for server in lib.servers:
            server.send_msg('/d_free', name) # BUG: no entiendo por qué usa server.value (que retorna el objeto server). Además, send_msg también es método de String en sclang lo que resulta confuso.

    # L570
    # // Methods for special optimizations

    # // Only send to servers.
    def send(self, server=None): # BUG: completion_msg) ninunga función send especifica ni documenta parece tener un completionMsg, tampoco tiene efecto o sentido en las pruebas que hice
        servers = ut.as_list(server or sv.Server.all_booted_servers()) # BUG: no está probado o implementado
        for each in servers:
            if not each.has_booted(): # BUG: no está implementada, creo.
                msg = "Server '{}' not running, could not send SynthDef"
                warnings.warn(msg.format(each.name)) # BUG en sclang: imprime server.name en vez de each.name
            if 'shouldNotSend' in self.metadata and self.metadata['shouldNotSend']:
                self._load_reconstructed(each) # BUG: completion_msg)
            else:
                self.do_send(each) # BUG: completion_msg)

    # L653
    # // This method warns and does not halt because
    # // loading existing def from disk is a viable
    # // alternative to get the synthdef to the server.
    def _load_reconstructed(self, server): # *** BUG: completion_msg) ninunga función send especifica ni documenta parece tener un completionMsg, tampoco tiene efecto o sentido en las pruebas que hice
        msg = "SynthDef '{}' was reconstructed from a .scsyndef file, "
        msg += "it does not contain all the required structure to send back to the server"
        warnings.warn(msg.format(self.name))
        if server.is_local:
            msg = "loading from disk instead for Server '{}'"
            warnings.warn(msg.format(server))
            bundle = ['/d_load', self.metadata['loadPath']] # BUG: completion_msg] # BUG: completion_msg) *** ACÁ SE USA COMPLETION_MSG ***
            server.send_bundle(None, bundle)
        else:
            msg = "Server '{}' is remote, cannot load from disk"
            raise Exception(msg.format(server))

    # // Send to server and write file.
    def load(self, server, completion_msg, dir=None): # *** BUG: completion_msg, parámetro intermedio
        server = server or sv.Server.default
        if 'shouldNotSend' in self.metadata and self.metadata['shouldNotSend']:
            self._load_reconstructed(server) # BUG: completion_msg)
        else:
            # // should remember what dir synthDef was written to
            dir = dir or SynthDef.synthdef_dir
            dir = pathlib.Path(dir)
            self.write_def_file(dir)
            server.send_msg('/d_load', str(dir / (self.name + '.scsyndef'))) # BUG: completion_msg) tendría que ver cómo es que se usa acá, no parece funcionar en sclang pero es un msj osc... (?)

    # L615
    # // Write to file and make synth description.
    def store(self, libname='global', dir=None, completion_msg=None, md_plugin=None): # *** BUG: completion_msg, parámetro intermedio
        lib = ds.SynthDescLib.get_lib(libname)
        dir = dir or SynthDef.synthdef_dir
        dir = pathlib.Path(dir)
        path = dir / (self.name + '.scsyndef')
        #if ('shouldNotSend' in self.metadata and not self.metadata['shouldNotSend']): # BUG, y confuso en sclang. falseAt devuevle true si la llave no existe, trueAt es equivalente a comprobar 'in' porque si no está la llave es false, pero falseAt no es lo mismo porque si la llave no existe sería lo mismo que ubiese false.
        if 'shouldNotSend' not in self.metadata or not self.metadata['shouldNotSend']: # BUG: esto es equivalente a falseAt solo si funciona en corto circuito.
            with open(path, 'wb') as file:
                write_def([self], file)
            lib.read(path)
            for server in lib.servers:
                self.do_send(server) # BUG: server.value y completion_msg
            desc = lib.at(self.name)
            desc.metadata = self.metadata
            ds.SynthDesc.populate_metadata_func(desc) # BUG: (populate_metadata_func) aún no sé quién asigna la función a esta propiedad
            desc.write_metadata(path, md_plugin)
        else:
            lib.read(path)
            for server in lib.servers:
                self._load_reconstructed(server) # BUG: completion_msg)

    # L670
    # // This method needs a reconsideration
    def store_once(self, libname='global', dir=None, completion_msg=None, md_plugin=None): # *** BUG: completion_msg, parámetro intermedio
        dir = dir or SynthDef.synthdef_dir
        dir = pathlib.Path(dir)
        path = dir / (self.name + '.scsyndef')
        if not path.exists():
            self.store(libname, dir, completion_msg, md_plugin)
        else:
            # // load synthdesc from disk
            # // because SynthDescLib still needs to have the info
            lib = ds.SynthDescLib.get_lib(libname)
            lib.read(path)

    # L683
    def play(self, target, args, add_action='addToHead'):
        raise Exception('SynthDef.play no está implementada') # BUG: esta función de deprecated y des-deprecated


# decorator syntax
class synthdef():
    '''Clase para ser usada como decorador y espacio de nombres de decoradores,
    decoradores para ser usados simplemente como atajo sintáctico de las
    funciones más comunes, instancia sin y con parámetros y add.

    @synthdef
    def synth1():
        pass

    @synthdef.params(
        rates=[],
        variants={},
        metadata={})
    def synth2():
        pass

    @synthdef.add()
    def synth3():
        pass
    '''

    def __new__(cls, graph_func):
        return SynthDef(graph_func.__name__, graph_func)

    @staticmethod
    def params(rates=None, prepend_args=None, variants=None, metadata=None):
        def make_def(graph_func):
            return SynthDef(graph_func.__name__, graph_func,
                            rates, prepend_args, variants, metadata)
        return make_def

    @staticmethod
    def add(libname=None, completion_msg=None, keep_def=True):
        '''Es atajo solo para add, la SynthDef se construye con los parametros
        por defecto, el caso más simple, si se quieren más parámetros no tiene
        sentido agregar todo acá, se crea con params y luego se llama a add.
        De lo contrario el atajo termina siendo más largo y menos claro.'''
        def make_def(graph_func):
            sdef = synthdef(graph_func)
            sdef.add(libname, completion_msg, keep_def)
            return sdef
        return make_def


# Collection SynthDef support.

def write_def(lst, file):
    '''Escribe las SynthDefs contenidas en la lista lst en el archivo file.
    file es un stream en el que se puede escribir.'''

    file.write(b'SCgf') # BUG: es putString y dice: 'a null terminated String', parece estar correcto porque muestra los nombres bien. # 'all data is stored big endian' Synth Definition File Format. En este caso no afecta porque son bytes. Todos los enteros son con signo.
    file.write(struct.pack('>i', 2)) # file.putInt32(2); // file version
    file.write(struct.pack('>h', len(lst))) # file.putInt16(this.size); // number of defs in file.
    for synthdef in lst:
        synthdef.write_def(file)