## Per-Class F1 (F1 Happy, F1 Sad, F1 Neutral)

**Definition:** The F1 score computed separately for each emotion class.

**Formula:** F1_k = 2 * Precision_k * Recall_k / (Precision_k + Recall_k), computed independently for happy, sad, and neutral.

### Plain Language
Instead of one overall F1 score, per-class F1 gives three separate scores---one for happy, one for sad, one for neutral. This matters because a model might be excellent at recognizing happiness but terrible at recognizing sadness. V2 synthetic had F1 Happy = 0.946 (excellent) but F1 Sad = 0.694 (below the 0.70 passing threshold). Per-class F1 is what caught this hidden weakness that aggregate F1 Macro concealed.

### Technical Detail
Per-class F1 scores decompose the macro aggregate into its constituent components, revealing class-level disparities. The coefficient of variation (CV) of per-class F1 quantifies classification equity: V2 synthetic had CV = 15.1% (severe inequity) versus V1 synthetic's 4.2%. The per-class F1 gate (>= 0.70 each) prevents deployment of models that achieve acceptable macro metrics by excelling on the majority class (happy, 48.7%) while neglecting minorities (sad, 17.9%). This gate correctly rejected V2 synthetic despite its higher composite score, kappa, and accuracy.

**Gate A:** Per-class F1 >= 0.70 each (deploy), >= 0.80 each (validation).
