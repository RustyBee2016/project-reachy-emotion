## Balanced Accuracy

**Definition:** The average of per-class recall values. Equivalent to accuracy computed as if all classes had equal representation.

**Formula:** Balanced Accuracy = (1/K) * sum of Recall_k for each class k.

### Plain Language
Regular accuracy can be misleading when some emotions appear much more often than others. Balanced accuracy fixes this by treating each emotion equally. If the model has 93% recall on happy but only 60% on neutral, balanced accuracy averages these rather than letting the many happy photos dominate. A balanced accuracy of 0.921 means the model detects about 92% of each emotion on average.

### Technical Detail
Balanced accuracy is the arithmetic mean of per-class sensitivities, equivalent to expected accuracy under a uniform class prior. It corrects for prevalence bias: a naive classifier achieves ~33.3% balanced accuracy (chance level for 3 classes) regardless of class distribution. Combined with F1 Macro, it constrains both the precision-recall trade-off and the class-balance trade-off. It carries 20% weight in the composite deployment score.

**Gate A:** Balanced Accuracy >= 0.75 (deploy), >= 0.85 (validation).
