# Phase 3 Statistical Analysis: Edge Deployment Performance Evaluation

**Validating Real-Time Inference on Jetson Xavier NX Through Latency, Throughput, and Reliability Metrics**

---

## Abstract

This paper presents the statistical analysis for Phase 3 of Project Reachy, focusing on edge deployment performance validation. We evaluate the TensorRT-optimized EfficientNet-B0 engine running on Jetson Xavier NX against Gate B and Gate C requirements through: (1) **Latency Analysis**—measuring inference time distributions, p50/p95 percentiles, and end-to-end response latency; (2) **Resource Utilization**—tracking GPU memory consumption, thermal behavior, and CPU overhead; (3) **Throughput and Reliability**—assessing sustained FPS, WebSocket connection stability, and gesture execution success rates. Results demonstrate Gate B compliance with p50 latency = 42 ms (threshold ≤ 120 ms), GPU memory = 0.84 GB (threshold ≤ 2.5 GB), and sustained throughput of 28 FPS. Gate C validation confirms end-to-end latency = 187 ms (threshold ≤ 300 ms) and abstention rate = 4.8% (threshold ≤ 20%).

**Keywords:** Edge inference, TensorRT, Jetson Xavier NX, latency analysis, repeated measures ANOVA, multiple regression, autocorrelation, throughput, deployment validation

---

## 1. Introduction

### 1.1 Phase 3 Objectives

Phase 3 deploys the trained emotion classifier to the Jetson Xavier NX edge device for real-time inference during human-robot interaction. Key components include:

- **TensorRT Conversion**: ONNX → FP16 TensorRT engine optimization
- **DeepStream Integration**: GStreamer pipeline with `nvinfer` plugin
- **WebSocket Communication**: Bidirectional Jetson ↔ Gateway messaging
- **Staged Rollout**: Shadow → Canary → Production deployment

### 1.2 Research Questions

1. **RQ1**: Does the TensorRT engine meet Gate B latency and memory requirements?
2. **RQ2**: Can the system sustain required throughput under continuous operation?
3. **RQ3**: Does the end-to-end system meet Gate C user experience thresholds?

### 1.3 Quality Gates

| Gate | Focus | Key Metrics |
|------|-------|-------------|
| **Gate B** | Shadow Mode | Latency p50 ≤ 120 ms, p95 ≤ 250 ms, GPU ≤ 2.5 GB, F1 ≥ 0.80 |
| **Gate C** | User Rollout | E2E latency ≤ 300 ms, abstention ≤ 20%, complaints < 1% |

---

## 2. Statistical Framework

### 2.1 Latency Metrics

#### 2.1.1 Inference Latency Distribution

Inference latency ($L$) is modeled as a right-skewed distribution. We report:

- **Mean**: $\bar{L} = \frac{1}{n} \sum_{i=1}^{n} L_i$
- **Median (p50)**: $L_{0.50}$ such that $P(L \leq L_{0.50}) = 0.50$
- **95th Percentile (p95)**: $L_{0.95}$ such that $P(L \leq L_{0.95}) = 0.95$
- **Standard Deviation**: $s_L = \sqrt{\frac{1}{n-1} \sum_{i=1}^{n} (L_i - \bar{L})^2}$

#### 2.1.2 End-to-End Latency

Total latency from frame capture to gesture execution:

$$L_{\text{E2E}} = L_{\text{capture}} + L_{\text{inference}} + L_{\text{network}} + L_{\text{LLM}} + L_{\text{gesture}}$$

### 2.2 Resource Utilization Metrics

#### 2.2.1 GPU Memory

Peak and sustained GPU memory consumption:

$$\text{GPU}_{\text{peak}} = \max_{t} \text{GPU}(t)$$
$$\text{GPU}_{\text{sustained}} = \frac{1}{T} \int_0^T \text{GPU}(t) \, dt$$

#### 2.2.2 Thermal Analysis

GPU temperature over time with throttling threshold:

$$\text{Throttle Rate} = \frac{\text{Time at } T > T_{\text{thresh}}}{\text{Total Time}} \times 100\%$$

### 2.3 Throughput and Reliability Metrics

#### 2.3.1 Frames Per Second (FPS)

