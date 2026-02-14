# Statistical Analysis Workflow Overview

## Introduction

This tutorial provides a comprehensive overview of the statistical analysis workflow for emotion classification model evaluation. You'll learn how the three enhanced R scripts work together to provide a complete picture of model performance and fine-tuning effects.

## The Three-Stage Analysis Pipeline

### Stage 1: Quality Gate Validation (`01_quality_gate_metrics_enhanced.R`)
**Purpose**: Determine if your model meets minimum performance requirements

**Key Question**: "Is this model good enough for deployment?"

**What it does**:
- Computes classification metrics (Macro F1, Balanced Accuracy, F1 Neutral)
- Evaluates against quality gate thresholds
- Provides risk assessment and recommendations
- Generates confusion matrix visualizations

**When to use**: 
- After training any emotion classification model
- Before deploying to production
- When comparing different model architectures

### Stage 2: Pattern Change Detection (`02_stuart_maxwell_enhanced.R`)
**Purpose**: Detect if fine-tuning systematically changed prediction patterns

**Key Question**: "Did fine-tuning change HOW the model classifies emotions?"

**What it does**:
- Compares prediction patterns between base and fine-tuned models
- Tests for marginal homogeneity using chi-squared statistics
- Calculates effect sizes and agreement rates
- Identifies which emotions shifted in frequency

**When to use**:
- After fine-tuning an existing model
- When comparing two different model versions
- To understand systematic changes in model behavior

### Stage 3: Per-Class Impact Analysis (`03_perclass_paired_ttests_enhanced.R`)
**Purpose**: Identify which specific emotion classes improved or degraded

**Key Question**: "WHICH emotions got better/worse after fine-tuning?"

**What it does**:
- Performs paired t-tests on fold-level F1 scores
- Applies multiple comparison corrections (Benjamini-Hochberg)
- Calculates effect sizes for each emotion class
- Provides statistical significance testing with FDR control

**When to use**:
- After Stuart-Maxwell test indicates significant changes
- To identify specific areas of improvement/degradation
- For targeted model improvement strategies

## Complete Workflow Example

### Scenario: Evaluating Fine-Tuning Results

You've fine-tuned your emotion classification model and want to understand the impact. Here's the complete analysis workflow:

#### Step 1: Quality Gate Check
```bash
# Check if fine-tuned model meets deployment standards
Rscript 01_quality_gate_metrics_enhanced.R \
  --predictions-csv results/finetuned_predictions.csv \
  --model-name "fine_tuned_v2" \
  --output results/quality_gates \
  --plot --interactive
```

**Possible Outcomes**:
- ✅ **All gates pass**: Model ready for deployment, proceed to change analysis
- ⚠️ **Some gates fail**: Investigate specific issues, may still proceed with analysis
- ❌ **Critical failures**: Model needs more work before deployment

#### Step 2: Pattern Change Analysis
```bash
# Compare base vs fine-tuned prediction patterns
Rscript 02_stuart_maxwell_enhanced.R \
  --predictions-csv results/model_comparison.csv \
  --output results/stuart_maxwell \
  --plot --interactive
```

**Possible Outcomes**:
- **Significant change (p < 0.05)**: Fine-tuning had systematic impact → Proceed to Step 3
- **Non-significant (p ≥ 0.05)**: Minimal systematic changes → Analysis complete
- **Large effect size**: Even if non-significant, might warrant per-class investigation

#### Step 3: Per-Class Investigation
```bash
# Identify which emotions improved/degraded
Rscript 03_perclass_paired_ttests_enhanced.R \
  --metrics-csv results/fold_level_metrics.csv \
  --correction BH \
  --output results/perclass_analysis \
  --plot
```

**Outcomes**:
- **Specific improvements identified**: Focus future work on successful strategies
- **Degradations detected**: Investigate causes and mitigation strategies
- **Mixed results**: Understand trade-offs and overall impact

## Data Requirements

### For Quality Gates (Stage 1)
**Required CSV format**:
```csv
y_true,y_pred
anger,anger
happiness,happiness
neutral,sadness
fear,fear
...
```

