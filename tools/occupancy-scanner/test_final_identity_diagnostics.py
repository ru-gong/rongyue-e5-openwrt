"""Final-stat diagnostics only: native Mac fixtures, no device or VM."""
import errno
import signal
import unittest

from test_native_occupancy_scanner import ScannerTests


class FinalIdentityTests(ScannerTests):
    def final_failure(self, fault, code, reason, detail, observed=None, state=None):
        process, result, rows = self.run_scan(fault=fault)
        self.assertEqual(process.returncode, 70)
        self.assertFalse(result['complete'])
        self.assertEqual(result['unknown'], ['scan-not-complete'])
        self.assertEqual(result['phase'], 'final-process-identities')
        self.assertEqual(result['subphase'], 'pid-final-stat')
        self.assertEqual((result['pid'], result['processes'], result['fds']), (100, 1, 2))
        self.assertEqual((result['errno'], result['reason'], result['detail']), (code, reason, detail))
        self.assertEqual(result['final_stat_expected_starttime'], 1000)
        self.assertEqual(result['final_stat_observed_starttime'], observed)
        self.assertEqual(result['final_stat_observed_state'], state)
        self.assertEqual(sum(row['event'] == 'RESULT' for row in rows), 1)
        self.assertNotIn('final-boot', [row['phase'] for row in rows])
        return result

    def alternate(self, *, pid=100, start=1000, state='S'):
        self.write('proc/100/stat.final-diagnostic', self.stat_text(pid, start=start, state=state))

    def test_enoent_remains_gone_not_reuse(self):
        r = self.final_failure('final-stat-enoent', errno.ENOENT, 'final-pid-gone-unconfirmed', 'stat-read')
        self.assertEqual(r['gone_observed'], 0)

    def test_esrch_remains_gone_not_reuse(self):
        r = self.final_failure('final-stat-esrch', errno.ESRCH, 'final-pid-gone-unconfirmed', 'stat-read')
        self.assertEqual(r['gone_observed'], 0)

    def test_actual_missing_alternate_file_preserves_enoent(self):
        self.final_failure('final-stat-record', errno.ENOENT, 'final-pid-gone-unconfirmed', 'stat-read')

    def test_eacces_is_read_error_not_gone(self):
        r = self.final_failure('final-stat-eacces', errno.EACCES, 'final-pid-stat-read-error-unknown', 'stat-read')
        self.assertEqual(r['gone_observed'], 0)

    def test_eio_is_read_error_not_gone(self):
        r = self.final_failure('final-stat-eio', errno.EIO, 'final-pid-stat-read-error-unknown', 'stat-read')
        self.assertEqual(r['gone_observed'], 0)

    def test_malformed_record_preserves_parse_errno(self):
        self.write('proc/100/stat.final-diagnostic', 'not a stat record\n')
        self.final_failure('final-stat-record', errno.EPROTO, 'final-pid-stat-parse-error-unknown', 'stat-format')

    def test_truncated_record_preserves_parse_detail(self):
        self.write('proc/100/stat.final-diagnostic', '100 (test) S\n')
        self.final_failure('final-stat-record', errno.EPROTO, 'final-pid-stat-parse-error-unknown', 'stat-required-fields')

    def test_wrong_pid_is_parse_identity_error_not_start_drift(self):
        self.alternate(pid=101)
        self.final_failure('final-stat-record', errno.ESTALE, 'final-pid-stat-parse-error-unknown', 'stat-pid')

    def test_reused_pid_reports_successfully_observed_start(self):
        self.alternate(start=9999)
        self.final_failure('final-stat-record', errno.ESTALE, 'final-pid-starttime-changed-unknown', 'stat-starttime-drift', 9999, 'S')

    def test_zombie_is_not_live_not_start_drift(self):
        self.alternate(state='Z')
        p, r, _ = self.run_scan(fault='final-stat-record')
        self.assertEqual(p.returncode, 0)
        self.assertEqual(r['retired_tasks'], 1)

    def test_dead_state_is_not_live_not_start_drift(self):
        self.alternate(state='X')
        p, r, _ = self.run_scan(fault='final-stat-record')
        self.assertEqual(p.returncode, 0)
        self.assertEqual(r['retired_tasks'], 1)

    def test_deadline_preserves_timeout_not_gone(self):
        r = self.final_failure('final-stat-expired', errno.ETIMEDOUT, 'final-pid-stat-deadline-unknown', 'stat-read')
        self.assertEqual(r['gone_observed'], 0)

    def test_cancel_preserves_cancel_not_gone(self):
        r = self.final_failure('final-stat-cancelled', errno.ECANCELED, 'final-pid-stat-cancelled-unknown', 'stat-read')
        self.assertEqual(r['cancel_signal'], signal.SIGTERM)
        self.assertEqual(r['gone_observed'], 0)

    def test_unchanged_stat_success_keeps_coverage_and_null_diagnostics(self):
        self.alternate()
        process, result, _ = self.run_scan(fault='final-stat-record')
        self.assertEqual(process.returncode, 0)
        self.assertTrue(result['complete'])
        self.assertEqual((result['processes'], result['fds'], result['fd_tables']), (1, 2, 1))
        self.assertIsNone(result['final_stat_expected_starttime'])
        self.assertIsNone(result['final_stat_observed_starttime'])
        self.assertIsNone(result['final_stat_observed_state'])

    def test_disabled_native_cannot_enter_fault_path(self):
        process, result, _ = self.run_scan(disabled=True, fault='final-stat-record')
        self.assertEqual(process.returncode, 70)
        self.assertEqual(result['reason'], 'production-device-execution-disabled')
        self.assertIsNone(result['final_stat_observed_starttime'])


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(FinalIdentityTests(name) for name in FinalIdentityTests.__dict__ if name.startswith('test_'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