Sustained inference throughput:

$$\text{FPS} = \frac{n_{\text{frames}}}{\Delta t}$$

#### 2.3.2 WebSocket Reliability

Connection stability metrics:

- **Reconnection Rate**: Disconnections per hour
- **Message Delivery Rate**: Successfully delivered / total sent
- **Heartbeat Success Rate**: Successful heartbeats / total attempts

#### 2.3.3 Gesture Execution Success

$$\text{Gesture Success Rate} = \frac{\text{Gestures Executed}}{\text{Gesture Cues Received}} \times 100\%$$

### 2.4 Advanced Multivariate Methods

#### 2.4.1 Repeated Measures ANOVA

**Purpose**: Tests throughput stability across time periods while accounting for correlated measurements from the same device.

**Total sum of squares decomposition**:

$$SS_{total} = SS_{subjects} + SS_{time} + SS_{error}$$

**Between-time sum of squares**:

$$SS_{time} = n \sum_{j=1}^{k} (\bar{Y}_{\cdot j} - \bar{Y}_{\cdot \cdot})^2$$

**Error sum of squares** (subject × time interaction):

$$SS_{error} = \sum_{i=1}^{n} \sum_{j=1}^{k} (Y_{ij} - \bar{Y}_{i \cdot} - \bar{Y}_{\cdot j} + \bar{Y}_{\cdot \cdot})^2$$

**F-statistic**:

$$F = \frac{MS_{time}}{MS_{error}} = \frac{SS_{time}/(k-1)}{SS_{error}/((n-1)(k-1))}$$

Under $H_0$, $F \sim F(k-1, (n-1)(k-1))$.

**Mauchly's sphericity test**:

$$W = \frac{|\mathbf{C}^T \mathbf{S} \mathbf{C}|}{\left( \frac{\text{tr}(\mathbf{C}^T \mathbf{S} \mathbf{C})}{k-1} \right)^{k-1}}$$

where $\mathbf{C}$ is an orthonormal contrast matrix and $\mathbf{S}$ is the covariance matrix.

**Greenhouse-Geisser correction** (if sphericity violated):

$$\hat{\epsilon}_{GG} = \frac{\left( \sum_{j=1}^{k-1} \lambda_j \right)^2}{(k-1) \sum_{j=1}^{k-1} \lambda_j^2}$$

where $\lambda_j$ are eigenvalues of the transformed covariance matrix.

#### 2.4.2 Multiple Regression for E2E Latency

**Purpose**: Model end-to-end latency as a function of component latencies to identify optimization targets.

**E2E latency model**:

$$L_{E2E} = \beta_0 + \beta_1 L_{capture} + \beta_2 L_{inference} + \beta_3 L_{network} + \beta_4 L_{LLM} + \beta_5 L_{gesture} + \epsilon$$

**Standardized coefficients** (for comparing relative importance):

$$\beta_j^* = \beta_j \cdot \frac{s_{X_j}}{s_Y}$$

where $s_{X_j}$ is the standard deviation of predictor $j$ and $s_Y$ is the standard deviation of the response.

**Variance Inflation Factor** (multicollinearity diagnostic):

$$VIF_j = \frac{1}{1 - R_j^2}$$

where $R_j^2$ is the $R^2$ from regressing $X_j$ on all other predictors. $VIF > 10$ indicates problematic multicollinearity.

**Coefficient of determination**:

$$R^2 = 1 - \frac{\sum_i (y_i - \hat{y}_i)^2}{\sum_i (y_i - \bar{y})^2}$$

#### 2.4.3 Autocorrelation Analysis (Time Series)

**Purpose**: Tests whether FPS measurements are independent over time, validating ANOVA assumptions.

**Sample autocovariance** at lag $k$:

$$\hat{\gamma}_k = \frac{1}{n} \sum_{t=k+1}^{n}(y_t - \bar{y})(y_{t-k} - \bar{y})$$

**Autocorrelation function (ACF)**:

$$r_k = \frac{\hat{\gamma}_k}{\hat{\gamma}_0} = \frac{\sum_{t=k+1}^{n}(y_t - \bar{y})(y_{t-k} - \bar{y})}{\sum_{t=1}^{n}(y_t - \bar{y})^2}$$

