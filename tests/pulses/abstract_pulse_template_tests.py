import unittest
from unittest import mock

from qupulse.expressions import ExpressionScalar
from qupulse.pulses.abstract_pulse_template import AbstractPulseTemplate, NotSpecifiedError

from tests.pulses.sequencing_dummies import DummyPulseTemplate


class AbstractPulseTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freezable_property_values = {
            'defined_channels': {'A', 'B'},
            'duration': ExpressionScalar(4),
            'measurement_names': {'m', 'n'},
            'integral': {'A': ExpressionScalar('a*b'), 'B': ExpressionScalar(32)},
            'parameter_names': {'a', 'b', 'c'}
        }

    def test_minimal_init(self):
        apt = AbstractPulseTemplate(identifier='my_apt')

        self.assertEqual(apt._frozen_properties, set())
        self.assertEqual(apt._declared_properties, {})
        self.assertEqual(apt.identifier, 'my_apt')

    def test_declaring(self):
        apt = AbstractPulseTemplate(identifier='my_apt', defined_channels={'A'})

        self.assertEqual(apt._frozen_properties, set())
        self.assertEqual(apt._declared_properties, {'defined_channels': {'A'}})
        self.assertEqual(apt.identifier, 'my_apt')

    def test_freezing(self):
        apt = AbstractPulseTemplate(identifier='my_apt', defined_channels={'A'})

        # freeze
        self.assertEqual(apt.defined_channels, {'A'})

        self.assertEqual(apt._frozen_properties, {'defined_channels'})
        self.assertEqual(apt._declared_properties, {'defined_channels': {'A'}})

        apt = AbstractPulseTemplate(identifier='my_apt', **self.freezable_property_values)
        expected_frozen = set()

        for property_name, valid_value in self.freezable_property_values.items():
            self.assertEqual(apt._frozen_properties, expected_frozen)

            self.assertEqual(getattr(apt, property_name), valid_value)
            expected_frozen.add(property_name)

            self.assertEqual(apt._frozen_properties, expected_frozen)

    def test_unspecified(self):
        specified = {}
        unspecified = self.freezable_property_values.copy()

        for property_name, valid_value in self.freezable_property_values.items():
            specified[property_name] = unspecified.pop(property_name)

            apt = AbstractPulseTemplate(identifier='my_apt', **specified)

            for x, v in specified.items():
                self.assertEqual(v, getattr(apt, x))

            for unspecified_property_name in unspecified:
                with self.assertRaisesRegex(NotSpecifiedError, unspecified_property_name,
                                            msg=unspecified_property_name):
                    getattr(apt, unspecified_property_name)

    def test_linking(self):
        apt = AbstractPulseTemplate(identifier='apt')

        linked = DummyPulseTemplate()

        self.assertIsNone(apt._linked_target)

        apt.link_to(linked)

        self.assertIs(linked, apt._linked_target)

    def test_linking_wrong_frozen(self):
        apt = AbstractPulseTemplate(identifier='my_apt', defined_channels={'A'})

        dummy = DummyPulseTemplate(defined_channels={'B'})
        apt.link_to(dummy)

        self.assertEqual(apt.defined_channels, dummy.defined_channels)

        apt = AbstractPulseTemplate(identifier='my_apt', defined_channels={'A'})

        # freeze
        apt.defined_channels

        dummy = DummyPulseTemplate(defined_channels={'B'})

        with self.assertRaisesRegex(RuntimeError, 'Wrong value of property "defined_channels"'):
            apt.link_to(dummy)

    def test_method_forwarding(self):
        apt = AbstractPulseTemplate(identifier='my_apt')

        args = ([], {}, 'asd')
        kwargs = {'kw1': [], 'kw2': {}}

        forwarded_methods = ['build_sequence', '_create_program', 'is_interruptable', 'requires_stop']

        for method_name in forwarded_methods:
            method = getattr(apt, method_name)
            with self.assertRaisesRegex(RuntimeError, 'No linked target'):
                method(*args, **kwargs)

        linked = mock.MagicMock()
        apt.link_to(linked)

        for method_name in forwarded_methods:
            method = getattr(apt, method_name)
            mock_method = getattr(linked, method_name)

            method(*args, **kwargs)

            mock_method.assert_called_once_with(*args, **kwargs)

    def test_forwarded_get_attr(self):
        apt = AbstractPulseTemplate(identifier='my_apt')

        self.assertFalse(hasattr(apt, 'test'))

        linked = mock.MagicMock()

        apt.link_to(linked)

        self.assertTrue(hasattr(apt, 'test'))
        self.assertIs(apt.test, linked.test)
