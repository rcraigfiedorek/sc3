"""
Builtin UGen classes submodule.
"""

import importlib as _importlib
import inspect as _inspect
import pathlib as _pathlib
# import sys as _sys


installed_ugens = dict()

_package_qual_name = 'sc3.synth.ugens'
_module = _importlib.import_module(_package_qual_name)
_mapping = _inspect.getmembers(_module, _inspect.isclass)  # NOTE: abajo
installed_ugens.update(dict(_mapping))

_package_path = _pathlib.Path(__file__).parent
_sub_modules_list = _package_path.glob('**/[!_]*.py')

for _sub_module_filename in _sub_modules_list:
    _full_name = _package_qual_name + '.' + _sub_module_filename.stem
    print('@@@ full_name:', _full_name)
    _module = _importlib.import_module(_full_name)
    _mapping = _inspect.getmembers(_module, _inspect.isclass)  # *** NOTE: y también tiene que ser UGen... # es un array de tuplas # el formato se convierte en diccionario con dict(_mapping)
    installed_ugens.update(dict(_mapping))
    # _sys.modules[__name__].__dict__.update(dict(_mapping))  # *** NOTE: leer todo https://docs.python.org/3/reference/import.html