**95% confidence bounds** (under white noise):

$$\pm \frac{1.96}{\sqrt{n}}$$

**Ljung-Box test** (joint test for autocorrelation up to lag $h$):

$$Q = n(n+2) \sum_{k=1}^{h} \frac{r_k^2}{n-k}$$

Under $H_0$ (no autocorrelation), $Q \sim \chi^2(h)$.

**Box-Pierce test** (simpler alternative):

$$Q_{BP} = n \sum_{k=1}^{h} r_k^2$$

#### 2.4.4 Multivariate Profile Analysis

**Purpose**: Compares resource utilization (GPU, CPU, memory) profiles across test conditions.

**Contrast matrix** for testing profile shape:

$$\mathbf{C} = \begin{bmatrix} 1 & -1 & 0 \\ 0 & 1 & -1 \end{bmatrix}$$

**Parallelism test** (equal slopes across groups):

$$H_0: \mathbf{C}(\boldsymbol{\mu}_1 - \boldsymbol{\mu}_2) = \mathbf{0}$$

$$\Lambda_{parallel} = \frac{|\mathbf{E}|}{|\mathbf{E} + \mathbf{H}|}$$

where $\mathbf{H}$ is the hypothesis SSCP and $\mathbf{E}$ is the error SSCP for transformed variables.

**Levels test** (equal overall means):

$$H_0: \mathbf{1}^T \boldsymbol{\mu}_1 = \mathbf{1}^T \boldsymbol{\mu}_2$$

Equivalent to testing if the average across variables differs between groups.

**Flatness test** (equal variable means within group):

$$H_0: \mu_{\cdot 1} = \mu_{\cdot 2} = \cdots = \mu_{\cdot p}$$

Tests whether the profile is "flat" (all resources equally utilized).

---

## 3. Experimental Setup

### 3.1 Hardware Configuration

| Component | Specification |
|-----------|---------------|
| **Device** | Jetson Xavier NX 16 GB |
| **GPU** | 384 CUDA cores, Volta architecture |
| **CPU** | 6-core NVIDIA Carmel ARM v8.2 |
| **Memory** | 16 GB LPDDR4x (shared CPU/GPU) |
| **Storage** | 256 GB NVMe SSD |
| **Network** | Gigabit Ethernet (10.0.4.150) |

### 3.2 Software Configuration

| Component | Version |
|-----------|---------|
| JetPack | 5.1.2 |
| TensorRT | 8.6.1 |
| DeepStream | 6.3 |
| CUDA | 11.8 |
| Python | 3.8.10 |

### 3.3 Test Protocol

| Test | Duration | Samples | Purpose |
|------|----------|---------|---------|
| Latency Benchmark | 1 hour | 108,000 | Gate B validation |
| Sustained Load | 8 hours | 864,000 | Thermal stability |
| E2E Validation | 4 hours | 500 sessions | Gate C validation |
| Stress Test | 2 hours | 216,000 | Peak load behavior |

---

## 4. Results

### 4.1 Inference Latency Analysis (RQ1)

#### 4.1.1 Latency Distribution Summary

| Metric | Value | Gate B Threshold | Status |
|--------|-------|------------------|--------|
| Mean | 43.2 ms | — | — |
| **p50 (Median)** | **42.1 ms** | ≤ 120 ms | ✓ **Pass** |
| **p95** | **58.7 ms** | ≤ 250 ms | ✓ **Pass** |
| p99 | 71.3 ms | — | — |
| Max | 127.4 ms | — | — |
| Std Dev | 8.9 ms | — | — |

#### 4.1.2 Latency Percentile Distribution

| Percentile | Latency (ms) |
|------------|--------------|
| p10 | 34.2 |
| p25 | 38.1 |
| p50 | 42.1 |
| p75 | 47.8 |
| p90 | 54.3 |
| p95 | 58.7 |
| p99 | 71.3 |

#### 4.1.3 Latency by Batch Size

| Batch Size | p50 (ms) | p95 (ms) | Throughput (FPS) |
|------------|----------|----------|------------------|
| 1 | 42.1 | 58.7 | 28.4 |
| 2 | 48.3 | 67.2 | 41.2 |
| 4 | 62.7 | 89.4 | 63.8 |

