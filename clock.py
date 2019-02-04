"""Clock.sc"""

import threading as _threading
import time as _time
import sys as _sys
import traceback as _traceback
import math as _math
from queue import PriorityQueue as _PriorityQueue
from queue import Full as _Full
from numbers import Real as _Real
#import sched tal vez sirva para AppClock (ver scd)
#Event = collections.namedtuple('Event', []) podría servir pero no se pueden agregar campos dinámicamente, creo, VER

import supercollie._global as _gl
import supercollie.builtins as bi


# // clocks for timing threads.

class Clock(_threading.Thread): # ver std::copy y std::bind
    def __new__(cls):
        raise NotImplementedError('Clock is an abstract class')

    @classmethod
    def play(cls, task):
        cls.sched(0, task)
    @classmethod
    def seconds(cls): # seconds es el tiempo lógico de cada thread
        return _gl.this_thread.seconds() # BUG: no me quedan claras las explicaciones dispersas en al documentación Process, Thread, Clock(s)

    # // tempo clock compatibility
    @classmethod
    def beats(cls):
        return _gl.this_thread.seconds()
    @classmethod
    def beats2secs(cls, beats):
        return beats
    @classmethod
    def secs2beats(cls secs):
        return secs
    @classmethod
    def beats2bars(cls):
        return 0
    @classmethod
    def bars2beats(cls):
        return 0
    @classmethod
    def time_to_next_beat(cls):
        return 0
    @classmethod
    def next_time_on_grid(cls, quant=1, phase=0):
        if quant == 0:
            return cls.beats() + phase
        if phase < 0:
            phase = bi.mod(phase, quant)
        return bi.roundup(cls.beats() - bi.mod(phase, quant), quant)


