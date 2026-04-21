## Precision (Macro)

**Definition:** Of all predictions for a given emotion, how many were correct---averaged equally across all three classes.

**Formula:** Precision_k = TP_k / (TP_k + FP_k); Precision_macro = mean across classes.

### Plain Language
Imagine the model says "this person is sad" 200 times. Precision tells you how many of those 200 were actually sad. If precision for sadness is 0.88, then 88 out of 100 "sad" predictions were correct. The other 12 were false alarms. Macro precision averages this across happy, sad, and neutral equally.

### Technical Detail
Macro precision is the unweighted mean of per-class positive predictive values. It is sensitive to false positives: low sad precision means frequent false sadness alerts. V2 synthetic had sad precision of only 56.5%---when it identified sadness, it was correct barely more than half the time. This metric is displayed on the Dashboard but is not independently gated; it is captured implicitly through per-class F1 and F1 Macro thresholds.

**Gate A:** Not gated independently (captured via F1).