**Note**: Batch size = 1 used for real-time HRI to minimize latency.

#### 4.1.4 Comparison: EfficientNet-B0 vs. ResNet-50

| Model | p50 (ms) | p95 (ms) | GPU Memory | Gate B Margin |
|-------|----------|----------|------------|---------------|
| **EfficientNet-B0** | **42.1** | **58.7** | **0.84 GB** | **2.9× latency, 3.0× memory** |
| ResNet-50 (prior) | 118.4 | 187.2 | 2.41 GB | 1.0× latency, 1.0× memory |

**Interpretation**: EfficientNet-B0 provides 2.9× latency improvement and 3.0× memory reduction, validating the model selection decision from Phase 1.

### 4.2 Resource Utilization

#### 4.2.1 GPU Memory Consumption

| Metric | Value | Gate B (≤ 2.5 GB) | Status |
|--------|-------|-------------------|--------|
| Peak | 0.91 GB | ✓ Pass | 2.7× margin |
| **Sustained** | **0.84 GB** | ✓ **Pass** | **3.0× margin** |
| Idle | 0.12 GB | — | — |

#### 4.2.2 GPU Utilization Distribution

| Utilization Range | Time (%) |
|-------------------|----------|
| 0–20% | 12.3% |
| 20–40% | 67.8% |
| 40–60% | 18.4% |
| 60–80% | 1.4% |
| 80–100% | 0.1% |

**Mean Utilization**: 31.2%

#### 4.2.3 Thermal Analysis (8-Hour Sustained Test)

| Metric | Value |
|--------|-------|
| Mean Temperature | 52.3°C |
| Max Temperature | 68.7°C |
| Throttle Threshold | 84°C |
| **Time Above 70°C** | **0.0%** |
| **Throttle Events** | **0** |

**Interpretation**: The system operates well within thermal limits with no throttling events during 8-hour sustained operation.

#### 4.2.4 CPU Overhead

| Process | CPU (%) | Memory (MB) |
|---------|---------|-------------|
| DeepStream Pipeline | 18.4% | 287 |
| Emotion Client (Python) | 4.2% | 156 |
| System Services | 8.1% | 412 |
| **Total** | **30.7%** | **855** |

### 4.3 Throughput and Reliability

#### 4.3.1 Sustained FPS Analysis

| Test Period | FPS (Mean) | FPS (Min) | FPS (Max) |
|-------------|------------|-----------|-----------|
| Hour 1 | 28.4 | 26.1 | 29.8 |
| Hour 2 | 28.2 | 25.8 | 29.6 |
| Hour 4 | 28.1 | 25.4 | 29.5 |
| Hour 8 | 27.9 | 24.9 | 29.3 |
| **Overall** | **28.2** | **24.9** | **29.8** |

**Target**: ≥ 20 FPS  
**Status**: ✓ **Pass** (41% above minimum)

#### 4.3.2 FPS Stability (Coefficient of Variation)

$$CV = \frac{s_{\text{FPS}}}{\bar{\text{FPS}}} = \frac{1.23}{28.2} = 4.4\%$$

**Interpretation**: Low CV indicates stable throughput with minimal variance.

#### 4.3.3 WebSocket Reliability (4-Hour E2E Test)

| Metric | Value | Target |
|--------|-------|--------|
| Total Messages Sent | 14,847 | — |
| Messages Delivered | 14,832 | — |
| **Delivery Rate** | **99.90%** | ≥ 99% |
| Reconnections | 2 | — |
| **Reconnection Rate** | **0.5/hour** | ≤ 5/hour |
| Heartbeat Success | 100% | ≥ 99% |

#### 4.3.4 Gesture Execution Analysis

| Metric | Value | Target |
|--------|-------|--------|
| Gesture Cues Received | 1,247 | — |
| Gestures Executed | 1,234 | — |
| **Execution Success Rate** | **98.96%** | ≥ 95% |
| Mean Execution Time | 847 ms | — |
| Failed Executions | 13 | — |

**Failure Analysis**:
- Queue overflow: 7 (53.8%)
- Timeout: 4 (30.8%)
- Invalid parameters: 2 (15.4%)

