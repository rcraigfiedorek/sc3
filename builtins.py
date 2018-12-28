"""
builtins.py

Builtin functions from sclang.

Son los operadores unarios/(¿binarios?)/enarios de las
AbstractFunction y las UGen que también se aplican a otros
tipos de datos básico dentro de la librería de clases.

Son las funciones de _specialindex.py.

De no tener equivalentes estas funciones deberían implementarse
en CPython. En SuperCollider están implementadas a bajo nivel.

Ver:
/include/plugin_interface/SC_InlineUnaryOp.h
/include/plugin_interface/SC_InlineBinaryOp.h
"""

import math
#from functools import singledispatch

from . import functions as fn


# DONE: ver qué hacer con las listas de Python. RTA: EN PYTHON SE USA MAP Y
# LISTCOMPREHENSION, TRATAR DE HACERLA PYTÓNICA.

# DONE: ver qué hacer con los métodos mágicos de AbstractFucntion. RTA: EL PROBLEMA NO ES ABSTRACTFUNCTION
# SINO LOS TIPOS NUMÉRICOS INTEGRADOS, ABFUNC FUNCIONA CON LOS MÉTODOS INTEGRADOS NUMÉRICOS PERO LOS
# NÚMEROS NO VAN A FUNCIONAR CON MIDICPS, POR EJEMPLO. NO REIMPLEMENTAR LAS OPERACIONES PARA LOST TIPOS INTEGRADOS,
# NO REIMPLEMENTAR LOS MÉTODOS PARA LOS TIPOS INTEGRADOS (E.G. NEG).

# DONE: VER: https://docs.python.org/3/library/numbers.html#numbers.Integral
# implementa como if isinstance elif isinstance, tal vez @singledispatch
# genera una sobrecarga importante. Pero @singledispatch es relativamente
# nuevo, v3.4 o .5. En todo caso se puede cambiar después (o medir ahora...)

# TODO: ver módulo operator: https://docs.python.org/3/library/operator.html
# No estoy implementando los métodos inplace (e.g. a += b). Además el módulo
# provee funciones para las operaciones sobre tipos integrados, ver cuáles
# sí implementa y sin funcionan mediante los métodos mágicos.

# TODO: OTRA COSA, se puede asignar una función a una variable
# de instancia al declarar la clase. por ejemplo midicps = builtins.midicps.
# en ese caso tendría que pensar en los argumentos self y los nombres que
# se crean al usar singledispatch.

# Unary

_MSG = "bad operand type for {}: '{}'"

# TODO: es para denormals en ugens, pero el nombre está bueno.
# // this is a function for preventing pathological math operations in ugens.
# // can be used at the end of a block to fix any recirculating filter values.
# def zapgremlins(x):
#     float32 absx = std::abs(x);
#     // very small numbers fail the first test, eliminating denormalized numbers
#     //    (zero also fails the first test, but that is OK since it returns zero.)
#     // very large numbers fail the second test, eliminating infinities
#     // Not-a-Numbers fail both tests and are eliminated.
#     return (absx > (float32)1e-15 && absx < (float32)1e15) ? x : (float32)0.;

# TODO: No quiero sobreescribir o variar operaciones básicas de Python
# TODO: PERO TENGO QUE HACERLO PARA ALGUNAS FUNCIONES BÁSICAS.

# TODO: poner los try? si? no? sino?
def log(x, base=math.e):
    if isinstance(x, fn.AbstractFunction):
        return fn.ValueOpFunction(math.log, x, base)
    else:
        return math.log(x, base)

def log2(x):
    if isinstance(x, fn.AbstractFunction):
        return fn.ValueOpFunction(math.log2, x)
    else:
        return math.log2(x)

def log10(x):
    if isinstance(x, fn.AbstractFunction):
        return fn.ValueOpFunction(math.log10, x)
    else:
        return math.log10(x)

def log1p(x):
    if isinstance(x, fn.AbstractFunction):
        return fn.ValueOpFunction(math.log1p, x)
    else:
        return math.log1p(x)

_ONETWELFTH = 1/12
_ONE440TH = 1/440

def midicps(note):
    try: # TODO: VER: try evita dependencia cíclica, la otra es dejar que tiere el error de tipo que tira por defecto.
        # return (float64)440. * std::pow((float64)2., (note - (float64)69.) * (float64)0.08333333333333333333333333);
        return 440. * pow(2., (note - 69.) * _ONETWELFTH)
    except TypeError as e:
        raise TypeError(_MSG.format('midicps()', type(note).__name__)) from e

def cpsmidi(freq):
    try:
        # return sc_log2(freq * (float64)0.002272727272727272727272727) * (float64)12. + (float64)69.;
        return log2(freq * _ONE440TH) * 12. + 69.
    except TypeError as e:
        raise TypeError(_MSG.format('cpsmidi()', type(freq).__name__)) from e

def midiratio(midi):
    #return std::pow((float32)2. , midi * (float32)0.083333333333);
    #return pow(2., midi * _ONETWELFTH)
    pass