**Columns**:
- `y_true`: Ground truth emotion labels
- `y_pred`: Model predictions

### For Stuart-Maxwell (Stage 2)
**Required CSV format**:
```csv
base_pred,finetuned_pred
anger,anger
happiness,surprise
neutral,neutral
fear,anger
...
```

**Columns**:
- `base_pred`: Base model predictions
- `finetuned_pred`: Fine-tuned model predictions
- **Note**: Must be paired predictions on same samples

### For Per-Class Analysis (Stage 3)
**Required CSV format**:
```csv
fold,emotion_class,base_score,finetuned_score
1,anger,0.82,0.87
1,happiness,0.91,0.93
1,neutral,0.88,0.90
2,anger,0.85,0.89
...
```

**Columns**:
- `fold`: Cross-validation fold number
- `emotion_class`: Emotion class name
- `base_score`: Base model F1 score for this class/fold
- `finetuned_score`: Fine-tuned model F1 score for this class/fold

## Decision Tree: When to Use Each Script

```
Start: Do you have a trained emotion classification model?
│
├─ YES → Run Quality Gates (Stage 1)
│   │
│   ├─ Gates PASS → Do you have a comparison model?
│   │   │
│   │   ├─ YES → Run Stuart-Maxwell (Stage 2)
│   │   │   │
│   │   │   ├─ Significant change → Run Per-Class Analysis (Stage 3)
│   │   │   └─ No significant change → Analysis complete
│   │   │
│   │   └─ NO → Analysis complete (single model evaluation)
│   │
│   └─ Gates FAIL → Investigate issues, improve model, repeat
│
└─ NO → Train model first, then return to workflow
```

## Interpreting Combined Results

### Scenario 1: Successful Fine-Tuning
```
Quality Gates: ✅ PASS (all thresholds met)
Stuart-Maxwell: Significant change (p = 0.003, medium effect)
Per-Class: 3 classes improved, 1 degraded, 4 unchanged
```

**Interpretation**: Fine-tuning was successful with targeted improvements
**Action**: Deploy fine-tuned model, monitor degraded class

### Scenario 2: Marginal Improvement
```
Quality Gates: ⚠️ MIXED (2/3 gates pass)
Stuart-Maxwell: Non-significant (p = 0.12, small effect)
Per-Class: Not needed (no systematic changes)
```

**Interpretation**: Fine-tuning had minimal impact
**Action**: Consider alternative training strategies or more data

### Scenario 3: Problematic Fine-Tuning
```
Quality Gates: ❌ FAIL (critical failures detected)
Stuart-Maxwell: Significant change (p < 0.001, large effect)
Per-Class: 2 classes improved, 4 degraded, 2 unchanged
```

**Interpretation**: Fine-tuning caused more harm than good
**Action**: Revert to base model, investigate fine-tuning approach

## Advanced Usage Patterns

### Batch Analysis
```bash
# Analyze multiple model versions
for model in v1 v2 v3; do
  echo "Analyzing model $model"
  
  # Quality gates
  Rscript 01_quality_gate_metrics_enhanced.R \
    --predictions-csv results/${model}_predictions.csv \
    --model-name $model \
    --output results/batch_analysis/$model
done
```

### Automated Pipeline
```bash
#!/bin/bash
# complete_analysis.sh

MODEL_NAME=$1
OUTPUT_DIR="results/analysis_$(date +%Y%m%d_%H%M%S)"

echo "Starting complete analysis for $MODEL_NAME"

# Stage 1: Quality Gates
echo "Stage 1: Quality Gate Analysis"
Rscript 01_quality_gate_metrics_enhanced.R \
  --predictions-csv data/${MODEL_NAME}_predictions.csv \
  --model-name $MODEL_NAME \
  --output $OUTPUT_DIR/quality_gates \
  --plot

# Stage 2: Stuart-Maxwell (if comparison data exists)
if [ -f "data/${MODEL_NAME}_comparison.csv" ]; then
  echo "Stage 2: Stuart-Maxwell Analysis"
  Rscript 02_stuart_maxwell_enhanced.R \
    --predictions-csv data/${MODEL_NAME}_comparison.csv \
    --output $OUTPUT_DIR/stuart_maxwell \
    --plot
fi

# Stage 3: Per-Class Analysis (if fold data exists)
if [ -f "data/${MODEL_NAME}_folds.csv" ]; then
  echo "Stage 3: Per-Class Analysis"
  Rscript 03_perclass_paired_ttests_enhanced.R \
    --metrics-csv data/${MODEL_NAME}_folds.csv \
    --output $OUTPUT_DIR/perclass \
    --plot
fi

echo "Analysis complete. Results in: $OUTPUT_DIR"
```

