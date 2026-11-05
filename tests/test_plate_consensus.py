import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from plate_consensus import PlateConsensus


def plate(text='30A33918', box=(10, 10, 100, 40), confidence=0.99):
    return {'detection': {'bounding_box': dict(zip(('x1', 'y1', 'x2', 'y2'), box))},
            'ocr': {'text': text, 'confidence': confidence}}


class ConsensusTests(unittest.TestCase):
    def test_letters_after_five_digits_can_reach_consensus(self):
        tracker = PlateConsensus()
        for index in range(15):
            result = tracker.update([plate('80-441 NN-02')], index/30)[0]
        self.assertEqual(result['stable_text'], '80441NN02')
        self.assertEqual(result['votes'], 15)
        self.assertIsNone(result['pending_reason'])

    def test_non_domestic_letter_positions_are_not_rejected(self):
        tracker = PlateConsensus()
        for index in range(5):
            result = tracker.update([plate('5AU5341')], index/30)[0]
        self.assertEqual(result['stable_text'], '5AU5341')

    def test_pending_reasons_distinguish_confidence_format_and_vote_count(self):
        for text, confidence, reason in [('80441NN02', .4, 'low_confidence'),
                                          ('junk', .99, 'unsupported_layout'),
                                          ('', .99, 'empty_ocr'),
                                          ('80441NN02', .99, 'not_enough_matches')]:
            result = PlateConsensus().update([plate(text, confidence=confidence)], 0)[0]
            self.assertEqual(result['pending_reason'], reason)
            self.assertIsNone(result['stable_text'])

    def test_jitter_does_not_override_supported_text(self):
        tracker = PlateConsensus()
        sequence = ['30A33918'] * 5 + ['30A33913', '30A33918', '30A33918']
        for index, text in enumerate(sequence):
            result = tracker.update([plate(text)], index / 30)[0]
            if index < 4:
                self.assertIsNone(result['stable_text'])
            else:
                self.assertEqual(result['stable_text'], '30A33918')
        self.assertEqual(result['raw_text'], sequence[-1])

    def test_two_plates_remain_separate_when_detection_order_changes(self):
        tracker = PlateConsensus()
        left = plate('30A33918')
        right = plate('59U116124', (300, 10, 390, 40))
        for index in range(8):
            rows = tracker.update([left, right] if index % 2 == 0 else [right, left], index / 30)
        self.assertEqual({r['raw_text']: r['stable_text'] for r in rows},
                         {'30A33918': '30A33918', '59U116124': '59U116124'})
        self.assertEqual(len({r['track_id'] for r in rows}), 2)

    def test_absence_expires_votes_even_at_same_location(self):
        tracker = PlateConsensus()
        for index in range(5):
            old = tracker.update([plate()], index / 30)[0]
        tracker.update([], 1)
        new = tracker.update([plate('30F21717')], 1.1)[0]
        self.assertNotEqual(new['track_id'], old['track_id'])
        self.assertIsNone(new['stable_text'])

    def test_unreadable_or_low_confidence_does_not_confirm(self):
        tracker = PlateConsensus()
        samples = [plate(confidence=[0.99, 0.2]), plate('junk'), plate('30A33918', confidence=math.nan)]
        for index in range(12):
            result = tracker.update([samples[index % 3]], index / 30)[0]
            self.assertIsNone(result['stable_text'])

    def test_old_votes_age_out_instead_of_latching_forever(self):
        tracker = PlateConsensus()
        for index in range(5):
            result = tracker.update([plate()], index / 30)[0]
        self.assertEqual(result['stable_text'], '30A33918')
        for index in range(5, 22):
            result = tracker.update([plate('unreadable')], index / 30)[0]
        self.assertIsNone(result['stable_text'])
        self.assertEqual(tracker.summaries()[0]['last_consensus'], '30A33918')

    def test_ambiguous_overlap_cannot_inherit_confirmed_votes(self):
        tracker = PlateConsensus()
        for index in range(5):
            old = tracker.update([plate()], index / 30)[0]
        rows = tracker.update([plate(box=(11, 10, 101, 40)), plate(box=(9, 10, 99, 40))], 0.2)
        self.assertTrue(all(row['track_id'] != old['track_id'] for row in rows))
        self.assertTrue(all(row['stable_text'] is None for row in rows))

    def test_time_reversal_or_nonfinite_is_rejected(self):
        tracker = PlateConsensus()
        tracker.update([], 1)
        for invalid in (0, math.inf, math.nan):
            with self.assertRaises(ValueError):
                tracker.update([], invalid)


if __name__ == '__main__':
    unittest.main()