def ratiomidi(ratio):
    #return (float32)12. * sc_log2(ratio);
    #return 12. * math.log2(ratio)
    pass

def octcps(note):
    # return (float32)440. * std::pow((float32)2., note - (float32)4.75);
    pass

def cpsoct(freq):
    # return sc_log2(freq * (float32)0.0022727272727) + (float32)4.75;
    pass

def ampdb(amp):
    # return std::log10(amp) * (float32)20.;
    pass

def dbamp(db):
    # return std::pow((float32)10., db * (float32).05);
    pass

# TODO: VER qué onda...
# squared(float32 x) return x * x;
# cubed(float32 x) return return x * x * x;
# sqrt(float32 x) return x < (float32)0. ? -sqrt(-x) : sqrt(x);

def hanwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # return (float32)0.5 - (float32)0.5 * static_cast<float32>(cos(x * (float32)twopi));
    pass

def welwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # return static_cast<float32>(sin(x * pi));
    pass

def triwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # if (x < (float32)0.5) return (float32)2. * x;
    # else return (float32)-2. * x + (float32)2.;
    pass

def bitriwindow(x):
    # float32 ax = (float32)1. - std::abs(x);
    # if (ax <= (float32)0.) return (float32)0.;
    # return ax;
    pass

def rectwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # return (float32)1.;
    pass

def scurve(x):
    # if (x <= (float32)0.) return (float32)0.;
    # if (x >= (float32)1.) return (float32)1.;
    # return x * x * ((float32)3. - (float32)2. * x);
    pass

def scurve0(x):
    # // assumes that x is in range
    # return x * x * ((float32)3. - (float32)2. * x);
    pass

def ramp(x):
    # if (x <= (float32)0.) return (float32)0.;
    # if (x >= (float32)1.) return (float32)1.;
    # return x;
    pass

def sign(x):
    # return x < (float32)0. ? (float32)-1. : (x > (float32)0. ? (float32)1.f : (float32)0.f);
    pass

def distort(x):
    # return x / ((float32)1. + std::abs(x));
    pass

def distortneg(x):
    # if (x < (float32)0.)
    #     return x/((float32)1. - x);
    # else
    #     return x;
    pass

def softclip(x):
    # float32 absx = std::abs(x);
    # if (absx <= (float32)0.5) return x;
    # else return (absx - (float32)0.25) / x;
    pass

# // Taylor expansion out to x**9/9! factored  into multiply-adds
# // from Phil Burk.
def taylorsin(x):
    # // valid range from -pi/2 to +3pi/2
    # x = static_cast<float32>((float32)pi2 - std::abs(pi2 - x));
    # float32 x2 = x * x;
    # return static_cast<float32>(x*(x2*(x2*(x2*(x2*(1.0/362880.0)
    #         - (1.0/5040.0))
    #         + (1.0/120.0))
    #         - (1.0/6.0))
    #         + 1.0));
    pass

# TODO: VER arriba.
# trunc(x) return std::trunc(x);
# ceil(x) usa SSE4 opcionalmente
# floor(x) ídem.
# reciprocal(x) ídem, y es 1/x acá, y el nombre del método es largo, pero me ha resultado útil.
# bitNot return (float32) ~ (int)x;

def frac(x):
    # return x - sc_floor(x);
    pass

def sc_lg3interp(x1, a, b, c, d): # solo la define para float32
    # // cubic lagrange interpolator
    # float32 x0 = x1 + 1.f;
    # float32 x2 = x1 - 1.f;
    # float32 x3 = x1 - 2.f;
    #
    # float32 x03 = x0 * x3 * 0.5f;
    # float32 x12 = x1 * x2 * 0.16666666666666667f;
    #
    # return x12 * (d * x0 - a * x3) + x03 * (b * x2 - c * x1);
    pass

def calcfeedback(delaytime, decaytime):  # CalcFeedback, solo la define para float
    # if (delaytime == 0.f || decaytime == 0.f)
    #     return 0.f;
    #
    # float32 absret = static_cast<float32>( std::exp(log001 * delaytime / std::abs(decaytime)));
    # float32 ret = std::copysign(absret, decaytime);
    # return ret;
    pass

def wrap1(x):
    # if (x >= (float32) 1.) return x + (float32)-2.;
    # if (x <  (float32)-1.) return x + (float32) 2.;
    # return x;
    pass

def fold1(x):
    # if (x >= (float32) 1.) return (float32) 2. - x;
    # if (x <  (float32)-1.) return (float32)-2. - x;
    # return x;
    pass

def graycode(x): # grayCode, está abajo de todo y es para float32
    # return x ^ (x >> 1);
    pass

# TODO: En AbstractFunction
#linrand
#bilinrand
#sum3rand # hay otras comentadas alrededor.
#coin
#digitValue
#thru ??

# complex y cartesian
#rho
#theta
#rotate
#dist

# Binary
# TODO: ver el módulo operator: https://docs.python.org/3/library/operator.html
# VER NOTAS ARRIBA.
# ...
#lcm
#gcd
#...

# Nary
# ...