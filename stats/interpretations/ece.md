## Expected Calibration Error (ECE)

**Definition:** The weighted average gap between the model's predicted confidence and its actual accuracy, computed over 10 equal-width probability bins.

**Formula:** ECE = sum over bins b of (n_b / N) * |accuracy(b) - confidence(b)|.

### Plain Language
ECE measures how honest the model is about how sure it is. When the model says "I'm 90% sure this is happy," ECE checks whether it's actually right about 90% of the time. An ECE of 0.036 means the model's confidence is off by only 3.6 percentage points on average---very trustworthy. An ECE of 0.142 means confidence is off by 14.2 points. This matters because Reachy uses the confidence number to decide how dramatically to gesture.

### Technical Detail
ECE uses 10 equal-width bins on [0, 1]. It is bounded [0, 1] with 0 indicating perfect calibration. Temperature scaling directly targets ECE minimization by adjusting the logit scale. The post-scaling ECE of 0.036 for V2 mixed+T represents a 75% reduction from 0.142, achieved by a single learned parameter T = 0.59. ECE is independent of classification accuracy---it measures only whether confidence magnitudes match empirical correctness rates. With n = 894 and 10 bins, some bins may have sparse counts, introducing variance.

**Gate A:** ECE <= 0.12 (both deploy and validation tiers).
