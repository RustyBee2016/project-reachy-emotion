# Statistical Interpretations Guide

## Reachy Emotion Classification System — Dashboard & Compare Page Metrics

**Author:** Russell Bray  
**Date:** May 2026  
**Project:** Reachy Emotion Classification System — Master of Science Capstone, Loyola University Chicago

---

## Table of Contents

1. [Dashboard Page Metrics](#1-dashboard-page-metrics)
   - 1.1 Accuracy
   - 1.2 Precision (Macro)
   - 1.3 Recall (Macro)
   - 1.4 F1 Score (Macro)
   - 1.5 Balanced Accuracy
   - 1.6 Confusion Matrix
2. [Compare Page Metrics](#2-compare-page-metrics)
   - 2.1 Per-Class F1 (F1 Happy, F1 Sad, F1 Neutral)
   - 2.2 Composite Score
   - 2.3 Delta (V1 − V2) and Winner Indicator
   - 2.4 Recommendation Engine
3. [Calibration Metrics (Both Pages)](#3-calibration-metrics-both-pages)
   - 3.1 Expected Calibration Error (ECE)
   - 3.2 Brier Score
   - 3.3 Maximum Calibration Error (MCE)
4. [Gate A Quality Gate Statistics](#4-gate-a-quality-gate-statistics)
   - 4.1 Gate A-val (Synthetic Validation Tier)
   - 4.2 Gate A-deploy (Real-World Deployment Tier)
   - 4.3 Individual Gate Thresholds
   - 4.4 Gate Compliance Summary
5. [Coefficient of Variation (CV)](#5-coefficient-of-variation-cv)
6. [Cohen's Kappa (κ)](#6-cohens-kappa-κ)
7. [Wilson Score Confidence Intervals](#7-wilson-score-confidence-intervals)
8. [Summary Table: All Metrics at a Glance](#8-summary-table-all-metrics-at-a-glance)

---

## 1. Dashboard Page Metrics

The Dashboard page (`06_Dashboard.py`) displays per-run results for training, validation, and test evaluations. It shows five classification metrics across the top row, three calibration metrics below, a confusion matrix visualization, Gate A pass/fail indicators, and a statistical interpretation panel.

---

### 1.1 Accuracy

**Definition:** The proportion of all predictions that are correct.

$$\text{Accuracy} = \frac{\text{Number of correct predictions}}{\text{Total number of predictions}}$$

**High School Interpretation:**  
Accuracy is like a test score. If you took a 100-question test and got 82 right, your accuracy is 82%. It tells you "out of everything the model looked at, what percentage did it get right?" In our project, accuracy of 0.817 means the model correctly identified the emotion in about 82 out of every 100 photos. The limitation is that if most of the photos show happy faces, the model could get a high score just by always guessing "happy" — even if it never correctly identifies sadness. That is why we do not rely on accuracy alone.

**Graduate Interpretation:**  
Accuracy is the simplest point estimate of classifier performance: $\hat{p} = \frac{TP + TN}{N}$ generalized to the multi-class setting as $\frac{\sum_i C_{ii}}{\sum_{i,j} C_{ij}}$ where $C$ is the confusion matrix. In imbalanced settings — our test set is 48.7% happy, 17.9% sad, 33.4% neutral — accuracy is biased toward the majority class. A classifier that predicts "happy" for every input achieves 48.7% accuracy without learning anything about sadness or neutrality. Accuracy is reported on the Dashboard for completeness but is not used in any Gate A threshold. It is superseded by F1 Macro and Balanced Accuracy, which explicitly correct for class imbalance.

---

### 1.2 Precision (Macro)

**Definition:** Of all the times the model predicted a particular emotion, how often was it actually correct — averaged equally across all three classes.

$$\text{Precision}_k = \frac{TP_k}{TP_k + FP_k}, \quad \text{Precision}_{\text{macro}} = \frac{1}{K}\sum_{k=1}^{K}\text{Precision}_k$$

**High School Interpretation:**  
Imagine the model says "this person is sad" 200 times. Precision tells you how many of those 200 times the person was actually sad. If precision for sadness is 0.88, that means 88 out of 100 times the model said "sad," the person really was sad. The remaining 12 were false alarms — people who were neutral or happy but got mislabeled as sad. Macro precision averages this across all three emotions equally, so no single emotion dominates the score.

**Graduate Interpretation:**  
Macro precision is the unweighted mean of per-class positive predictive values. It is sensitive to false positives: a model with low sad precision generates many false sadness alerts. In the Reachy context, low sad precision means the robot frequently offers comfort to people who are not actually sad — the neutral→sad confusion pattern that disqualified V2 synthetic (sad precision = 56.5%). The macro averaging scheme gives equal weight to each class regardless of prevalence, preventing the majority class from masking minority-class deficiencies. This metric is displayed on the Dashboard but is not independently gated; it is captured implicitly through per-class F1 and F1 Macro thresholds.

---

### 1.3 Recall (Macro)

**Definition:** Of all the photos that actually showed a particular emotion, how many did the model correctly identify — averaged equally across all three classes.

$$\text{Recall}_k = \frac{TP_k}{TP_k + FN_k}, \quad \text{Recall}_{\text{macro}} = \frac{1}{K}\sum_{k=1}^{K}\text{Recall}_k$$

**High School Interpretation:**  
Recall asks: "When someone really was sad, did the model catch it?" If recall for sadness is 0.89, the model correctly detected 89 out of 100 actually-sad faces. The other 11 were missed — the model thought they were neutral or happy. Macro recall averages this detection rate across happy, sad, and neutral equally.

**Graduate Interpretation:**  
Macro recall (sensitivity) is the unweighted mean of per-class true positive rates. It measures completeness of detection: the probability that a genuinely sad individual is correctly classified. In our test data, recall is equivalent to balanced accuracy when all classes are equally weighted. Low recall on a particular class means the model systematically misses that emotion. For instance, V2 synthetic's neutral recall was only 0.602 — the model missed 40% of neutral faces, predominantly classifying them as sad (105/299 = 35.1%). Recall is displayed on the Dashboard and is a component of F1, but is not independently gated.

---

### 1.4 F1 Score (Macro)

**Definition:** The harmonic mean of precision and recall, averaged equally across all classes. The single most important classification metric on the Dashboard.

$$F1_k = \frac{2 \cdot \text{Precision}_k \cdot \text{Recall}_k}{\text{Precision}_k + \text{Recall}_k}, \quad F1_{\text{macro}} = \frac{1}{K}\sum_{k=1}^{K}F1_k$$

**High School Interpretation:**  
F1 combines two questions into one score: "When the model says an emotion, is it right?" (precision) and "When the emotion is there, does the model find it?" (recall). If either one is low, the F1 score gets dragged down. A score of 0.916 means the model is both accurate in its claims and thorough in its detection across all three emotions. The "macro" part means each emotion counts equally — happy doesn't get more influence just because there are more happy photos.

**Graduate Interpretation:**  
F1 Macro is the primary classification metric in the Reachy system and carries the largest weight (50%) in the composite deployment score. As the harmonic mean of precision and recall, it penalizes extreme imbalance between the two: a model cannot achieve high F1 by sacrificing one for the other. The macro averaging scheme treats each class as equally important regardless of support, which is critical given our imbalanced test distribution. F1 Macro is gated at ≥ 0.75 for deployment. However, F1 Macro can still mask class-level failures — V1 synthetic (0.781) and V2 synthetic (0.780) had nearly identical F1 Macro despite radically different per-class profiles. This is why per-class F1 gates were added as a separate threshold.

**Gate A Threshold:** F1 Macro ≥ 0.75 (deploy), ≥ 0.84 (validation)

---

### 1.5 Balanced Accuracy

**Definition:** The average of per-class recall values. Equivalent to accuracy computed as if all classes had equal representation.

$$\text{Balanced Accuracy} = \frac{1}{K}\sum_{k=1}^{K}\text{Recall}_k$$

**High School Interpretation:**  
Regular accuracy can be misleading when some emotions appear much more often than others in the test data. Balanced accuracy fixes this by treating each emotion as equally important. If the model has 93% recall on happy faces but only 60% on neutral faces, balanced accuracy averages these rather than letting the many happy photos dominate the score. A balanced accuracy of 0.921 means the model detects about 92% of each emotion on average.

**Graduate Interpretation:**  
Balanced accuracy is the arithmetic mean of per-class sensitivities (recall values), equivalent to the expected accuracy under a uniform class prior. It corrects for prevalence bias: in our test set, happy comprises 48.7% of samples, so a naive classifier achieving 48.7% accuracy could appear reasonable. Balanced accuracy would correctly score such a classifier at ~33.3% (chance level for 3 classes). It is gated at ≥ 0.75 for deployment and carries 20% weight in the composite score. Balanced accuracy is mathematically equivalent to macro recall and numerically identical in our evaluation pipeline.

**Gate A Threshold:** Balanced Accuracy ≥ 0.75 (deploy), ≥ 0.85 (validation)

---

### 1.6 Confusion Matrix

**Definition:** A table showing exactly how many images of each true emotion class were predicted as each class.

**Format on Dashboard:**  
Rows represent the true emotion; columns represent the model's prediction. The diagonal shows correct classifications; off-diagonal cells show specific error types.

```
              Predicted
              Happy   Sad   Neutral
True Happy  [  404,    2,     29  ]    ← V2 mixed+T
True Sad    [    1,  143,     16  ]
True Neutral[    1,   17,    281  ]
```

**High School Interpretation:**  
The confusion matrix is a detailed "report card" that shows exactly where the model gets confused. Each row is a group of photos with the same real emotion. Reading across a row tells you what the model said about those photos. For example, in the V2 mixed+T results: out of 299 truly neutral photos, the model correctly said "neutral" for 281, incorrectly said "happy" for 1, and incorrectly said "sad" for 17. The numbers on the diagonal (top-left to bottom-right: 404, 143, 281) are the successes. Everything else is an error. Larger diagonal numbers = better model.

**Graduate Interpretation:**  
The confusion matrix $C \in \mathbb{Z}^{K \times K}$ is the fundamental data structure from which all classification metrics are derived. Element $C_{ij}$ is the count of samples with true label $i$ predicted as label $j$. Row normalization yields per-class recall; column normalization yields per-class precision. The off-diagonal structure reveals error patterns with behavioral consequences: the (neutral, sad) cell was the critical discriminator between V1 and V2. The Dashboard renders the confusion matrix as either a raw-number table or a color-coded heatmap using scikit-learn's `ConfusionMatrixDisplay`. The Compare page shows side-by-side confusion matrices for V1 and V2 to enable direct visual comparison of error patterns.

---

## 2. Compare Page Metrics

The Compare page (`08_Compare.py`) displays all Dashboard metrics for both Variant 1 and Variant 2, plus additional comparison-specific statistics.

---

### 2.1 Per-Class F1 (F1 Happy, F1 Sad, F1 Neutral)

**Definition:** The F1 score computed separately for each emotion class.

**High School Interpretation:**  
Instead of one overall F1 score, per-class F1 gives you three separate scores — one for happy, one for sad, one for neutral. This matters because a model might be excellent at recognizing happiness but terrible at recognizing sadness. In our project, V2 synthetic had F1 Happy = 0.946 (excellent) but F1 Sad = 0.694 (below the passing threshold). Per-class F1 is what caught this hidden weakness.

**Graduate Interpretation:**  
Per-class F1 scores decompose the macro aggregate into its constituent components, revealing class-level disparities that F1 Macro conceals by averaging. The coefficient of variation (CV) of per-class F1 scores quantifies classification equity: V2 synthetic had CV = 15.1% (severe inequity) versus V1 synthetic's 4.2%. The per-class F1 gate (≥ 0.70 for each class) was specifically designed to prevent deployment of models that achieve acceptable macro metrics by excelling on the majority class (happy, 48.7%) while neglecting minorities (sad, 17.9%). This gate was the mechanism that correctly rejected V2 synthetic despite its higher composite score, kappa, and accuracy.

**Gate A Threshold:** Per-Class F1 ≥ 0.70 each (deploy), ≥ 0.80 each (validation)

---

### 2.2 Composite Score

**Definition:** A weighted combination of classification and calibration metrics used to rank model runs.

$$S = 0.50 \times F1_{\text{macro}} + 0.20 \times \text{bAcc} + 0.15 \times \overline{F1}_{\text{per-class}} + 0.15 \times (1 - \text{ECE})$$

**High School Interpretation:**  
The composite score is like a weighted GPA where different subjects count for different amounts. F1 Macro (overall classification quality) counts the most — 50%. Balanced accuracy adds 20%. The average of the three per-class F1 scores adds 15%. And calibration quality (1 − ECE) adds the final 15%. A higher composite score is better. V2 mixed+T scored 0.924, which was the highest of any model — confirming it as the best overall choice.

**Graduate Interpretation:**  
The composite score is a scalar aggregation function that reduces the multi-dimensional metric space to a single total ordering for automated run selection. The weight vector (0.50, 0.20, 0.15, 0.15) reflects the project's priority hierarchy: classification accuracy is primary (70% combined weight for F1-based metrics), calibration quality is secondary (15%). The calibration component uses (1 − ECE) to convert the lower-is-better ECE into a higher-is-better quantity compatible with the other terms. The composite score is used by `_load_best_test_result()` to automatically select the highest-performing run per variant. It is distinct from Gate A compliance: a model can have a high composite score but still fail deployment gates (as V2 synthetic demonstrated with score 0.805 but 4/7 gates failed). Gate compliance takes priority over composite score in the recommendation engine.

---

### 2.3 Delta (V1 − V2) and Winner Indicator

**Definition:** The arithmetic difference between Variant 1 and Variant 2 on each metric, with a "Winner" column indicating which variant is superior.

**High School Interpretation:**  
Delta is simply "V1's score minus V2's score." A positive delta means V1 is better; a negative delta means V2 is better. For metrics where lower is better (ECE, Brier, MCE), the winner logic is flipped — the lower score wins. The Winner column shows "V1" or "V2" in bold. This makes it easy to scan the table and see at a glance which model is better at what.

**Graduate Interpretation:**  
The signed delta provides a first-order comparison but does not account for statistical significance. A delta of +0.001 on F1 Macro (V1 synthetic vs. V2 synthetic) is within sampling noise for $n = 894$, whereas a delta of −0.082 (V1 mixed+T vs. V2 mixed+T) represents a substantive effect. The Compare page does not currently display confidence intervals on the deltas; significance testing is provided in the research paper via Wilson score intervals and z-tests. The winner indicator correctly handles the directionality of each metric (higher-better for classification, lower-better for calibration).

---

### 2.4 Recommendation Engine

**Definition:** An automated system that determines which variant to recommend for deployment.

**Logic:**

1. If exactly one variant passes Gate A-deploy → recommend it (HIGH confidence)
2. If both pass or both fail → compare composite scores; confidence is HIGH (Δ > 0.02), MODERATE (0.005 < Δ ≤ 0.02), or LOW (Δ ≤ 0.005)

**High School Interpretation:**  
The recommendation engine is like a hiring committee with strict minimum requirements. First, it checks: does each model meet all the minimum passing grades (Gate A)? If only one model passes, it wins automatically. If both pass, or neither does, the committee compares their overall "GPA" (composite score) and recommends the one with the higher score. The confidence level tells you how close the competition was — HIGH means the winner was clearly better, LOW means it was essentially a tie.

**Graduate Interpretation:**  
The recommendation engine implements a lexicographic decision rule: gate compliance is the primary criterion (binary filter), composite score is the secondary criterion (continuous ranking). This prioritization ensures that no model bypasses safety and quality thresholds regardless of aggregate performance. The confidence calibration (HIGH/MODERATE/LOW) based on score differential serves as an informal effect-size indicator. The current thresholds (0.005, 0.02) are heuristic; a more rigorous approach would use bootstrap confidence intervals on the composite score difference. In the final evaluation, V2 mixed+T is the only 7/7 gate-compliant model, making the recommendation unambiguous (HIGH confidence, score 0.924 vs. next-best 0.857).

---

## 3. Calibration Metrics (Both Pages)

Calibration metrics assess whether the model's stated confidence matches its actual correctness rate. Both Dashboard and Compare pages display these.

---

### 3.1 Expected Calibration Error (ECE)

**Definition:** The weighted average gap between the model's predicted confidence and its actual accuracy, computed over equal-width probability bins.

$$\text{ECE} = \sum_{b=1}^{B} \frac{n_b}{N} \left| \text{acc}(b) - \text{conf}(b) \right|$$

where $B = 10$ bins, $n_b$ is the number of samples in bin $b$, $\text{acc}(b)$ is the fraction of correct predictions in that bin, and $\text{conf}(b)$ is the mean predicted confidence in that bin.

**High School Interpretation:**  
ECE measures how honest the model is about how sure it is. When the model says "I'm 90% sure this is happy," ECE checks whether it's actually right about 90% of the time in such cases. If the model says 90% but is only right 70% of the time, the gap (20%) contributes to a high ECE. An ECE of 0.036 means the model's confidence is off by only 3.6 percentage points on average — very trustworthy. An ECE of 0.142 means confidence is off by 14.2 points — the model is overconfident or underconfident in a meaningful way. This matters because Reachy uses the confidence number to decide how dramatically to gesture. If the model says "92% happy" but is wrong, the robot does an enthusiastic celebration for no reason.

**Graduate Interpretation:**  
ECE (Naeini et al., 2015) is the standard post-hoc calibration metric using equal-width binning ($B = 10$). It decomposes into reliability (calibration error) and is bounded $[0, 1]$. ECE = 0 indicates perfect calibration; ECE = 1 indicates maximum miscalibration. Our implementation uses 10 equal-width bins on $[0, 1]$. ECE is sensitive to the number of bins and the distribution of predicted probabilities; with $n = 894$ and $B = 10$, some bins may have sparse counts, introducing variance in the estimate. Temperature scaling directly targets ECE minimization by adjusting the logit scale. The post-scaling ECE of 0.036 for V2 mixed+T represents a 75% reduction from the pre-scaling value of 0.142, achieved by a single learned parameter $T = 0.59$. ECE is independent of classification accuracy — it measures only whether confidence magnitudes match empirical correctness rates.

**Gate A Threshold:** ECE ≤ 0.12 (deploy and validation)

---

### 3.2 Brier Score

**Definition:** The mean squared error between predicted probability vectors and one-hot true labels.

$$\text{Brier} = \frac{1}{N} \sum_{i=1}^{N} \sum_{k=1}^{K} (p_{ik} - y_{ik})^2$$

where $p_{ik}$ is the predicted probability for sample $i$ class $k$, and $y_{ik}$ is 1 if sample $i$ belongs to class $k$ and 0 otherwise.

**High School Interpretation:**  
The Brier score measures both whether the model gets the right answer AND whether its confidence levels are accurate. Unlike ECE (which only checks confidence), the Brier score penalizes both wrong predictions and miscalibrated confidence. It ranges from 0 (perfect) to 2 (worst possible for 3 classes). A Brier score of 0.128 is good — the model's probability estimates are close to reality. A Brier score of 0.340 is concerning — the model is frequently confident about wrong answers or uncertain about correct ones.

**Graduate Interpretation:**  
The Brier score is a strictly proper scoring rule (Brier, 1950), meaning it is uniquely minimized when predicted probabilities equal true conditional probabilities. It decomposes into three components: reliability (calibration error), resolution (how much predictions deviate from the base rate), and uncertainty (intrinsic difficulty). Unlike ECE, which bins predictions and measures only calibration, the Brier score captures both calibration and discrimination quality in a single quantity. This is why V1 mixed+T can pass ECE (0.021) but fail Brier (0.244) — its confidence is well-calibrated but its classification accuracy is insufficient, yielding large squared errors on misclassified samples. The Brier score is gated at ≤ 0.16 for deployment. V2 mixed+T achieves 0.128, the only configuration below this threshold among the variants.

**Gate A Threshold:** Brier ≤ 0.16 (deploy)

---

### 3.3 Maximum Calibration Error (MCE)

**Definition:** The largest calibration gap across all probability bins.

$$\text{MCE} = \max_{b \in \{1, \ldots, B\}} \left| \text{acc}(b) - \text{conf}(b) \right|$$

**High School Interpretation:**  
While ECE gives the average calibration gap, MCE reports the worst single gap. Even if most confidence levels are accurate, MCE catches the one range where the model is most dishonest. For example, the model might be well-calibrated for high-confidence predictions but badly wrong for medium-confidence ones. MCE would flag this. It is displayed on both pages as an informational metric — there is no Gate A threshold for MCE alone.

**Graduate Interpretation:**  
MCE identifies the worst-case calibration failure across the binned confidence spectrum. It is more conservative than ECE and is sensitive to outlier bins. MCE is useful for detecting localized miscalibration — for instance, a model might have excellent average calibration (low ECE) but a single bin with a 25% gap between confidence and accuracy. In safety-critical applications, MCE provides a minimax calibration guarantee. In our system, MCE is displayed for diagnostic purposes but is not independently gated. The ECE threshold (≤ 0.12) serves as the gated calibration metric because it better reflects overall calibration quality relevant to the gesture modulation system.

---

## 4. Gate A Quality Gate Statistics

Gate A is the quality control framework that determines whether a model is allowed to proceed to the next stage. There are two tiers with different thresholds.

---

### 4.1 Gate A-val (Synthetic Validation Tier)

**Purpose:** Controls whether a trained model checkpoint is exported to ONNX format from the training pipeline.

**Evaluation data:** Synthetic face-cropped frames (validation split from the same distribution as training data).

| Metric            | Threshold   | Direction        |
| ----------------- | ----------- | ---------------- |
| F1 Macro          | ≥ 0.84      | Higher is better |
| Balanced Accuracy | ≥ 0.85      | Higher is better |
| Per-Class F1      | ≥ 0.80 each | Higher is better |
| ECE               | ≤ 0.12      | Lower is better  |

**High School Interpretation:**  
Gate A-val is like a "midterm exam" that checks whether the model has learned its training material well enough to continue. It uses the same type of data the model was trained on (synthetic faces), so the thresholds are higher — the model should be very good on data similar to what it practiced with. If it fails here, there is a fundamental training problem to fix before even trying real-world evaluation.

**Graduate Interpretation:**  
Gate A-val evaluates in-distribution performance on a held-out validation set drawn from the same synthetic domain as training data. The higher thresholds (F1 ≥ 0.84, bAcc ≥ 0.85, per-class F1 ≥ 0.80) reflect the expectation that models should achieve near-ceiling performance on in-distribution data. Failure at this tier indicates underfitting, misconfiguration, or fundamental training issues — for example, V1 run_0107 failed Gate A-val on ECE (0.124 > 0.12) despite excellent classification performance (F1 = 0.990). Gate A-val is an automated checkpoint in the n8n training orchestrator workflow; passing triggers automatic ONNX export.

---

### 4.2 Gate A-deploy (Real-World Deployment Tier)

**Purpose:** Controls whether a model is promoted to the Jetson Xavier NX for production inference.

**Evaluation data:** 894 real AffectNet photographs (never seen during training or validation).

| Metric            | Threshold   | Direction        |
| ----------------- | ----------- | ---------------- |
| F1 Macro          | ≥ 0.75      | Higher is better |
| Balanced Accuracy | ≥ 0.75      | Higher is better |
| Per-Class F1      | ≥ 0.70 each | Higher is better |
| ECE               | ≤ 0.12      | Lower is better  |
| Brier             | ≤ 0.16      | Lower is better  |

**High School Interpretation:**  
Gate A-deploy is the "final exam" using completely new data the model has never seen before — real photographs of real people, not AI-generated images. The passing grades are lower than the midterm because real-world data is harder. The model must pass every single threshold — failing even one means it cannot be deployed to the robot. This prevents a model that is great at recognizing happiness but terrible at recognizing sadness from being deployed just because its overall score looks acceptable.

**Graduate Interpretation:**  
Gate A-deploy evaluates out-of-distribution generalization on real-world data, applying the deployment quality standard. The lower thresholds relative to Gate A-val explicitly acknowledge the synthetic-to-real domain gap. The inclusion of a Brier score threshold (≤ 0.16) — absent from Gate A-val — reflects the operational requirement that deployed models must have both accurate classifications and reliable confidence scores for the gesture modulation pipeline. The per-class F1 threshold (≥ 0.70) is the most discriminating gate: it rejected V2 synthetic (F1 Sad = 0.694, F1 Neutral = 0.699) despite acceptable aggregate metrics, correctly identifying a model with a dangerous 35.1% neutral→sad confusion rate. The conjunction (all gates must pass) implements a minimax criterion — no single failure mode is acceptable for production deployment.

---

### 4.3 Individual Gate Thresholds — Detailed Interpretation

#### F1 Macro ≥ 0.75 (deploy) / ≥ 0.84 (val)

**High School:** The model must correctly detect each emotion with both good accuracy and good completeness, averaged across all three emotions. A score of 0.75 means the model is right about 75% of the time on each emotion, balancing false alarms and missed detections.

**Graduate:** The F1 Macro threshold establishes the minimum acceptable harmonic mean of precision and recall. The deploy threshold (0.75) accommodates the expected 10–25% performance degradation from synthetic to real data. The validation threshold (0.84) ensures the training process has converged to a near-optimal solution before proceeding to out-of-distribution evaluation.

#### Balanced Accuracy ≥ 0.75 (deploy) / ≥ 0.85 (val)

**High School:** The model must detect each emotion at least 75% of the time on real data. This prevents the model from being good at one emotion and bad at another.

**Graduate:** Balanced accuracy ensures minimum recall across all classes. It is mathematically equivalent to macro recall and provides a class-prior-independent performance guarantee. Combined with F1 Macro, it constrains both the precision-recall trade-off and the class-balance trade-off.

#### Per-Class F1 ≥ 0.70 (deploy) / ≥ 0.80 (val)

**High School:** Each individual emotion must score at least 70% on its own — no emotion can be neglected. This is the gate that caught V2 synthetic's weakness: sadness scored 69.4% and neutral scored 69.9%, both just barely below the 70% requirement.

**Graduate:** The per-class floor prevents the "tyranny of the majority" where a classifier achieves acceptable aggregate metrics by excelling on prevalent classes while neglecting rare ones. With $K = 3$ classes and threshold 0.70, this gate ensures no class has F1 more than 30% below perfect. This was the decisive gate in the synthetic-only phase: V2's per-class CV of 15.1% (driven by F1 Sad = 0.694, F1 Neutral = 0.699 versus F1 Happy = 0.946) triggered the failure despite F1 Macro = 0.780 passing the 0.75 threshold.

#### ECE ≤ 0.12 (both tiers)

**High School:** The model's confidence must be off by no more than 12 percentage points on average. If the model says "80% sure it's happy," it should actually be correct about 68–92% of the time in practice. This ensures the robot's gestures match its actual accuracy.

**Graduate:** The ECE threshold constrains the expected absolute calibration error to 12%. This threshold was calibrated empirically: at ECE ≤ 0.12, the 5-tier gesture modulation system (threshold boundaries at 0.60, 0.70, 0.80, 0.90) produces behaviorally appropriate gestures within one tier of the optimal selection ≥ 88% of the time. ECE is gated at the same threshold for both tiers because calibration quality is equally important for both synthetic validation diagnostics and real-world deployment.

#### Brier ≤ 0.16 (deploy only)

**High School:** The Brier score combines accuracy and confidence into one measure. A threshold of 0.16 means the model's probability estimates must be close to reality — it cannot be wrong often or overconfident about wrong answers. This is the strictest calibration gate and the one that only V2 mixed+T passed.

**Graduate:** The Brier threshold ensures proper scoring rule compliance, capturing both discrimination (classification accuracy) and reliability (calibration quality) in a single constraint. The 0.16 threshold is stricter than ECE alone because Brier penalizes both miscalibration and misclassification. V1 mixed+T passes ECE (0.021) but fails Brier (0.244) because its classification accuracy (F1 = 0.834) is insufficient — the squared error on misclassified samples dominates. Only V2 mixed+T's combination of high classification accuracy (F1 = 0.916) and good calibration (ECE = 0.036) yields a Brier score below 0.16.

---

### 4.4 Gate Compliance Summary

| Configuration | F1 ≥ 0.75 | bAcc ≥ 0.75 | F1/class ≥ 0.70 | ECE ≤ 0.12 | Brier ≤ 0.16 | Total   |
| ------------- | --------- | ----------- | --------------- | ---------- | ------------ | ------- |
| V1 synthetic  | ✅ 0.781   | ✅ 0.799     | ✅ all ≥ 0.743   | ✅ 0.102    | ❌ 0.340      | 4/5     |
| V2 synthetic  | ✅ 0.780   | ✅ 0.812     | ❌ sad=0.694     | ✅ 0.096    | ❌ 0.279      | 3/5     |
| V1 mixed+T    | ✅ 0.834   | ✅ 0.840     | ✅ all ≥ 0.801   | ✅ 0.021    | ❌ 0.244      | 4/5     |
| V2 mixed+T    | ✅ 0.916   | ✅ 0.921     | ✅ all ≥ 0.888   | ✅ 0.036    | ✅ 0.128      | **5/5** |

**High School:** Only V2 mixed+T passes every single checkpoint. All other models fail at least one test — usually the Brier score, which is the hardest gate to pass because it requires both good accuracy and good confidence.

**Graduate:** The gate compliance pattern reveals the iterative diagnostic capability of the framework. In the synthetic-only phase, per-class F1 was the discriminating gate (rejecting V2 despite higher aggregate scores). After mixed-domain training, Brier became the discriminating gate (reflecting the residual calibration-classification coupling). Temperature scaling resolved the final blocker by decoupling calibration from classification quality. The progression demonstrates that the gate framework not only selects models but also diagnoses specific deficiencies, guiding targeted interventions.

---

## 5. Coefficient of Variation (CV)

**Definition:** The standard deviation of per-class F1 scores divided by their mean, expressed as a percentage.

$$CV = \frac{\sigma(F1_{\text{happy}}, F1_{\text{sad}}, F1_{\text{neutral}})}{\mu(F1_{\text{happy}}, F1_{\text{sad}}, F1_{\text{neutral}})} \times 100\%$$

**High School Interpretation:**  
CV measures how evenly the model performs across all three emotions. A low CV (like 4%) means the model is equally good at all three — no emotion is being neglected. A high CV (like 15%) means there is a big gap between the best and worst emotions. V2 synthetic had CV = 15.1% because it was great at happy (0.946) but poor at sad (0.694) and neutral (0.699). After mixed-domain training, V2's CV dropped to 4.3% — nearly as balanced as V1's 4.2%.

**Graduate Interpretation:**  
The coefficient of variation of per-class F1 scores is a dimensionless measure of classification equity across the label space. It normalizes the standard deviation by the mean, enabling comparison across models with different overall performance levels. CV < 5% indicates equitable classification; CV > 10% signals significant class-level disparities. In the synthetic-only phase, the CV ratio (V2/V1 = 15.1%/4.2% = 3.6×) was a stronger signal of V2's deficiency than the F1 Macro difference (Δ = 0.001), demonstrating the value of dispersion metrics over central tendency measures for deployment decisions.

---

## 6. Cohen's Kappa (κ)

**Definition:** A measure of agreement between the model's predictions and the true labels, corrected for agreement expected by chance.

$$\kappa = \frac{p_o - p_e}{1 - p_e}$$

where $p_o$ is observed agreement (accuracy) and $p_e$ is expected agreement under random assignment.

**High School Interpretation:**  
Cohen's kappa asks: "Is the model actually smarter than random guessing?" If you randomly assigned emotions to photos, you would get some right just by luck. Kappa measures how much better the model does compared to this luck baseline. A kappa of 0 means "no better than random." A kappa of 1 means "perfect." Our best model (V2 mixed+T) has κ = 0.865, which is in the "almost perfect" category. V1 synthetic's κ = 0.645 is "substantial" — clearly better than chance but with room to improve.

**Graduate Interpretation:**  
Cohen's kappa corrects observed accuracy for chance agreement, providing a more conservative estimate of classification performance than raw accuracy. The Landis and Koch (1977) benchmark scale categorizes κ: 0.41–0.60 moderate, 0.61–0.80 substantial, 0.81–1.00 almost perfect. In the synthetic-only phase, V2's higher κ (0.712 vs. 0.645) was driven by its excellent happy recall (48.7% prevalence class), demonstrating that κ — as a global measure — is susceptible to the same majority-class inflation as accuracy. The improvement from κ = 0.645 (V1 synthetic) to κ = 0.865 (V2 mixed+T) represents a shift from "substantial" to "almost perfect" agreement, corresponding to the resolution of both the neutral→sad confusion pattern and the synthetic-to-real domain gap.

---

## 7. Wilson Score Confidence Intervals

**Definition:** A confidence interval for a proportion that maintains correct coverage even near 0 or 1, based on inverting the score test.

$$\hat{p} \pm \frac{z_{\alpha/2}}{1 + z_{\alpha/2}^2/n}\left(\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z_{\alpha/2}^2}{4n^2}}\right)$$

**High School Interpretation:**  
When we test a model on 160 sad photos and it correctly identifies 143, the recall is 143/160 = 89.4%. But if we tested on a different set of 160 sad photos, we might get 88% or 91%. The Wilson confidence interval gives us a range — say [84.4%, 93.8%] — within which we are 95% confident the "true" recall falls. It accounts for the limited number of test photos. With only 160 sad photos, the interval is wider (more uncertainty) than for happy with 435 photos (narrower interval, more certainty).

**Graduate Interpretation:**  
The Wilson score interval (Wilson, 1927) is preferred over the Wald (normal approximation) interval for proportions because it maintains nominal coverage even when $\hat{p}$ is near 0 or 1, and for small $n$. For per-class recall with class sizes of 160–435, the Wilson interval provides meaningful coverage guarantees. The non-overlapping Wilson intervals for V1 and V2 happy recall ([0.591, 0.681] vs. [0.906, 0.953]) and neutral recall ([0.903, 0.959] vs. [0.546, 0.656]) in the synthetic-only phase confirmed that the per-class performance differences were statistically significant, not sampling artifacts. This supported the deployment decision with inferential rigor beyond point estimates.

---

## 8. Summary Table: All Metrics at a Glance

| Metric            | Page      | Type           | Higher/Lower Better | Gate A Threshold  | Purpose                         |
| ----------------- | --------- | -------------- | ------------------- | ----------------- | ------------------------------- |
| Accuracy          | Dashboard | Classification | Higher              | — (not gated)     | Overall correctness             |
| Precision (Macro) | Both      | Classification | Higher              | — (not gated)     | False alarm rate                |
| Recall (Macro)    | Both      | Classification | Higher              | — (not gated)     | Detection completeness          |
| F1 (Macro)        | Both      | Classification | Higher              | ≥ 0.75 (deploy)   | Primary quality metric          |
| Balanced Accuracy | Both      | Classification | Higher              | ≥ 0.75 (deploy)   | Class-balanced detection        |
| F1 Happy          | Compare   | Classification | Higher              | ≥ 0.70 (deploy)   | Happy detection quality         |
| F1 Sad            | Compare   | Classification | Higher              | ≥ 0.70 (deploy)   | Sad detection quality           |
| F1 Neutral        | Compare   | Classification | Higher              | ≥ 0.70 (deploy)   | Neutral detection quality       |
| ECE               | Both      | Calibration    | Lower               | ≤ 0.12 (deploy)   | Confidence trustworthiness      |
| Brier             | Both      | Calibration    | Lower               | ≤ 0.16 (deploy)   | Combined accuracy + calibration |
| MCE               | Both      | Calibration    | Lower               | — (not gated)     | Worst-case calibration          |
| Composite Score   | Compare   | Composite      | Higher              | — (ranking only)  | Automated run selection         |
| Cohen's κ         | Paper     | Agreement      | Higher              | — (analysis only) | Chance-corrected agreement      |
| CV (per-class F1) | Paper     | Dispersion     | Lower               | — (analysis only) | Classification equity           |
| Wilson CI         | Paper     | Inference      | — (interval)        | — (analysis only) | Statistical significance        |
| Confusion Matrix  | Both      | Diagnostic     | — (table)           | — (diagnostic)    | Error pattern analysis          |

---

*This document accompanies the research paper "Iterative Model Selection for Privacy-First Emotion Recognition" and provides interpretations at both introductory and graduate levels for all statistical measures used in the Reachy Emotion Classification System.*
