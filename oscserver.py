
import threading
import atexit
import time as _time # BUG: ver qué time es abajos

import liblo as _lo

import supercollie.utils as utl
import supercollie.netaddr as nad
from . import main # cíclico
from . import clock as clk # es cíclico a través de main


DEFAULT_CLIENT_PORT = 57120
DEFAULT_CLIENT_PROTOCOL = _lo.UDP


class OSCServer():
    def __init__(self, port=DEFAULT_CLIENT_PORT,
                 proto=DEFAULT_CLIENT_PROTOCOL):
        self.port = port
        self._starting_port = port
        self._port_range = 10
        self.proto = proto
        self._running = False
        self._recv_funcs = set()
        self._bundle_timestamp = None

    def start(self):
        if self._running:
            return
        self._init_osc()
        self._running = True
        atexit.register(self.stop)

    def _init_osc(self):
        try:
            self._osc_server_thread = _lo.ServerThread(self.port, self.proto)
            self._osc_server_thread.start()
            self._osc_server_thread.add_method(None, None, self._recv, self)
            self._osc_server_thread.add_bundle_handlers(self._start_handler,
                                                        self._end_handler,
                                                        self)
        except _lo.ServerError as e:
            if e.num == 9904: # b'cannot find free port'
                if self.port < self.port + self._port_range:
                    self.port += 1
                    self._init_osc()
            else:
                raise e

    @staticmethod
    def _recv(*msg):
        obj = msg[4]
        if obj._bundle_timestamp is not None:
            time = obj._bundle_timestamp # BUG: lo tiene otra referencia temporal
        else:
            time = _time.time() # BUG: ver qué time es
        addr = nad.NetAddr(msg[3].hostname, msg[3].port)
        arr = [msg[0]]
        arr.extend(msg[1])
        print('OSCServer._recv:', arr, time, addr, obj.port)
        obj._bundle_timestamp = None

        def sched_func():
            print('OSCServer._recv en AppClock')
            for func in obj._recv_funcs:
                 func(arr, time, addr, obj.port)
        clk.AppClock.sched(0, sched_func)  # NOTE: Lo envía al thread de AppClock que es seguro.

    @staticmethod
    def _start_handler(*msg):
        print('start handler')
        msg[1]._bundle_timestamp = msg[0]

    @staticmethod
    def _end_handler(*msg):
        pass  # No le veo uso por ahora.

    def add_recv_func(self, func):
        self._recv_funcs.add(func)

    def remove_recv_func(self, func):
        self._recv_funcs.remove(func)

    # por lo que hace es redundante
    # def replace_recv_func(self, func, new_func):
    #     self._recv_funcs.remove(func)
    #     self._recv_funcs.add(func)

    # openPorts y openUDPPort(portNum) irían en Main
    # creo que con liblo tengo que crear un server por puerto

    def stop(self):
        if not self._running: return
        self._stop_osc()
        self._running = False
        atexit.unregister(self.stop)

    def _stop_osc(self):
        self._osc_server_thread.stop()
        self._osc_server_thread.free()

    def running(self):
        return self._running

    # *** Métodos de NetAddr ***

    # def port(self): # TODO: sería NetAddr.langPort, haciendo que el atributo port sea privado e inmutable.
    #     return self._port

    # def send_raw(self, target, raw_bytes): # send a raw message without timestamp to the addr (es int8array, creo)
    #     msg = _lo.Message('/', raw_bytes) # sclang no especifica dirección osc.
    #     self._osc_server_thread.send(target, msg) # posible BUG: VER: para liblo el tipo bytes envía un mensaje blob.
    #                                               # En Server:sendSynthDef hace this.sendMsg("/d_recv", buffer); buffer es Int8Array que lee de un archivo.
    #                                               # No se usa en ninguna parte de la librería de clases salvo para Server-sendRaw que tampoco se usa.

    def send_msg(self, target, *args):
        """args es la lista de valores para crear un mensaje"""
        msg = _lo.Message(*args) # BUG: falta la conversión de tipos con tupla
        self._osc_server_thread.send(target, msg) # BUG: AttributeError: 'Client' object has no attribute '_osc_server_thread'. Este error no es informativo de que el cliente no está en ejecución (la variable de instsancia no existe)

    def send_bundle(self, target, time, *args): # // sclang warning: this primitive will fail to send if the bundle size is too large # // but it will not throw an error.  this needs to be fixed
        """args son listas de valores para crear varios mensajes"""
        messages = [_lo.Message(*x) for x in args] # BUG: falta la conversión de tipos con tupla
                                                   # BUG: ver si los bundles en sc pueden ser recursivos!!!
        time = time or 0 # BUG: qué pasaba con valores negativos?
        bundle = _lo.Bundle(float(time), *messages)
        self._osc_server_thread.send(target, bundle)

    def send_status_msg(self):
        self.send_msg('/status')

    def sync(self, condition=None, bundle=None, latency=0): # BUG: dice array of bundles, los métodos bundle_size y send_bundle solo pueden enviar uno. No me cierra/me confunde en sclang porque usa send bundle agregándole latencia.
        condition = condition or threading.Condition()
        if bundle is None:
            id = self.make_sync_responder(condition)
            self.send_bundle(('127.0.0.1', 57120), latency, ['/sync', id]) # TEST BUG: falta default target que creo que sería el servidor por defecto, está puesto sclang
            with condition:
                condition.wait() # BUG: poner timeout y lanzar una excepción?
        else:
            # BUG: esto no está bien testeado, y acarreo el problema del tamaño exacto de los mensajes.
            sync_size = self.msg_size(['/sync', utl.UniqueID.next()])
            max_size = 65500 - sync_size # BUG: 65500 es un límite práctico que puede estar mal si las cuentas de abajo están mal.
            if self.bundle_size(bundle) > max_size:
                clumped_bundles = self.clump_bundle(bundle, max_size)
                for item in clumped_bundles:
                    id = self.make_sync_responder(condition)
                    item.append(['/sync', id])
                    self.send_bundle(('127.0.0.1', 57120), latency, *item) # TEST BUG: falta default target que creo que sería el servidor por defecto, está puesto sclang
                    latency += 1e-9 # nanosecond, TODO: esto lo hace así no sé por qué.
                    with condition:
                        condition.wait() # BUG: poner timeout y lanzar una excepción?
            else:
                id = self.make_sync_responder(condition)
                bundle = bundle[:]
                bundle.append(['/sync', id])
                self.send_bundle(('127.0.0.1', 57120), latency, *bundle) # TEST BUG: falta default target que creo que sería el servidor por defecto, está puesto sclang
                with condition:
                    condition.wait() # BUG: poner timeout y lanzar una excepción?

    def make_sync_responder(self, condition): # TODO: funciona en realación al método de arriba.
        id = utl.UniqueID.next()

        def responder(*msg):
            print(' ****** added method argument *msg:', msg)
            if msg[1][0] == id: # TODO: msg es ('/synced', [1001], 'i', <liblo.Address object at 0x7f56c88b3d80>, None)
                self._osc_server_thread.del_method('/synced', 'i') # BUG: no dice qué tipo de dato es typespec # BUG: borra la función por path y tipo de dato no por la identidad de la función.
                with condition:
                    condition.notify()
        self._osc_server_thread.add_method('/synced', 'i', responder)
        return id

    # def send_clumped_bundles(self, time, *args): # TODO: importante, lo usa para enviar paquetes muy grandes como stream, liblo tira error y no envía
    def clump_bundle(self, msg_list, new_bundle_size): # msg_list siempre es un solo bundle [['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        ret = [[]]
        clump_count = 0
        acc_size = 0
        aux = 0 # solo inicializo porque se usa dentro del loop
        for item in msg_list:
            aux = self.msg_size(item)
            if acc_size + aux > new_bundle_size: # BUG: 65500 es un límite práctico que puede estar mal si las cuentas de abajo están mal.
                acc_size = aux
                clump_count += 1
                ret.append([])
                ret[clump_count].append(item)
            else:
                acc_size += aux
                ret[clump_count].append(item)
        if len(ret[0]) == 0: ret.pop(0)
        return ret

    def msg_size(self, arg_list): # arg_list siempre es ['/path', arg1, arg2, ..., argN]
        size = 0 # bytes
        typetags = -1 # path no cuenta
        aux = 0 # solo inicializo porque se usa dentro del loop
        for item in arg_list:
            t = type(item)
            if t is str:
                aux = len(item)
                mod4 = aux & 3 # aux % 4
                size += aux
                if mod4:
                    size += 4 - mod4 # alineamiento
                else:
                    size += 4 # null y alineamiento
            elif t is bytes:
                aux = 4 # size count
                aux += len(item)
                mod4 = aux & 3 # aux % 4
                size += aux
                if mod4:
                    size += 4 - mod4 # alineamiento
            elif t is int or t is float or t is tuple:
                size += 4 # BUG: 8 si se usan doubles
            else:
                raise TypeError('invalid type ({}) for OSC message'.format(t)) # BUG: pueden haber tipos de datos que son válidos porque liblo traduce después?
            typetags += 1
        size += 1 # 1 byte para la ',' del type tag
        size += typetags # type tag por cada argumento osc
        mod4 = (1 + typetags) & 3 # (1 + typetags) % 4
        if mod4:
            size += 4 - mod4 # alienamiento
        return size # bytes # + 12 # BUG: falta algo, acá se pueden sumar 12 por: 8 bytes udp (BUG: depende de proto) header, 20 bits (redondeado a 4 bytes con alineamiento aunque no se si corresponde) ip header, igual me faltan alrededor de 20 bytes entre msg y bundle, salvo que sea algo dinámico y me falen más. En sclang hay una nota que justo son 20 bytes: // 65515 = 65535 - 16 - 4 (sync msg size)

    def bundle_size(self, args): # args siempre es [['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        size = 0
        for item in args:
            size += self.msg_size(item)
        return size + 40 # bytes # BUG: 8 bytes para '#bundle', 8 para time tag, 4 para el tamaño del atado, pero la cuenta en msg está mal, falta(n) algo(s). Y creo que los mensajes pueden tener distinto formato, no me quedó claro.
