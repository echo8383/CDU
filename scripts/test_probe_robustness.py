"""Small implementation tests only; not substitutes for the 350-series controls."""
import unittest
import numpy as np
from threadpoolctl import threadpool_limits
from run_probe_robustness import sample_indices, weights, make_model, load_score
from evaluate_cdu_protocol_v1 import average_rank01, log_loss_bits


class ProbeTests(unittest.TestCase):
    def test_sampling_order_independent_and_label_free(self):
        a = sample_indices("series-a", 9000, 2048, "test")
        sample_indices("series-b", 8000, 2048, "test")
        np.testing.assert_array_equal(a, sample_indices("series-a", 9000, 2048, "test"))
        self.assertEqual(len(np.unique(a)), 2048)
        np.testing.assert_array_equal(sample_indices("a", 5, 0, "x"), np.arange(5))

    def test_source_series_weights(self):
        rows = [{"source": "A", "start": 0, "end": 2},
                {"source": "A", "start": 2, "end": 8},
                {"source": "B", "start": 8, "end": 12}]
        w = weights(rows)
        self.assertAlmostEqual(w.sum(), 12)
        self.assertAlmostEqual(w[:8].sum(), 6)
        self.assertAlmostEqual(w[8:].sum(), 6)
        self.assertAlmostEqual(w[:2].sum(), w[2:8].sum())

    def test_controls_and_ties(self):
        b = np.arange(310, dtype=np.float32).reshape(10, 31)
        y = np.arange(10) % 2
        np.testing.assert_array_equal(load_score("test", "duplicate", b, y), b[:, 4])
        np.testing.assert_array_equal(load_score("test", "noise", b, y),
                                      load_score("test", "noise", b, 1-y))
        np.testing.assert_array_equal(average_rank01(np.ones(10)), np.full(10, .5))

    def test_probe_finite_predictions_and_signal(self):
        rng = np.random.default_rng(123)
        x = rng.normal(size=(1600, 3))
        y = rng.integers(0, 2, 1600)
        signal = y + rng.normal(0, .05, 1600)
        config = {"hgb": {"max_iter": 12, "max_leaf_nodes": 7, "min_samples_leaf": 20,
                          "early_stopping": False, "random_state": 2024}}
        with threadpool_limits(limits=1):
            for kind in ["hgb", "logistic"]:
                m0 = make_model(kind, config).fit(x[:1000], y[:1000], sample_weight=np.ones(1000))
                m1 = make_model(kind, config).fit(np.column_stack([x[:1000], signal[:1000]]),
                                                y[:1000], sample_weight=np.ones(1000))
                p0 = m0.predict_proba(x[1000:])[:, 1]
                p1 = m1.predict_proba(np.column_stack([x[1000:], signal[1000:]]))[:, 1]
                self.assertTrue(np.isfinite(p1).all())
                self.assertGreater(log_loss_bits(y[1000:], p0)-log_loss_bits(y[1000:], p1), .1)


if __name__ == "__main__":
    unittest.main()
