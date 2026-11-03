import json
import os
import tempfile
import unittest

import scheduler_advisor


class SchedulerAdvisorTests(unittest.TestCase):
    def test_reads_cumulative_monitor_ticks_as_deltas(self):
        with tempfile.NamedTemporaryFile(mode="w", newline="", delete=False) as monitor_file:
            monitor_file.write(
                "time,pid,tickets,ticks\n"
                "100,11,20,10\n"
                "100,12,10,10\n"
                "200,11,20,80\n"
                "200,12,10,40\n"
            )
            path = monitor_file.name
        try:
            summary = scheduler_advisor.read_monitor_csv(path, [11, 12])
        finally:
            os.unlink(path)

        self.assertEqual(summary[0]["delta_ticks"], 70)
        self.assertEqual(summary[0]["observed_share_percent"], 70.0)
        self.assertEqual(summary[1]["delta_ticks"], 30)
        self.assertEqual(summary[1]["observed_share_percent"], 30.0)

    def test_rejects_changes_to_non_target_pid(self):
        response = json.dumps({
            "pid": 12,
            "new_tickets": 30,
            "reason": "Increase the target's share.",
        })
        with self.assertRaisesRegex(ValueError, "target PID"):
            scheduler_advisor.validate_recommendation(response, 11)

    def test_accepts_a_bounded_target_recommendation(self):
        response = json.dumps({
            "pid": 11,
            "new_tickets": 30,
            "reason": "The target is below its requested CPU share.",
        })
        self.assertEqual(
            scheduler_advisor.validate_recommendation(response, 11),
            {
                "pid": 11,
                "new_tickets": 30,
                "reason": "The target is below its requested CPU share.",
            },
        )

    def test_rejects_tickets_outside_existing_kernel_bounds(self):
        response = json.dumps({
            "pid": 11,
            "new_tickets": 250,
            "reason": "Increase the target's share.",
        })
        with self.assertRaisesRegex(ValueError, "10..200"):
            scheduler_advisor.validate_recommendation(response, 11)


if __name__ == "__main__":
    unittest.main()