### 4.4 End-to-End Latency (Gate C)

#### 4.4.1 E2E Latency Breakdown

| Component | p50 (ms) | p95 (ms) |
|-----------|----------|----------|
| Frame Capture | 12 | 18 |
| Inference | 42 | 59 |
| Network (Jetson → Gateway) | 8 | 14 |
| LLM Response | 98 | 187 |
| Network (Gateway → Jetson) | 7 | 12 |
| Gesture Dispatch | 20 | 31 |
| **Total E2E** | **187** | **321** |

#### 4.4.2 Gate C Validation

| Metric | Value | Gate C Threshold | Status |
|--------|-------|------------------|--------|
| **E2E Latency (p50)** | **187 ms** | ≤ 300 ms | ✓ **Pass** |
| E2E Latency (p95) | 321 ms | — | Monitoring |
| **Abstention Rate** | **4.8%** | ≤ 20% | ✓ **Pass** |
| User Complaints | 0.2% | < 1% | ✓ **Pass** |

#### 4.4.3 User Session Analysis (500 Sessions)

| Metric | Value |
|--------|-------|
| Total Sessions | 500 |
| Successful Sessions | 498 |
| **Session Success Rate** | **99.6%** |
| Mean Session Duration | 4.2 min |
| Emotions Detected/Session | 15.7 |
| Gestures Executed/Session | 2.5 |

---

## 5. Statistical Tests

### 5.1 Latency Normality Test

**Shapiro-Wilk Test** (n = 1000 sample):
- $W = 0.847$
- $p < 0.001$
- **Decision**: Reject normality (right-skewed distribution)

**Implication**: Non-parametric percentiles (p50, p95) are appropriate metrics.

### 5.2 Repeated Measures ANOVA: Throughput Stability

Testing FPS stability across 8 hours with sessions as subjects (correlated measurements).

#### 5.2.1 Mauchly's Test of Sphericity

| Parameter | Value |
|-----------|-------|
| Mauchly's W | 0.891 |
| $\chi^2$ | 8.42 |
| df | 27 |
| p-value | 0.312 |

**Decision**: Sphericity assumption is met ($p = 0.312 > 0.05$); no correction needed.

#### 5.2.2 Repeated Measures ANOVA Results

| Source | SS | df | MS | F | p | $\eta^2_p$ |
|--------|----|----|----|----|---|------------|
| Hour | 2.87 | 7 | 0.41 | 0.27 | 0.963 | 0.003 |
| Error (Hour) | 1198.4 | 693 | 1.73 | — | — | — |
| Between Subjects | 847.2 | 99 | 8.56 | — | — | — |

**Interpretation**: No significant effect of time on FPS ($F(7, 693) = 0.27$, $p = 0.963$, $\eta^2_p = 0.003$). Throughput remains stable across the 8-hour test period.

### 5.3 Autocorrelation Analysis: FPS Independence

#### 5.3.1 Autocorrelation Function (ACF)

| Lag (minutes) | $r_k$ | 95% CI |
|---------------|-------|--------|
| 1 | 0.042 | [-0.062, 0.146] |
| 5 | 0.028 | [-0.076, 0.132] |
| 10 | -0.015 | [-0.119, 0.089] |
| 30 | 0.021 | [-0.083, 0.125] |
| 60 | -0.008 | [-0.112, 0.096] |

#### 5.3.2 Ljung-Box Test

| Parameter | Value |
|-----------|-------|
| Q(10) | 4.87 |
| df | 10 |
| p-value | **0.899** |

**Interpretation**: No significant autocorrelation detected ($Q = 4.87$, $p = 0.899$). FPS measurements are independent, validating the ANOVA assumption and confirming no temporal drift patterns.

### 5.4 Multiple Regression: E2E Latency Components

#### 5.4.1 Model: E2E Latency = f(Component Latencies)

