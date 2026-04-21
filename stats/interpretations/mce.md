## Maximum Calibration Error (MCE)

**Definition:** The largest calibration gap across all probability bins.

**Formula:** MCE = max over all bins b of |accuracy(b) - confidence(b)|.

### Plain Language
While ECE gives the average calibration gap, MCE reports the worst single gap. Even if most confidence levels are accurate, MCE catches the one range where the model is most dishonest. For example, the model might be well-calibrated for high-confidence predictions but badly wrong for medium-confidence ones. MCE flags this worst case.

### Technical Detail
MCE identifies the worst-case calibration failure across the binned confidence spectrum. It is more conservative than ECE and sensitive to outlier bins. MCE is useful for detecting localized miscalibration---a model might have low ECE but a single bin with a 25% gap. In safety-critical applications, MCE provides a minimax calibration guarantee. In our system, MCE is displayed for diagnostics but is not independently gated. The ECE threshold (<=0.12) serves as the gated calibration metric because it better reflects overall calibration quality relevant to the gesture modulation system.

**Gate A:** Not gated (diagnostic only).
