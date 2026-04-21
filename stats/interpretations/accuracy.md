## Accuracy

**Definition:** The proportion of all predictions that are correct.

**Formula:** Accuracy = (Correct Predictions) / (Total Predictions)

### Plain Language
Accuracy is like a test score. If the model looked at 894 photos and correctly identified the emotion in 730 of them, accuracy is 730/894 = 81.7%. The limitation: if most photos show happy faces, the model could score well by always guessing "happy" even if it never recognizes sadness. That is why accuracy is not gated and is supplemented by F1 Macro and Balanced Accuracy.

### Technical Detail
Accuracy is the simplest point estimate of classifier performance. In the multi-class setting, it equals the trace of the confusion matrix divided by the total sample count. With our imbalanced test set (48.7% happy, 17.9% sad, 33.4% neutral), accuracy is biased toward the majority class. A classifier predicting "happy" for every input achieves 48.7% accuracy without learning. Accuracy is reported for completeness but is not used in any Gate A threshold.

**Gate A:** Not gated (informational only).