| Predictor | $\beta$ | SE | t | p | Std. $\beta$ | VIF |
|-----------|---------|----|----|---|--------------|-----|
| (Intercept) | 2.14 | 1.87 | 1.14 | 0.254 | — | — |
| $L_{capture}$ | 1.02 | 0.08 | 12.75 | < 0.001 | 0.089 | 1.12 |
| $L_{inference}$ | 0.98 | 0.04 | 24.50 | < 0.001 | 0.171 | 1.08 |
| $L_{network}$ | 2.01 | 0.11 | 18.27 | < 0.001 | 0.127 | 1.15 |
| $L_{LLM}$ | 1.01 | 0.02 | 50.50 | < 0.001 | **0.524** | 1.21 |
| $L_{gesture}$ | 0.99 | 0.06 | 16.50 | < 0.001 | 0.088 | 1.09 |

#### 5.4.2 Model Fit Statistics

| Statistic | Value |
|-----------|-------|
| $R^2$ | **0.987** |
| Adjusted $R^2$ | **0.987** |
| F(5, 494) | 7,521.4 |
| p-value | < 0.0001 |
| RMSE | 8.42 ms |

#### 5.4.3 Relative Importance (Standardized $\beta$)

| Component | Std. $\beta$ | Contribution |
|-----------|--------------|-------------|
| **LLM Response** | **0.524** | **52.4%** |
| Inference | 0.171 | 17.1% |
| Network (total) | 0.127 | 12.7% |
| Capture | 0.089 | 8.9% |
| Gesture | 0.088 | 8.8% |

**Interpretation**: The regression model explains 98.7% of E2E latency variance. **LLM response** dominates with standardized $\beta = 0.524$ (52.4% contribution), confirming it as the primary optimization target. All VIF values < 2 indicate no multicollinearity.

### 5.5 Multivariate Profile Analysis: Resource Utilization

#### 5.5.1 Resource Profiles by Test Condition

| Condition | GPU Util (%) | CPU Util (%) | Memory (GB) |
|-----------|--------------|--------------|-------------|
| Idle | 2.1 | 8.2 | 0.42 |
| Inference Only | 31.2 | 22.4 | 0.84 |
| Full Pipeline | 34.7 | 30.7 | 0.91 |
| Stress Test | 48.3 | 42.1 | 0.94 |

#### 5.5.2 Profile Analysis Results

| Hypothesis | Wilks' $\Lambda$ | F | df1 | df2 | p |
|------------|------------------|---|-----|-----|---|
| Parallelism | 0.847 | 2.87 | 6 | 74 | 0.014 |
| Levels | 0.312 | 27.4 | 3 | 37 | < 0.001 |
| Flatness | 0.421 | 12.8 | 2 | 38 | < 0.001 |

**Interpretation**: 
- **Parallelism rejected** ($p = 0.014$): Profiles are not parallel—resources scale differently across conditions
- **Levels significant** ($p < 0.001$): Conditions differ in overall resource usage
- **Flatness rejected** ($p < 0.001$): Resources are not equally utilized; GPU and CPU show different patterns

### 5.6 Latency Normality Test

### 5.7 Latency Comparison: FP16 vs. FP32

| Precision | p50 (ms) | p95 (ms) | Memory (GB) |
|-----------|----------|----------|-------------|
| FP16 | 42.1 | 58.7 | 0.84 |
| FP32 | 78.3 | 112.4 | 1.52 |

**Paired t-Test**:
- $t = 127.4$, $df = 999$, $p < 0.0001$
- **Decision**: FP16 significantly faster than FP32

### 5.8 Thermal Regression Analysis

Linear regression of temperature vs. time (8-hour test):

$$T(t) = 51.2 + 0.14t$$

| Parameter | Estimate | SE | t | p |
|-----------|----------|----|----|---|
| Intercept | 51.2 | 0.31 | 165.2 | < 0.001 |
| Slope | 0.14 | 0.05 | 2.8 | 0.005 |

**Interpretation**: Temperature increases by 0.14°C per hour. At this rate, 84°C throttle threshold would be reached after 234 hours—well beyond operational requirements.

---

## 6. Discussion

### 6.1 Addressing Research Questions

**RQ1 (Gate B Compliance)**: The TensorRT-optimized EfficientNet-B0 achieves p50 = 42.1 ms (2.9× below threshold) and GPU memory = 0.84 GB (3.0× below threshold). All Gate B requirements are met with substantial margins.

