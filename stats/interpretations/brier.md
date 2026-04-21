## Brier Score

**Definition:** The mean squared error between predicted probability vectors and one-hot true labels.

**Formula:** Brier = (1/N) * sum over all samples and classes of (predicted_prob - true_label)^2.

### Plain Language
The Brier score measures both whether the model gets the right answer AND whether its confidence levels are accurate. It ranges from 0 (perfect) to 2 (worst for 3 classes). A Brier score of 0.128 is good---the model's probability estimates are close to reality. A score of 0.340 is concerning---the model is frequently confident about wrong answers or uncertain about correct ones.

### Technical Detail
The Brier score is a strictly proper scoring rule, uniquely minimized when predicted probabilities equal true conditional probabilities. It decomposes into reliability (calibration), resolution (discrimination), and uncertainty. Unlike ECE which measures only calibration, Brier captures both calibration and classification quality. V1 mixed+T passes ECE (0.021) but fails Brier (0.244) because its classification accuracy is insufficient---squared errors on misclassified samples dominate. Only V2 mixed+T's combination of high classification accuracy (F1 = 0.916) and good calibration (ECE = 0.036) yields Brier below 0.16.

**Gate A:** Brier <= 0.16 (deploy only; not gated at validation tier).
