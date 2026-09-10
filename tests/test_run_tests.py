"""Discovery errors must remain failures in the parallel test runner."""
import unittest

if __package__:
    from . import run_tests
else:
    import run_tests


class ParallelDiscovery(unittest.TestCase):
    def test_failed_import_is_not_rescheduled_as_an_empty_class(self):
        error = ImportError('Deliberately broken discovery fixture')
        suite = unittest.TestSuite([
            unittest.loader._FailedTest('broken_test_module', error)])
        with self.assertRaisesRegex(RuntimeError, 'Test discovery failed') as caught:
            run_tests._class_groups(suite)
        self.assertIs(caught.exception.__cause__, error)