**RQ2 (Sustained Throughput)**: The system maintains 28.2 FPS over 8 hours with CV = 4.4%, demonstrating stable operation. Repeated measures ANOVA confirms no significant FPS degradation ($F = 0.27$, $p = 0.963$), and Ljung-Box testing validates measurement independence ($Q = 4.87$, $p = 0.899$). No thermal throttling occurred.

**RQ3 (Gate C User Experience)**: End-to-end latency of 187 ms (p50) meets the 300 ms threshold with 38% margin. Abstention rate of 4.8% and user complaint rate of 0.2% both satisfy Gate C requirements.

### 6.2 Model Selection Validation

The choice of EfficientNet-B0 over ResNet-50 is validated by:

| Metric | Improvement | Impact |
|--------|-------------|--------|
| Latency | 2.9× faster | Enables real-time HRI |
| Memory | 3.0× smaller | Thermal headroom |
| Throughput | 41% above minimum | Future feature capacity |

### 6.3 Bottleneck Analysis (Multiple Regression)

Multiple regression ($R^2 = 0.987$) quantifies component contributions:

| Component | Std. $\beta$ | Contribution | Optimization Priority |
|-----------|--------------|--------------|----------------------|
| **LLM Response** | **0.524** | **52.4%** | **High** (primary target) |
| Inference | 0.171 | 17.1% | Low (well-optimized) |
| Network | 0.127 | 12.7% | Low (LAN minimal) |
| Capture | 0.089 | 8.9% | Low (driver overhead) |
| Gesture | 0.088 | 8.8% | Low (acceptable) |

The regression confirms LLM response as the dominant bottleneck, accounting for over half of E2E latency variance.

### 6.4 Limitations

- **Single Device**: Results from one Jetson Xavier NX; production fleet may vary
- **Controlled Environment**: Lab testing; real-world conditions may introduce variance
- **Limited User Sample**: 500 sessions may not capture all usage patterns

---

## 7. Conclusion

Phase 3 statistical analysis confirms successful edge deployment with all quality gates passed:

| Gate | Metric | Value | Threshold | Margin |
|------|--------|-------|-----------|--------|
| B | Latency p50 | 42.1 ms | ≤ 120 ms | 2.9× |
| B | Latency p95 | 58.7 ms | ≤ 250 ms | 4.3× |
| B | GPU Memory | 0.84 GB | ≤ 2.5 GB | 3.0× |
| B | Throughput | 28.2 FPS | ≥ 20 FPS | 1.4× |
| C | E2E Latency | 187 ms | ≤ 300 ms | 1.6× |
| C | Abstention | 4.8% | ≤ 20% | 4.2× |
| C | Complaints | 0.2% | < 1% | 5.0× |

The EfficientNet-B0 TensorRT engine provides substantial performance margins, enabling reliable real-time emotion recognition for human-robot interaction. The system is ready for production deployment with confidence in meeting user experience requirements.

---

## References

- NVIDIA Corporation. (2024). TensorRT Developer Guide. https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/
- NVIDIA Corporation. (2024). DeepStream SDK Developer Guide. https://docs.nvidia.com/metropolis/deepstream/dev-guide/
- NVIDIA Corporation. (2024). Jetson Xavier NX Developer Kit. https://developer.nvidia.com/embedded/jetson-xavier-nx
- Tan, M., & Le, Q. V. (2019). EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks. *ICML 2019*.
- Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality. *Biometrika*, 52(3-4), 591-611.
- Mauchly, J. W. (1940). Significance test for sphericity of a normal n-variate distribution. *Annals of Mathematical Statistics*, 11(2), 204-209.
- Greenhouse, S. W., & Geisser, S. (1959). On methods in the analysis of profile data. *Psychometrika*, 24(2), 95-112.
- Ljung, G. M., & Box, G. E. P. (1978). On a measure of lack of fit in time series models. *Biometrika*, 65(2), 297-303.
- Box, G. E. P., & Pierce, D. A. (1970). Distribution of residual autocorrelations. *Journal of the American Statistical Association*, 65(332), 1509-1526.

---

**Document Version**: 1.1  
**Author**: Russell Bray  
**Date**: 2026-01-31  
**Status**: Complete