class SystemClock(Clock): # TODO: creo que esta sí podría ser una ABC singletona
    _SECONDS_FROM_1900_TO_1970 = 2208988800 # (int32)UL # 17 leap years
    _NANOS_TO_OSC = 4.294967296 # PyrSched.h: const double kNanosToOSC  = 4.294967296; // pow(2,32)/1e9
    _MICROS_TO_OSC = 4294.967296 # PyrSched.h: const double kMicrosToOSC = 4294.967296; // pow(2,32)/1e6
    _SECONDS_TO_OSC = 4294967296. # PyrSched.h: const double kSecondsToOSC  = 4294967296.; // pow(2,32)/1
    _OSC_TO_NANOS = 0.2328306436538696# PyrSched.h: const double kOSCtoNanos  = 0.2328306436538696; // 1e9/pow(2,32)
    _OSC_TO_SECONDS =  2.328306436538696e-10 # PyrSched.h: const double kOSCtoSecs = 2.328306436538696e-10;  // 1/pow(2,32)

    _instance = None # singleton instance

    def __new__(cls):
        #_host_osc_offset = 0 # int64
        #_host_start_nanos = 0 # int64
        #_elapsed_osc_offset = 0 # int64
        #_rsync_thread # syncOSCOffsetWithTimeOfDay resyncThread
        #_time_of_initialization # original es std::chrono::high_resolution_clock::time_point
        #monotonic_clock es _time.monotonic()? usa el de mayor resolución
        #def dur_to_float, ver
        #_run_sched # gRunSched es condición para el loop de run
        if cls._instance is None:
            obj = cls()
            _threading.Thread.__init__(obj)
            obj._task_queue = _PriorityQueue() # BUG: inQueue infinite by default, ver cómo y donde setea el tamaño de la pila sclang, put(block=False) puede tierar Full igualmente
            obj._sched_cond = _threading.Condition() # VER, tal vez no debería ser reentrante
            obj.start()
            obj._sched_init()
            cls._instance = obj
            return obj
        else:
            raise Exception('there is one SystemClock instance already') # BUG: sclang devuelve otras instancias lo que es confuso, no tiene sentido

    def _sched_init(self): # L253 inicia los atributos e.g. _time_of_initialization
        #time.gmtime(0).tm_year # must be unix time
        self._time_of_initialization = _time.time()
        self._host_osc_offset = 0 # int64

        self._sync_osc_offset_with_tod()
        self._host_start_nanos = int(self._time_of_initialization / 1e9) # time.time_ns() -> int v3.7
        self._elapsed_osc_offset = int(
            self._host_start_nanos * SystemClock._NANOS_TO_OSC) + self._host_osc_offset

        print('_sched_init fork thread')

        # same every 20 secs
        self._resync_cond = _threading.Condition() # VER, aunque el uso es muy simple (gResyncThreadSemaphore)
        self._run_resync = False # test es true en el loop igual que la otra
        self._resync_thread = _threading.Thread( # AUNQUE NO INICIA EL THREAD EN ESTA FUNCIÓN
            target=self._resync_thread_func, daemon=True)
        self._resync_thread.start()

    def _sync_osc_offset_with_tod(self): # L314, esto se hace en _rsync_thread
    	# Original comment:
        # generate a value gHostOSCoffset such that
    	# (gHostOSCoffset + systemTimeInOSCunits)
    	# is equal to gettimeofday time in OSCunits.
    	# Then if this machine is synced via NTP, we are synced with the world.
    	# more accurate way to do this??
        number_of_tries = 1
        diff = 0 # int64
        min_diff = 0x7fffFFFFffffFFFF; # int64, a big number to miss
        new_offset = self._host_osc_offset

        for i in range(0, number_of_tries):
            system_time_before = _time.perf_counter()
            time_of_day = _time.time()
            system_time_after = _time.perf_counter()

            system_time_before = int(system_time_before / 1e6) # to usecs
            system_time_after = int(system_time_after / 1e6)
            diff = system_time_after - system_time_before

            if diff < min_diff:
                min_diff = diff

                system_time_between = system_time_before + diff // 2
                system_time_in_osc_units = int(
                    system_time_between * SystemClock._NANOS_TO_OSC)
                time_of_day_in_osc_units = (int(
                    time_of_day + SystemClock._SECONDS_FROM_1900_TO_1970) << 32) + int(time_of_day / 1e6 * SystemClock._MICROS_TO_OSC)

                new_offset = time_of_day_in_osc_units - system_time_in_osc_units
        # end for
        self._host_osc_offset = new_offset
        print('new offset:', self._host_osc_offset)

    def _resync_thread_func(self): # L408, es la función de _rsync_thread
        self._run_resync = True
        while self._run_resync:
            with self._resync_cond:
                self._resync_cond.wait(20)
            if not self._run_resync: return

            self._sync_osc_offset_with_tod()
            self._elapsed_osc_offset = int(
                self._host_start_nanos * SystemClock._NANOS_TO_OSC) + self._host_osc_offset

    def _sched_cleanup(self): # L265 es para rsync_thread join, la exporta como interfaz, pero no sé si no está mal llamada 'sched'
        with self._resync_cond:
            self._run_resync = False
            self._resync_cond.notify() # tiene que interrumpir el wait
        self._resync_thread.join()

    # ver si estas funciones no serían globales y cuales no usa en esta clase, ver PyrSched.h
    def elapsed_time(self) -> float: # devuelve el tiempo del reloj de mayor precisión menos _time_of_initialization
        return _time.time() - self._time_of_initialization

    def monotonic_clock_time(self) -> float: # monotonic_clock::now().time_since_epoch(), no sé dónde usa esto
        return _time.monotonic() # en linux es hdclock es time.perf_counter(), no se usa la variable que declara

    def elapsed_time_to_osc(self, elapsed: float) -> int: # retorna int64
        return int(elapsed * SystemClock._SECONDS_TO_OSC) + self._elapsed_osc_offset

    def osc_to_elapsed_time(self, osctime: int) -> float: # L286
        return float(osctime - self._elapsed_osc_offset) * SystemClock._OSC_TO_SECONDS

    def osc_time(self) -> int: # L309, devuleve elapsed_time_to_osc(elapsed_time())
        return self.elapsed_time_to_osc(self.elapsed_time())

    def sched_add(self, secs, task): # L353, ver los otros sched_ y cuáles son parte de la interfaz
        # gLangMutex must be locked # es self._sched_cond y bloquea acá, luego ver quién llama en sclang
        with self._sched_cond:
            item = (elapsed, secs, task) # BUG, BUG: elapsed? ver qué hice...

            if self._task_queue.empty():
                prev_time = -1e10
            else:
                prev_time = self._task_queue.queue[0][0] # queue.queue no está documentado?

            try:
                self._task_queue.put(item, block=False) # Full exception BUG: put de PriorityQueue es infinita por defecto, pero put(block=False) solo agrega si hay espacio libre inmediatamente o tira Full.
                self._task_queue.task_done() # se necesita siendo el mismo thread?
                #if type(task) is supercollie.Coroutine # no está definida BUG: *************************
                #    task.next_beat = secs
                if self._task_queue.queue[0][0] != prev_time:
                    with self._sched_cond:
                        self._sched_cond.notify() #_all()
            except _Full:
                print('SystemClock ERROR: scheduler queue is full')

    def sched_stop(self):
        # usa gLangMutex locks
        with self._sched_cond:
            if self._run_sched:
                self._run_sched = False
                self._sched_cond.notify() #_all()
        self.join() # VER esto, la función sched_stop se llama desde otro hilo y es sincrónica allí
        # tal vez debería juntar con _resync_thread

    def sched_clear(self): # L387, llama a schedClearUnsafe() con gLangMutex locks, esta función la exporta con SCLANG_DLLEXPORT_C
        with self._sched_cond:
            if _self._run_sched:
                del self._task_queue # BUG: en realidad tiene un tamaño que reusa y no borra, pero no sé dónde se usa esta función, desde sclang usa *clear
                self._task_queue = _PriorityQueue()
                self._sched_cond.notify() #_all()

    #def sched_run_func(self): # L422, es la función de este hilo, es una función estática, es run acá (salvo que no subclasee)
    def run(self):
        self._run_sched = True
        while True:
            # wait until there is something in scheduler
            while self._task_queue.empty():
                with self._sched_cond:
                    self._sched_cond.wait() # ver qué pasa con los wait en el mismo hilo, si se produce
                if not self._run_sched: return

            # wait until an event is ready
            now = 0
            sched_secs = 0
            sched_point = 0
            while not self._task_queue.empty():
                now = _time.time()
                sched_secs = self._task_queue.queue[0][0] # no documentado
                sched_point = self._time_of_initialization + sched_secs # sched_secs (el retorno del generador) se tiene que setear desde afuera con + elapsed_time()
                print('sched_secs, now and point:', sched_secs, now, sched_point)
                if now > sched_point: break # va directo al loop siguiente
                print('wait sched_secs:', sched_secs)
                with self._sched_cond:
                    self._sched_cond.wait(sched_secs) # **** !!!!!!!! **** (sched_point) # notify lo tiene que interrumpir cuando se agrega otra tarea, ver por qué usa wait_until en c++ que usa tod (probable drift)
                if not self._run_sched: return

            # perform all events that are ready
            while not self._task_queue.empty() and (now >= self._time_of_initialization + self._task_queue.queue[0][0]): # **** si está vacía va a tirar error o hace corto?
                item = self._task_queue.get()
                sched_time = item[0]
                task = item[1]
                #if type(task) is supercollie.Coroutine # no está definida  BUG *********************************
                #    task.next_beat = None
                try:
                    delta = task.__next__() # creo que setea en nil el valor de retorno anterior,
                                    # vuelve a poner la rutina en la pila de sclang y
                                    # la ejecuta, para retomar desde donde estaba y tener
                                    # el nuevo valor de retorno que, si es número,
                                    # se convierte en el nuevo valor de espera, por
                                    # eso setea en Nil el valor de retorno en la pila
                                    # de sclang y llama a runAwakeMessage. Tengo que
                                    # ver cómo se comporta la propiedad next_beat y
                                    # si acá se usa simplemente next sobre un generador.
                    if isinstance(delta, _Real) and not isinstance(delta, bool): # ver si los generadores retornan None cuando terminan, y ver como se escríbe "is not"
                        time = sched_time + delta
                        self.sched_add(time, task)
                except StopIteration:
                    pass
                except Exception:
                    # hay que poder recuperar el loop ante cualquier otra excepción...
                    # imprimir las demás excepciones pero seguir, ahora, no se tiene que poder producir ningún otro error en try
                    # no sé bien cómo es.
                    _traceback.print_exception(*_sys.exc_info())

    # sclang methods

    @classmethod
    def clear(cls): # método de SystemClock en sclang, llama a schedClearUnsafe() mediante prClear/_SystemClock_Clear después de vaciar la cola prSchedulerQueue que es &g->process->sysSchedulerQueue
        if cls._instance is None: return
        while not cls._instance._task_queue.empty():
            cls._instance._task_queue.get() # de por sí PriorityQueue es thread safe, la implementación de SuperCollider es distinta
        cls._instance._sched_cond.notify() #_all()

    @classmethod
    def sched(cls, delta, item): # Process.elapsedTime es el tiempo físico (desde que se inició la aplicación), que también es elapsedTime de SystemClock (elapse_time acá) [Process.elapsedTime, SystemClock.seconds, thisThread.seconds] thisThread sería mainThread si se llama desde fuera de una rutina, thisThread.clock === SystemClock, es la clase singleton
        seconds = cls._instance.elapse_time()
        seconds += delta
        if seconds == _math.inf:
            msg = "won't schedule {} to infinity, clock time: {}, delta: {}"
            raise Exception(msg.format(item, seconds, delta))
        cls._instance.sched_add(seconds, item)

    @classmethod
    def sched_abs(cls, time, item):
        if time == _math.inf:
            msg = "sched_abs won't schedule {} to infinity"
            raise Exception(msg.format(item, time))
        cls._instance.sched_add(time, item)

    # L542 y L588 setea las prioridades 'rt' para mac o linux, es un parámetro de los objetos Thread
    # ver qué hace std::move(thread)
    # def sched_run(self): # L609, crea el thread de SystemClock
    #     # esto es simplemente start (sched_run_func es run) con prioridad rt
    #     # iría en el constructor/inicializador
    #     pass
    # L651, comentario importante sobre qué maneja cada reloj
    # luego ver también las funciones que exporta a sclang al final de todo


class TempoClock(Clock): # se crean desde SystemClock?
    pass


class AppClock(Clock): # ?
    pass


class NRTClock(Clock):
    # Los patterns temporales tienen que generar una rutina que
    # corra en el mismo reloj. El probleam es que el tiempo no
    # avanza si no se llama a yield/wait. El reloj de Jonathan
    # captura la cola y usa un servidor dummy, pero si el pattern
    # usa el reloj en 'tiempo real' eso no queda registrado.
    # Además, en nrt todas las acciones son sincrónicas.
    pass