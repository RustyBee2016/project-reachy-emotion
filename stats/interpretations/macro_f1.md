## F1 Score (Macro)

**Definition:** The harmonic mean of precision and recall, averaged equally across all three classes. The single most important classification metric.

**Formula:** F1_k = 2 * Precision_k * Recall_k / (Precision_k + Recall_k); F1_macro = mean across classes.

### Plain Language
F1 combines two questions: "When the model says an emotion, is it right?" (precision) and "When the emotion is there, does the model find it?" (recall). If either is low, F1 gets dragged down. A score of 0.916 means the model is both accurate and thorough across all three emotions. The "macro" part means each emotion counts equally---happy doesn't get more influence just because there are more happy photos.

### Technical Detail
F1 Macro is the primary classification metric, carrying 50% weight in the composite deployment score. As the harmonic mean of precision and recall, it penalizes imbalance between the two. Macro averaging treats each class equally regardless of support, which is critical given the imbalanced test set (48.7% happy). F1 Macro can still mask class-level failures---V1 (0.781) and V2 (0.780) had nearly identical F1 Macro despite radically different per-class profiles. This is why per-class F1 gates were added.

**Gate A:** F1 Macro >= 0.75 (deploy), >= 0.84 (validation).
