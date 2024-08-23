import unittest

import sc3

sc3.init()

from sc3.synth.ugens.oscillators import Impulse
from sc3.synth.ugens.infougens import BufSampleRate
from sc3.synth.ugens.poll import Poll


class UGenTestCase(unittest.TestCase):
    def test_internal_interface(self):
        # _method_selector_for_rate
        self.assertEqual(Impulse._method_selector_for_rate("audio"), "ar")
        self.assertEqual(Impulse._method_selector_for_rate("control"), "kr")
        self.assertEqual(Poll._method_selector_for_rate(None), "new")
        self.assertEqual(BufSampleRate._method_selector_for_rate("scalar"), "ir")
        self.assertRaises(AttributeError, Impulse._method_selector_for_rate, "scalar")
        self.assertRaises(
            AttributeError, BufSampleRate._method_selector_for_rate, "audio"
        )

        # _arg_name_for_input_at
        ugen = Impulse.ar()
        for i, name in enumerate(["freq", "phase", None]):
            self.assertEqual(ugen._arg_name_for_input_at(i), name)


if __name__ == "__main__":
    unittest.main()
