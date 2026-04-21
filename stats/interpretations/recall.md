## Recall (Macro)

**Definition:** Of all photos that actually showed a particular emotion, how many did the model correctly identify---averaged equally across all three classes.

**Formula:** Recall_k = TP_k / (TP_k + FN_k); Recall_macro = mean across classes.

### Plain Language
Recall asks: "When someone really was sad, did the model catch it?" If recall for sadness is 0.89, the model correctly detected 89 out of 100 actually-sad faces. The other 11 were missed. Macro recall averages this detection rate across happy, sad, and neutral equally.

### Technical Detail
Macro recall (sensitivity) is the unweighted mean of per-class true positive rates. It measures completeness of detection. Low recall on a class means the model systematically misses that emotion. V2 synthetic's neutral recall was only 0.602---it missed 40% of neutral faces, predominantly classifying them as sad (105/299 = 35.1%). Macro recall is mathematically equivalent to balanced accuracy in this evaluation pipeline.

**Gate A:** Not gated independently (captured via balanced accuracy and F1).