## Common Analysis Patterns

### Pattern 1: Model Development Cycle
1. **Train initial model** → Quality Gates
2. **Fine-tune model** → Quality Gates + Stuart-Maxwell + Per-Class
3. **Iterate improvements** → Repeat analysis cycle
4. **Final validation** → Complete analysis before deployment

### Pattern 2: Model Comparison Study
1. **Train multiple architectures** → Quality Gates for each
2. **Select best performers** → Stuart-Maxwell between top candidates
3. **Understand differences** → Per-Class analysis for insights
4. **Make informed decision** → Deploy best overall model

### Pattern 3: Production Monitoring
1. **Deploy model** → Baseline Quality Gates analysis
2. **Collect new data** → Periodic Quality Gates monitoring
3. **Detect drift** → Stuart-Maxwell vs baseline
4. **Investigate changes** → Per-Class analysis for specific issues

## Statistical Considerations

### Sample Size Requirements
- **Quality Gates**: Minimum 100 samples per class (800 total)
- **Stuart-Maxwell**: Minimum 50 paired predictions per class (400 total)
- **Per-Class**: Minimum 5 folds, preferably 10+ for adequate power

### Multiple Comparisons
- **Stuart-Maxwell**: Single test, no correction needed
- **Per-Class**: Always use multiple comparison correction (BH recommended)
- **Quality Gates**: Three related tests, consider Bonferroni if very conservative

### Effect Size Guidelines
- **Negligible**: < 0.2 (statistical artifact)
- **Small**: 0.2-0.5 (detectable by experts)
- **Medium**: 0.5-0.8 (noticeable to informed observers)
- **Large**: > 0.8 (obvious to anyone)

## Troubleshooting Common Issues

### Issue 1: Quality Gates Fail
**Symptoms**: Low F1 scores, poor balanced accuracy
**Solutions**:
- Check class balance in training data
- Increase model complexity or training time
- Improve data quality and labeling
- Consider different architectures

### Issue 2: Stuart-Maxwell Non-Significant Despite Visible Changes
**Symptoms**: p > 0.05 but apparent differences in confusion matrices
**Solutions**:
- Increase sample size for more power
- Check effect size (might be practically significant)
- Examine per-class changes individually
- Consider relaxed significance threshold (α = 0.10)

### Issue 3: Per-Class Tests Find No Significant Changes
**Symptoms**: All adjusted p-values > 0.05
**Solutions**:
- Check if Stuart-Maxwell was significant (prerequisite)
- Increase number of CV folds for more power
- Use less conservative correction (Holm vs Bonferroni)
- Examine effect sizes for practical significance

## Key Takeaways

1. **Sequential Analysis**: Use scripts in order for logical flow
2. **Data Requirements**: Ensure proper data format for each stage
3. **Statistical Rigor**: Always apply appropriate corrections and interpret effect sizes
4. **Business Context**: Connect statistical results to practical implications
5. **Iterative Process**: Use results to guide model improvement decisions

## Next Steps

- **Hands-On Practice**: Work through the individual script tutorials
- **Real Data Analysis**: Apply workflow to your own emotion classification models
- **Advanced Techniques**: Explore interactive visualizations and custom analyses
- **Production Integration**: Incorporate into your MLOps pipeline

This workflow provides a systematic approach to understanding model performance and the effects of model improvements. Master this process to make data-driven decisions about emotion classification model development and deployment.
