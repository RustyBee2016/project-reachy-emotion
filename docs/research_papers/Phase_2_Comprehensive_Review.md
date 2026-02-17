# Phase 2 Comprehensive Review: Degree, PPE, and Emotional Intelligence Extensions

**Advanced Emotional Metrics for Nuanced Human-Robot Interaction**

---

## Abstract

This paper provides a detailed examination of Phase 2 of Project Reachy, focusing on the extension of the Phase 1 three-class emotion classification system to incorporate nuanced emotional metrics that directly govern human-robot interaction (HRI). Phase 2 introduces three key enhancements: (1) **Degree of Emotion**—continuous confidence scores (0–1) representing emotion intensity, enabling the robot to modulate response strength based on prediction certainty, (2) **Primary Principles of Emotion (PPE)**—a theoretical framework based on Ekman's universal emotions that maps each detected emotion to specific LLM prompt conditioning and robot gesture selection, and (3) **Emotional Intelligence (EQ)**—the system's capacity to perceive emotions accurately, understand their meaning, respond appropriately, and critically, *self-assess* its own uncertainty. Through annotated code examples and detailed HRI scenarios, we explain how these concepts flow from model prediction through LLM response generation to physical robot behavior. This paper serves graduate students seeking to understand how probabilistic machine learning outputs translate into trustworthy, emotionally-aware robot behavior.

**Keywords:** human-robot interaction, calibration, Expected Calibration Error, Ekman emotions, emotion taxonomy, confidence estimation, LLM prompt engineering

---

## 1. Introduction

### 1.1 Motivation: Beyond Discrete Labels

Phase 1 of Project Reachy established a three-class emotion classifier distinguishing "happy," "sad," and "neutral" expressions. While effective for initial deployment, discrete classification presents limitations for sophisticated human-robot interaction:

1. **Loss of Nuance**: A person may appear "slightly sad" versus "deeply distressed"—discrete class labels obscure this critical distinction
2. **Confidence Misalignment**: A model may predict "happy" with 51% confidence versus 99% confidence—both yield the same label, yet imply vastly different certainty
3. **Downstream Decision Quality**: The Reachy robot's gesture planner and LLM interaction system benefit from knowing *how confident* the model is, not just *what* it predicts

Phase 2 addresses these limitations through three complementary extensions that preserve the efficiency of the EfficientNet-B0 backbone while enriching the output semantics.

### 1.2 Phase 2 Objectives

1. **Degree of Emotion**: Output continuous confidence scores (0.0–1.0) representing emotion intensity
2. **Primary Principles of Emotion (PPE)**: Support expansion to Ekman's eight basic emotions
3. **Emotional Intelligence (EQ) Metrics**: Implement calibration metrics ensuring confidence reliability
4. **Quality Gate Enhancement**: Enforce ECE ≤ 0.08 and Brier ≤ 0.16 thresholds before deployment

### 1.3 Theoretical Foundations

Phase 2 draws on established theory in affective computing and probabilistic machine learning:

- **Ekman's Basic Emotions** (Ekman, 1992): The six universal emotions (happiness, sadness, fear, anger, surprise, disgust) plus neutral and contempt form the PPE taxonomy
- **Calibration Theory** (Guo et al., 2017): Modern neural networks are often overconfident; calibration metrics quantify and correct this mismatch
- **Proper Scoring Rules** (Gneiting & Raftery, 2007): The Brier score is a strictly proper scoring rule, incentivizing honest probability estimates

---

## 2. Degree of Emotion: Continuous Confidence Scores

### 2.1 Conceptual Framework

Rather than outputting a single label, the EfficientNet-B0 classifier produces a probability distribution over emotion classes. The **degree of emotion** is the confidence score (softmax probability) associated with the predicted class.

```
Input Image → EfficientNet-B0 → Softmax → [P(happy)=0.87, P(sad)=0.13]
                                            ↓
                                    Prediction: happy
                                    Degree: 0.87 (87% confidence)
```

### 2.2 Implementation: Forward Pass with Confidence

The `EmotionClassifier` class returns both logits and derived probabilities:

```python
def forward(
    self, 
    x: torch.Tensor
) -> Dict[str, torch.Tensor]:
    """
    Forward pass.
    
    Args:
        x: Input tensor [B, 3, H, W]
    
    Returns:
        Dictionary with:
        - 'logits': Classification logits [B, num_classes]
        - 'features': Backbone features [B, feature_dim]
        - 'va' (optional): Valence/arousal predictions [B, 2]
    """
    # Extract features from EfficientNet-B0 backbone
    features = self.backbone(x)
    if isinstance(features, tuple):
        features = features[0]
    
    # Classification head
    x_drop = self.dropout(features)
    logits = self.fc(x_drop)
    
    output = {
        'logits': logits,
        'features': features,
    }
    
    # Optional multi-task VA prediction (Phase 2 extension)
    if self.va_head is not None:
        va = self.va_head(features)
        output['va'] = va
    
    return output
```

**Explanation**: The forward pass outputs raw logits, which downstream code converts to probabilities via softmax. This separation allows:

1. **Numerical Stability**: Cross-entropy loss operates on logits directly, avoiding log(softmax(x)) instabilities
2. **Flexibility**: Calibration techniques (e.g., temperature scaling) can be applied post-hoc to logits
3. **Multi-Task Support**: The optional `va_head` predicts continuous valence/arousal values alongside discrete emotions

### 2.3 Extracting Degree During Inference

```python
# During evaluation, convert logits to confidence scores
with torch.no_grad():
    outputs = model(images)
    logits = outputs['logits']
    
    # Convert to probabilities
    probs = torch.softmax(logits, dim=1)
    
    # Get predictions and confidence (degree)
    confidence, predictions = probs.max(dim=1)
    
    # Example: confidence=0.87, prediction=0 (happy)
    # Degree of emotion = 0.87
```

**Interpretation**: A confidence of 0.87 indicates the model assigns 87% probability to the predicted emotion. The gesture planner uses this degree to modulate response intensity—higher confidence triggers more emphatic gestures.

### 2.4 Degree in Downstream Systems

The emotion event schema transmitted to the gateway includes the degree:

```json
{
  "device_id": "reachy-mini-01",
  "ts": "2026-01-31T12:00:00Z",
  "emotion": "sad",
  "confidence": 0.82,
  "inference_ms": 38,
  "window": { "fps": 30, "size_s": 1.2, "hop_s": 0.5 },
  "meta": { "model_version": "enet_b0_8-0.9.0-trt" }
}
```

The `confidence` field (0.82) represents the degree of emotion, enabling:

- **Gesture Modulation**: Confidence maps to gesture amplitude, speed, and range
- **Abstention**: Very low confidence (<0.5) → neutral behavior, exploratory conversation
- **LLM Context**: Confidence shapes the emotional intensity of generated responses

### 2.5 Degree-Modulated Gesture Expressiveness

A truly emotionally intelligent companion robot doesn't simply execute "the sad gesture" or "the happy gesture." Instead, **the same gesture is performed with varying intensity based on the degree of emotion detected**. This is the connection between Degree and EQ—a robot that responds with the same intensity regardless of confidence appears tone-deaf and mechanical.

#### 2.5.1 The Expressiveness Spectrum

| Confidence Range | Expressiveness Level | Gesture Characteristics |
|------------------|---------------------|------------------------|
| **0.90–1.00** | Full | Maximum amplitude, normal speed, complete motion range |
| **0.75–0.89** | Moderate | 75% amplitude, slightly slower, full range |
| **0.60–0.74** | Subtle | 50% amplitude, deliberate pacing, reduced range |
| **0.40–0.59** | Minimal | 25% amplitude, slow/tentative, abbreviated motion |
| **< 0.40** | Abstain | No emotion-specific gesture; neutral posture |

#### 2.5.2 Example: The EMPATHY Gesture at Different Degrees

When Reachy detects "sad," the EMPATHY gesture involves arms moving forward in an open, supportive posture. But **how** this executes depends on confidence:

```
EMPATHY Gesture Modulation by Degree:

┌─────────────────────────────────────────────────────────────────────┐
│  CONFIDENCE: 0.95 (High)                                            │
│  ─────────────────────────────────────────────────────────────────  │
│  Arms: Extend fully forward (100% range)                            │
│  Speed: Normal (1.2 seconds)                                        │
│  Head: Tilt 15° toward user                                         │
│  Effect: "I clearly see you're hurting. I'm here for you."          │
├─────────────────────────────────────────────────────────────────────┤
│  CONFIDENCE: 0.72 (Moderate)                                        │
│  ─────────────────────────────────────────────────────────────────  │
│  Arms: Extend 75% forward                                           │
│  Speed: Slightly slower (1.5 seconds)                               │
│  Head: Tilt 10° toward user                                         │
│  Effect: "You seem a bit down. I'm paying attention."               │
├─────────────────────────────────────────────────────────────────────┤
│  CONFIDENCE: 0.55 (Low)                                             │
│  ─────────────────────────────────────────────────────────────────  │
│  Arms: Slight forward motion (40% range)                            │
│  Speed: Slow, tentative (2.0 seconds)                               │
│  Head: Minimal tilt (5°)                                            │
│  Effect: "Something might be off. I'm here if you want to talk."    │
├─────────────────────────────────────────────────────────────────────┤
│  CONFIDENCE: 0.35 (Very Low)                                        │
│  ─────────────────────────────────────────────────────────────────  │
│  Arms: Remain neutral (no emotion-specific motion)                  │
│  Speed: N/A                                                         │
│  Head: Attentive but neutral                                        │
│  Effect: "Hey, how's it going?" (neutral greeting, no assumption)   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.5.3 Why This Matters for Empathetic HRI

**The Problem with Binary Gestures:**
A robot that always executes full-intensity EMPATHY when detecting "sad" will:
1. Seem **over-dramatic** when the user is only mildly melancholy
2. Seem **presumptuous** when the model is uncertain (user might not actually be sad)
3. **Damage trust** when the confident gesture mismatches the user's actual state

**The Solution—Degree-Modulated Expression:**
By scaling gesture intensity with confidence, the robot:
1. **Matches user intensity**: Deep sadness → strong empathy; mild sadness → gentle acknowledgment
2. **Hedges uncertainty**: Low confidence → tentative response that invites correction
3. **Builds trust**: User sees that the robot responds proportionally, not mechanically

#### 2.5.4 Production Implementation

The degree-modulated gesture system is implemented in `apps/reachy/gestures/gesture_modulator.py`. Below is the core implementation:

```python
# apps/reachy/gestures/gesture_modulator.py

class ExpressivenessLevel(Enum):
    """Expressiveness tiers based on confidence."""
    FULL = "full"           # 0.90-1.00: Maximum amplitude, normal speed
    MODERATE = "moderate"   # 0.75-0.89: 75% amplitude, slightly slower
    SUBTLE = "subtle"       # 0.60-0.74: 50% amplitude, deliberate pacing
    MINIMAL = "minimal"     # 0.40-0.59: 25% amplitude, slow/tentative
    ABSTAIN = "abstain"     # < 0.40: No emotion-specific gesture


@dataclass
class ModulationParams:
    """Parameters for gesture modulation."""
    amplitude_multiplier: float  # Scale factor for joint angles (0-1)
    speed_multiplier: float      # Scale factor for duration (>1 = slower)
    head_tilt_multiplier: float  # Scale factor for head movements
    expressiveness: ExpressivenessLevel


# Confidence thresholds and their corresponding modulation parameters
CONFIDENCE_TIERS: list[Tuple[float, ModulationParams]] = [
    (0.90, ModulationParams(1.0, 1.0, 1.0, ExpressivenessLevel.FULL)),
    (0.75, ModulationParams(0.75, 1.25, 0.75, ExpressivenessLevel.MODERATE)),
    (0.60, ModulationParams(0.50, 1.5, 0.50, ExpressivenessLevel.SUBTLE)),
    (0.40, ModulationParams(0.25, 2.0, 0.25, ExpressivenessLevel.MINIMAL)),
]


def modulate_gesture(gesture: Gesture, confidence: float) -> Optional[Gesture]:
    """
    Modulate a gesture based on emotion confidence score.
    
    This is the core function for degree-modulated expressiveness.
    The same gesture is performed with varying intensity based on
    how confident the model is about the detected emotion.
    
    Args:
        gesture: Base gesture to modulate
        confidence: Model confidence score [0, 1]
        
    Returns:
        Modulated Gesture, or None if confidence is too low (abstain)
    """
    params = get_modulation_params(confidence)
    
    if params.expressiveness == ExpressivenessLevel.ABSTAIN:
        return None
    
    # Create modulated copies of arm and head sequences
    modulated_arms = [
        _modulate_arm_position(arm, params)
        for arm in gesture.arm_sequence
    ]
    
    modulated_heads = [
        _modulate_head_position(head, params)
        for head in gesture.head_sequence
    ]
    
    return Gesture(
        name=f"{gesture.name}_{params.expressiveness.value}",
        gesture_type=gesture.gesture_type,
        description=f"{gesture.description} (modulated: {params.expressiveness.value})",
        arm_sequence=modulated_arms,
        head_sequence=modulated_heads,
        total_duration=gesture.total_duration * params.speed_multiplier,
        loop=gesture.loop,
        loop_count=gesture.loop_count,
    )
```

**Key Implementation Details:**
- **Tiered Thresholds**: Five discrete tiers ensure consistent behavior across confidence ranges
- **Speed Scaling**: Lower confidence → slower execution (speed_multiplier > 1.0)
- **Abstention**: Below 0.40 confidence, the system returns `None`, signaling no emotion-specific gesture should execute
- **Immutable Design**: Original gestures are never modified; modulated copies are returned

The `GestureModulator` class provides a stateful wrapper with metrics tracking:

```python
class GestureModulator:
    """Stateful gesture modulator with observability."""
    
    def modulate(self, gesture: Gesture, confidence: float) -> Optional[Gesture]:
        """Modulate a gesture and track statistics."""
        params = get_modulation_params(confidence)
        self._last_expressiveness = params.expressiveness
        
        result = modulate_gesture(gesture, confidence)
        
        if result is None:
            self._abstain_count += 1
        else:
            self._modulation_count += 1
        
        return result
    
    @property
    def stats(self) -> dict:
        """Get modulation statistics for observability."""
        total = self._modulation_count + self._abstain_count
        return {
            "total_requests": total,
            "modulated": self._modulation_count,
            "abstained": self._abstain_count,
            "abstain_rate": self._abstain_count / total if total > 0 else 0.0,
        }
```

**Unit Test Coverage:** The implementation includes 25 unit tests in `tests/test_gesture_modulator.py` covering all confidence tiers, boundary conditions, and edge cases.

#### 2.5.5 Connection to EQ

This degree-modulated expressiveness is a core component of the robot's **Emotional Intelligence**:

| EQ Component | How Degree Modulation Implements It |
|--------------|-------------------------------------|
| **Perceive** | Confidence score reflects perception quality |
| **Understand** | Higher confidence = better understanding of emotional state |
| **Respond** | Gesture intensity matches perceived emotion intensity |
| **Self-Assess** | Low confidence → robot "knows it doesn't know" → cautious response |

**Key Insight**: A robot with high EQ doesn't just *detect* emotions—it expresses *appropriate uncertainty* through its physical behavior. This is what makes a companion robot feel empathetic rather than robotic.

---

## 3. Primary Principles of Emotion (PPE): Theoretical Foundation

### 3.1 What Are the Primary Principles of Emotion?

The **Primary Principles of Emotion (PPE)** in Project Reachy refers to the foundational framework governing how the system categorizes, interprets, and responds to human emotional states. PPE is built on three core principles:

1. **Universality**: Certain emotions are biologically innate and recognized across all human cultures
2. **Discreteness**: Emotions can be classified into distinct categories with characteristic expressions
3. **Actionability**: Each emotion category should trigger specific, appropriate robotic responses

These principles guide the system's emotion taxonomy, LLM prompt design, and gesture selection.

### 3.2 Ekman's Basic Emotions: The Scientific Foundation

Project Reachy adopts **Paul Ekman's Basic Emotion Theory** (Ekman, 1992) as the scientific foundation for PPE. Ekman's cross-cultural research demonstrated that six emotions produce universally recognized facial expressions:

| Emotion | Facial Markers | Evolutionary Function |
|---------|----------------|----------------------|
| **Happiness** | Raised cheeks, crow's feet, lip corners up | Social bonding, reward signaling |
| **Sadness** | Inner brow raise, lip corners down | Elicit support, signal loss |
| **Anger** | Lowered brows, tightened lips, hard stare | Assert dominance, signal threat |
| **Fear** | Raised brows, wide eyes, open mouth | Prepare for flight, signal danger |
| **Disgust** | Wrinkled nose, raised upper lip | Avoid contamination, reject |
| **Surprise** | Raised brows, wide eyes, dropped jaw | Orient attention, assess novelty |

Project Reachy extends this to eight classes by adding:
- **Neutral**: Baseline state (no strong emotion detected)
- **Contempt**: Asymmetric lip corner raise (indicates superiority/disdain)

### 3.3 Why Ekman Over Alternative Models?

Several emotion models exist in affective computing. The choice of Ekman's discrete model over alternatives has direct implications for HRI:

| Model | Description | Why Not Chosen for Reachy |
|-------|-------------|---------------------------|
| **Russell's Circumplex** | Emotions on valence-arousal plane | Continuous dimensions harder to map to discrete gestures |
| **Plutchik's Wheel** | 8 primary emotions with intensities | Similar to Ekman but adds complexity without clear HRI benefit |
| **Constructionist** | Emotions are culturally constructed | Undermines universal gesture design |
| **Ekman's Basic** | Discrete, universal categories | **Selected**: Clear mapping to robot behaviors |

**Key Rationale**: Discrete emotion categories enable deterministic gesture selection. When the model predicts "fear," the gesture planner can immediately select calming gestures without ambiguity.

### 3.4 PPE in Human-Robot Interaction: Emotion-to-Response Mapping

The PPE framework directly governs how Reachy responds to each detected emotion. This mapping occurs at two levels: **LLM prompt conditioning** and **gesture selection**.

#### 3.4.1 Emotion-Conditioned LLM Prompts

When an emotion is detected, the LLM receives a context-enriched prompt that shapes its response style:

| Detected Emotion | LLM Prompt Conditioning | Example Response Style |
|------------------|------------------------|------------------------|
| **Happy** | "User appears joyful. Match their energy with enthusiasm." | Celebratory, engaged, playful |
| **Sad** | "User appears sad. Respond with empathy and gentle support." | Soft, validating, supportive |
| **Anger** | "User appears frustrated. Acknowledge feelings, remain calm." | De-escalating, patient, solution-focused |
| **Fear** | "User appears anxious. Provide reassurance and stability." | Calming, grounding, protective |
| **Disgust** | "User shows aversion. Respect boundaries, offer alternatives." | Non-judgmental, redirecting |
| **Surprise** | "User is surprised. Help orient them to the situation." | Explanatory, grounding, informative |
| **Contempt** | "User may feel dismissive. Engage respectfully without defensiveness." | Neutral, professional, non-reactive |
| **Neutral** | "User is in baseline state. Proceed normally." | Standard conversational tone |

**Example Interaction Flow**:
```
1. User approaches Reachy with slumped posture, downcast eyes
2. Camera captures frame → EfficientNet-B0 predicts "sad" (confidence: 0.78)
3. Emotion event sent to gateway: {"emotion": "sad", "confidence": 0.78}
4. LLM prompt includes: "The user appears sad (78% confidence). Respond with 
   empathy. Ask how they're feeling. Offer support without being intrusive."
5. LLM generates: "Hey, I noticed you seem a bit down today. Want to talk 
   about it, or would you prefer some quiet company?"
6. Reachy speaks response with gentle tone, executes EMPATHY gesture
```

#### 3.4.2 Emotion-to-Gesture Mapping

Each PPE emotion maps to specific Reachy gestures:

| Emotion | Primary Gestures | Gesture Intent |
|---------|-----------------|----------------|
| **Happy** | CELEBRATE, THUMBS_UP, WAVE | Mirror joy, amplify positive affect |
| **Sad** | EMPATHY, COMFORT, HUG | Provide support, show understanding |
| **Anger** | LISTEN, CALM_DOWN, NOD | De-escalate, show attentiveness |
| **Fear** | REASSURE, SLOW_APPROACH, OPEN_ARMS | Reduce threat, offer safety |
| **Disgust** | STEP_BACK, NOD, NEUTRAL | Respect space, acknowledge |
| **Surprise** | WAVE, EXPLAIN, POINT | Orient attention, provide context |
| **Contempt** | NOD, NEUTRAL, LISTEN | Remain professional, non-reactive |
| **Neutral** | WAVE, NOD, IDLE | Standard greeting behaviors |

**Design Principle**: Gestures should be *congruent* with the emotion—a robot that celebrates when the user is sad would feel tone-deaf and damage trust.

### 3.5 PPE Taxonomy Configuration

The `DataConfig` class defines both the Phase 1 three-class taxonomy and the full PPE taxonomy:

```python
@dataclass
class DataConfig:
    """Dataset configuration."""
    
    # Class mapping (Phase 1 default, expandable)
    class_names: List[str] = field(default_factory=lambda: ["happy", "sad", "neutral"])
    
    # For multi-class expansion (PPE)
    full_class_names: List[str] = field(default_factory=lambda: [
        "neutral", "happy", "sad", "anger", "fear", "disgust", "surprise", "contempt"
    ])
```

**Explanation**: The configuration separates the Phase 1 class set (`class_names`) from the full taxonomy (`full_class_names`). Training scripts select the appropriate mapping:

- **Phase 1 Mode**: `class_names = ["happy", "sad", "neutral"]` → 3-class classification (Phase 1)
- **Multi-Class Mode**: `class_names = full_class_names` → 8-class classification (Phase 2+)

### 3.3 Multi-Class Configuration

The codebase includes a pre-configured multi-class setup:

```python
# Configuration for 8-class emotion classification
MULTICLASS_CONFIG = TrainingConfig(
    model=ModelConfig(
        num_classes=8,
        use_multi_task=True,  # Enable valence/arousal head
    ),
    data=DataConfig(
        class_names=["neutral", "happy", "sad", "anger", "fear", "disgust", "surprise", "contempt"],
    ),
)
```

**Explanation**: 

1. **`num_classes=8`**: The classification head outputs 8 logits instead of 2
2. **`use_multi_task=True`**: Enables the auxiliary valence/arousal regression head
3. **Class Balance**: Training requires balanced sampling across all 8 classes to prevent majority class dominance

### 3.4 Multi-Task Learning: Emotions + Valence/Arousal

The optional `va_head` enables simultaneous prediction of:

- **Discrete Emotion**: Categorical label (one of 8 classes)
- **Valence**: Continuous value [-1, 1] indicating positive/negative affect
- **Arousal**: Continuous value [-1, 1] indicating activation level

```python
# Optional multi-task head for valence/arousal regression
if use_multi_task:
    self.va_head = nn.Sequential(
        nn.Dropout(p=dropout_rate),
        nn.Linear(self.feature_dim, 64),
        nn.ReLU(inplace=True),
        nn.Linear(64, 2),  # valence, arousal
        nn.Tanh(),  # VA typically in [-1, 1]
    )
else:
    self.va_head = None
```

**Explanation**: Multi-task learning provides:

1. **Richer Representations**: The shared backbone learns features useful for both tasks
2. **Dimensional Emotion Model**: VA coordinates complement discrete labels (e.g., "happy" = high valence, moderate arousal)
3. **Regularization Effect**: Multi-task objectives can improve generalization

---

## 4. Emotional Intelligence (EQ): Trustworthy Emotion-Aware Systems

### 4.1 What Is Emotional Intelligence in a Robot System?

In human psychology, **Emotional Intelligence (EQ)** refers to the ability to perceive, understand, manage, and respond appropriately to emotions—both one's own and others' (Salovey & Mayer, 1990). For Project Reachy, we adapt this concept to define **Machine Emotional Intelligence**: the system's capacity to:

1. **Perceive**: Accurately detect human emotional states from facial expressions
2. **Understand**: Correctly interpret the meaning and intensity of detected emotions
3. **Respond**: Generate contextually appropriate verbal and physical responses
4. **Self-Assess**: Know when predictions are uncertain and adjust behavior accordingly

The fourth component—**self-assessment**—is what distinguishes a truly intelligent emotional system from a naive classifier. A system with high EQ doesn't just predict emotions; it *knows how confident it should be* in those predictions.

### 4.2 Why EQ Matters for Human-Robot Interaction

Consider two scenarios where Reachy detects "sad" with different confidence levels:

**Scenario A: High Confidence (95%)**
```
User: [clearly crying, slumped posture, covering face]
Model: "sad" (confidence: 0.95)
Reachy: Immediately offers empathetic response, executes COMFORT gesture
Result: Appropriate, timely support
```

**Scenario B: Low Confidence (55%)**
```
User: [ambiguous expression, slightly downturned mouth, could be tired]
Model: "sad" (confidence: 0.55)
Reachy: ??? 
```

In Scenario B, a system without EQ would respond identically to Scenario A—potentially offering unsolicited emotional support to someone who is merely tired, creating an awkward interaction. A system *with* EQ recognizes its uncertainty and adapts:

```
Reachy (with EQ): "Hey there! How's your day going?" 
[Neutral greeting, allows user to self-disclose if needed]
```

### 4.3 The Three Pillars of Machine EQ

Project Reachy implements EQ through three measurable pillars:

| Pillar | Definition | Metric | Gate A Threshold |
|--------|------------|--------|------------------|
| **Accuracy** | Correct emotion predictions | Macro F1 | ≥ 0.84 |
| **Calibration** | Confidence matches reality | ECE | ≤ 0.08 |
| **Reliability** | Consistent probabilistic quality | Brier Score | ≤ 0.16 |

**The EQ Equation**: A system has high EQ when it is *accurate* (predicts correctly), *calibrated* (confidence reflects true accuracy), and *reliable* (probability estimates are meaningful).

### 4.4 EQ in the HRI Pipeline

EQ metrics directly influence Reachy's behavior at runtime:

```
┌─────────────────────────────────────────────────────────────────┐
│                    EQ-AWARE HRI PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. PERCEPTION (EfficientNet-B0)                               │
│     Input: Video frame                                          │
│     Output: Emotion probabilities [0.05, 0.85, 0.03, ...]      │
│                                                                 │
│  2. EQ SELF-ASSESSMENT                                         │
│     confidence = max(probabilities) = 0.85                     │
│     IF confidence < 0.60: flag as "uncertain"                  │
│     IF confidence < 0.40: abstain from emotion-specific action │
│                                                                 │
│  3. RESPONSE MODULATION (based on EQ)                          │
│     HIGH confidence (≥0.80): Full emotional response           │
│       → LLM: "User is clearly sad. Respond empathetically."    │
│       → Gesture: Execute EMPATHY with full amplitude           │
│                                                                 │
│     MEDIUM confidence (0.60-0.80): Tempered response           │
│       → LLM: "User may be sad (moderate confidence)."          │
│       → Gesture: Execute EMPATHY with reduced amplitude        │
│                                                                 │
│     LOW confidence (<0.60): Neutral/exploratory response       │
│       → LLM: "User's emotional state is unclear."              │
│       → Gesture: NEUTRAL, allow user to self-disclose          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.5 The Calibration Problem: Why Raw Confidence Fails

A well-calibrated classifier satisfies the property: when it predicts class *k* with confidence *p*, it should be correct approximately *p* fraction of the time. Modern neural networks, including EfficientNet, are often **overconfident**—they assign high probabilities to predictions even when wrong.

**Example of Miscalibration**:
- Model predicts "happy" with 90% confidence across 100 samples
- Actual accuracy on those samples: only 70%
- The model is overconfident by 20 percentage points

**HRI Consequence**: An overconfident model triggers high-intensity emotional responses when it shouldn't, leading to awkward or inappropriate robot behavior. This damages user trust.

### 4.6 Expected Calibration Error (ECE)

ECE measures the average gap between confidence and accuracy across probability bins.

**Mathematical Definition**:

$$ECE = \sum_{m=1}^{M} \frac{|B_m|}{n} |acc(B_m) - conf(B_m)|$$

Where:
- *M* = number of bins (typically 10)
- *B_m* = set of samples in bin *m*
- *acc(B_m)* = accuracy of predictions in bin *m*
- *conf(B_m)* = average confidence in bin *m*
- *n* = total number of samples

**Implementation**:

```python
def expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Compute Expected Calibration Error (ECE).
    
    ECE measures how well predicted probabilities match actual accuracy.
    Lower is better. Gate A requires ECE ≤ 0.08.
    
    Args:
        y_true: Ground truth labels [N]
        y_prob: Predicted probabilities [N, C]
        n_bins: Number of calibration bins
    
    Returns:
        ECE value in [0, 1]
    """
    confidences = np.max(y_prob, axis=1)
    predictions = np.argmax(y_prob, axis=1)
    accuracies = (predictions == y_true).astype(float)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    
    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = in_bin.mean()
        
        if prop_in_bin > 0:
            avg_confidence = confidences[in_bin].mean()
            avg_accuracy = accuracies[in_bin].mean()
            ece += np.abs(avg_accuracy - avg_confidence) * prop_in_bin
    
    return float(ece)
```

**Explanation**:

1. **Binning**: Samples are grouped by confidence level into 10 bins ([0, 0.1], (0.1, 0.2], ..., (0.9, 1.0])
2. **Per-Bin Gap**: For each bin, compute |accuracy - confidence|
3. **Weighted Average**: Gaps are weighted by bin proportion to form ECE

**Interpretation**: ECE = 0.05 means, on average, the model's confidence differs from its actual accuracy by 5 percentage points—a well-calibrated model.

### 4.7 Brier Score

The Brier score is the mean squared error between predicted probabilities and one-hot encoded true labels.

**Mathematical Definition**:

$$Brier = \frac{1}{N} \sum_{i=1}^{N} \sum_{k=1}^{K} (p_{ik} - y_{ik})^2$$

Where:
- *p_ik* = predicted probability for sample *i*, class *k*
- *y_ik* = 1 if true label is *k*, else 0

**Implementation**:

```python
def brier_score(
    y_true: np.ndarray,
    y_prob: np.ndarray,
) -> float:
    """
    Compute Brier score (mean squared error of probabilities).
    
    Lower is better. Gate A requires Brier ≤ 0.16.
    
    Args:
        y_true: Ground truth labels [N]
        y_prob: Predicted probabilities [N, C]
    
    Returns:
        Brier score
    """
    n_classes = y_prob.shape[1]
    
    # One-hot encode true labels
    y_true_onehot = np.eye(n_classes)[y_true]
    
    # Mean squared error
    brier = np.mean(np.sum((y_prob - y_true_onehot) ** 2, axis=1))
    
    return float(brier)
```

**Explanation**:

1. **One-Hot Encoding**: True labels are converted to indicator vectors (e.g., label 1 → [0, 1, 0] for 3-class)
2. **Squared Error**: Each probability's deviation from the target is squared and summed
3. **Averaging**: The sum is averaged across all samples

**Interpretation**: 
- Brier = 0.0: Perfect predictions (all probabilities match true labels exactly)
- Brier ≈ 0.67: Uniform random guessing for 3-class classification
- Gate A requires Brier ≤ 0.16, indicating better-than-random calibrated predictions

### 4.8 Maximum Calibration Error (MCE)

MCE captures the worst-case calibration gap across all bins:

```python
def maximum_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Compute Maximum Calibration Error (MCE).
    
    MCE is the maximum gap between confidence and accuracy across bins.
    
    Args:
        y_true: Ground truth labels
        y_prob: Predicted probabilities
        n_bins: Number of calibration bins
    
    Returns:
        MCE value
    """
    confidences = np.max(y_prob, axis=1)
    predictions = np.argmax(y_prob, axis=1)
    accuracies = (predictions == y_true).astype(float)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    max_gap = 0.0
    
    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        
        if in_bin.sum() > 0:
            avg_confidence = confidences[in_bin].mean()
            avg_accuracy = accuracies[in_bin].mean()
            gap = np.abs(avg_accuracy - avg_confidence)
            max_gap = max(max_gap, gap)
    
    return float(max_gap)
```

**Explanation**: While ECE measures average calibration, MCE identifies the worst bin. A model with low ECE but high MCE may be well-calibrated overall but severely miscalibrated in specific confidence ranges.

---

## 5. Quality Gates: Enforcing Calibration Standards

### 5.1 Gate A Configuration

The training configuration embeds quality gate thresholds:

```python
@dataclass
class TrainingConfig:
    """Complete training configuration."""
    
    # Quality gates (from requirements_08.4.2.md)
    gate_a_min_f1_macro: float = 0.84
    gate_a_min_per_class_f1: float = 0.75
    gate_a_min_balanced_accuracy: float = 0.85
    gate_a_max_ece: float = 0.08
    gate_a_max_brier: float = 0.16
    
    gate_b_max_latency_p50_ms: float = 120.0
    gate_b_max_latency_p95_ms: float = 250.0
    gate_b_max_gpu_memory_gb: float = 2.5
    gate_b_min_f1_macro: float = 0.80
    gate_b_min_per_class_f1: float = 0.72
```

**Explanation**: Gate A (offline validation) enforces both classification quality (F1, accuracy) and calibration quality (ECE, Brier). A model must satisfy all thresholds before proceeding to Gate B (on-device validation).

### 5.2 Gate Checking Implementation

```python
def _check_quality_gates(self, metrics: Dict[str, float]) -> Dict[str, bool]:
    """
    Check quality gates from requirements_08.4.2.md.
    
    Args:
        metrics: Validation metrics
    
    Returns:
        Dictionary of gate results
    """
    results = {}
    
    # Gate A: Offline validation
    f1_macro = metrics.get('f1_macro', 0.0)
    f1_per_class = [metrics.get(f'f1_class_{i}', 0.0) 
                   for i in range(self.config.model.num_classes)]
    balanced_acc = metrics.get('balanced_accuracy', 0.0)
    ece = metrics.get('ece', 1.0)
    brier = metrics.get('brier', 1.0)
    
    gate_a_passed = (
        f1_macro >= self.config.gate_a_min_f1_macro and
        all(f1 >= self.config.gate_a_min_per_class_f1 for f1 in f1_per_class) and
        balanced_acc >= self.config.gate_a_min_balanced_accuracy and
        ece <= self.config.gate_a_max_ece and
        brier <= self.config.gate_a_max_brier
    )
    
    results['gate_a'] = gate_a_passed
    results['gate_a_details'] = {
        'f1_macro': f1_macro,
        'f1_per_class': f1_per_class,
        'balanced_accuracy': balanced_acc,
        'ece': ece,
        'brier': brier,
    }
    
    logger.info(f"Gate A: {'PASSED' if gate_a_passed else 'FAILED'}")
    logger.info(f"  F1 macro: {f1_macro:.4f} (req: {self.config.gate_a_min_f1_macro})")
    logger.info(f"  Balanced acc: {balanced_acc:.4f} (req: {self.config.gate_a_min_balanced_accuracy})")
    logger.info(f"  ECE: {ece:.4f} (req: ≤{self.config.gate_a_max_ece})")
    
    return results
```

**Explanation**: The gate check is a conjunction (AND) of all requirements:

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Macro F1 | ≥ 0.84 | Overall classification quality |
| Per-class F1 | ≥ 0.75 | No class collapse (prevents majority class bias) |
| Balanced Accuracy | ≥ 0.85 | Handles class imbalance |
| ECE | ≤ 0.08 | Confidence calibration |
| Brier | ≤ 0.16 | Probabilistic accuracy |

### 5.3 Evaluation Report Generation

The evaluation module generates human-readable reports:

```python
def generate_report(
    results: Dict[str, any],
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a human-readable evaluation report.
    
    Args:
        results: Evaluation results dictionary
        output_path: Optional path to save report
    
    Returns:
        Report string
    """
    lines = [
        "=" * 60,
        "EMOTION CLASSIFIER EVALUATION REPORT",
        "=" * 60,
        "",
        "CLASSIFICATION METRICS",
        "-" * 40,
        f"Accuracy:          {results.get('accuracy', 0):.4f}",
        f"Balanced Accuracy: {results.get('balanced_accuracy', 0):.4f}",
        f"F1 Macro:          {results.get('f1_macro', 0):.4f}",
        f"Precision Macro:   {results.get('precision_macro', 0):.4f}",
        f"Recall Macro:      {results.get('recall_macro', 0):.4f}",
        "",
        "CALIBRATION METRICS",
        "-" * 40,
        f"ECE:   {results.get('ece', 0):.4f} (target: ≤0.08)",
        f"MCE:   {results.get('mce', 0):.4f}",
        f"Brier: {results.get('brier', 0):.4f} (target: ≤0.16)",
        "",
        "QUALITY GATE STATUS",
        "-" * 40,
    ]
    
    # Gate A check
    gate_a_passed = (
        results.get('f1_macro', 0) >= 0.84 and
        results.get('balanced_accuracy', 0) >= 0.85 and
        results.get('ece', 1) <= 0.08 and
        results.get('brier', 1) <= 0.16
    )
    
    lines.append(f"Gate A: {'PASSED ✓' if gate_a_passed else 'FAILED ✗'}")
    
    return "\n".join(lines)
```

**Explanation**: The report consolidates all metrics in a single view, enabling rapid assessment of model quality. The Gate A status provides an immediate pass/fail indicator.

---

## 6. Complete Evaluation Pipeline

### 6.1 Computing All Metrics

The `compute_calibration_metrics` function aggregates ECE, Brier, and MCE:

```python
def compute_calibration_metrics(
    y_true: List[int],
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> Dict[str, float]:
    """
    Compute calibration metrics.
    
    Args:
        y_true: Ground truth labels
        y_prob: Predicted probabilities [N, C]
        n_bins: Number of bins for ECE
    
    Returns:
        Dictionary with ECE and Brier score
    """
    y_true = np.array(y_true)
    y_prob = np.array(y_prob)
    
    metrics = {}
    
    # Expected Calibration Error (ECE)
    metrics['ece'] = expected_calibration_error(y_true, y_prob, n_bins)
    
    # Brier score
    metrics['brier'] = brier_score(y_true, y_prob)
    
    # Maximum Calibration Error (MCE)
    metrics['mce'] = maximum_calibration_error(y_true, y_prob, n_bins)
    
    return metrics
```

### 6.2 Full Model Evaluation

The `evaluate_model` function runs inference and computes all metrics:

```python
def evaluate_model(
    model,
    dataloader,
    device: str = 'cuda',
    class_names: Optional[List[str]] = None,
) -> Dict[str, any]:
    """
    Evaluate a model on a dataset.
    
    Args:
        model: PyTorch model
        dataloader: DataLoader for evaluation
        device: Device to run on
        class_names: Class names
    
    Returns:
        Complete evaluation results
    """
    import torch
    
    model.eval()
    
    all_preds = []
    all_labels = []
    all_probs = []
    
    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(device)
            
            outputs = model(images)
            if isinstance(outputs, dict):
                logits = outputs['logits']
            else:
                logits = outputs
            
            probs = torch.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())
    
    # Compute all metrics
    results = compute_metrics(all_labels, all_preds, class_names)
    results.update(compute_calibration_metrics(all_labels, np.array(all_probs)))
    results['confusion'] = compute_confusion_matrix(all_labels, all_preds, class_names)
    
    return results
```

**Explanation**: The evaluation pipeline:

1. **Collects Predictions**: Iterates through the dataloader, storing predictions, labels, and probabilities
2. **Computes Classification Metrics**: Accuracy, F1, precision, recall via `compute_metrics`
3. **Computes Calibration Metrics**: ECE, Brier, MCE via `compute_calibration_metrics`
4. **Generates Confusion Matrix**: Per-class true/false positives/negatives

---

## 7. Calibration Improvement Techniques

### 7.1 Label Smoothing

The training configuration includes label smoothing as a built-in calibration technique:

```python
# Loss function with label smoothing
self.criterion = nn.CrossEntropyLoss(
    label_smoothing=config.label_smoothing  # default: 0.1
)
```

**Explanation**: Label smoothing replaces hard targets (e.g., [0, 1]) with soft targets (e.g., [0.05, 0.95]). This:

1. **Prevents Overconfidence**: The model cannot achieve zero loss even with perfect predictions
2. **Improves Calibration**: Softened targets encourage probability outputs closer to actual uncertainty
3. **Regularization**: Acts as implicit regularization, reducing overfitting

### 7.2 Temperature Scaling (Post-hoc)

While not implemented in the current codebase, temperature scaling is a standard post-hoc calibration technique:

```python
# Conceptual implementation of temperature scaling
def calibrate_with_temperature(logits: torch.Tensor, temperature: float = 1.5) -> torch.Tensor:
    """
    Apply temperature scaling to logits.
    
    Higher temperature → softer (less confident) probabilities
    Lower temperature → sharper (more confident) probabilities
    
    Args:
        logits: Raw model outputs [B, C]
        temperature: Scaling factor (>1 reduces confidence)
    
    Returns:
        Calibrated probabilities
    """
    scaled_logits = logits / temperature
    return torch.softmax(scaled_logits, dim=1)
```

**Future Enhancement**: Temperature can be learned on a validation set by minimizing negative log-likelihood.

---

## 8. Conclusion

Phase 2 of Project Reachy transforms a 3-class emotion classifier into a sophisticated emotional intelligence system that governs human-robot interaction. The three core concepts—Degree, PPE, and EQ—work together:

### 8.1 How It All Connects

```
┌─────────────────────────────────────────────────────────────────┐
│  USER shows facial expression                                   │
│                        ↓                                        │
│  EfficientNet-B0 predicts: "sad" (confidence: 0.82)            │
│                        ↓                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ PPE: "sad" → Ekman category requiring empathetic response   │  │
│  │ DEGREE: 0.82 → High confidence, full emotional response     │  │
│  │ EQ: Model is calibrated (ECE ≤0.08), confidence is reliable │  │
│  └───────────────────────────────────────────────────────────┘  │
│                        ↓                                        │
│  LLM receives: "User appears sad (82% confidence). Respond     │
│                 with empathy. Offer support."                  │
│                        ↓                                        │
│  LLM generates: "I can see you're having a tough time. Want    │
│                  to talk about it?"                            │
│                        ↓                                        │
│  REACHY executes EMPATHY gesture + speaks response             │
│                        ↓                                        │
│  USER feels understood → Trust in robot increases              │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Summary of Core Concepts

| Concept | Definition | HRI Impact |
|---------|------------|------------|
| **Degree** | Confidence score (0–1) for predicted emotion | Modulates response intensity; low confidence → cautious behavior |
| **PPE** | 8-class Ekman taxonomy with emotion-to-response mappings | Determines *what* response (empathy vs. celebration vs. calming) |
| **EQ** | Accuracy + Calibration + Self-Assessment | Ensures confidence is trustworthy; prevents overconfident errors |

### 8.3 Key Takeaways for Graduate Students

1. **PPE Enables Actionable Responses**: Discrete emotion categories map directly to robot behaviors—this is why Ekman's model was chosen over continuous dimensional models
2. **Degree Enables Nuance**: The same emotion at different confidence levels triggers different response intensities
3. **EQ Enables Trust**: A calibrated model knows when it doesn't know—and a robot that admits uncertainty is more trustworthy than one that acts overconfidently
4. **The Triad Is Inseparable**: PPE without EQ produces confident but unreliable responses; EQ without PPE produces calibrated but generic responses; both need Degree to modulate appropriately

---

## References

Ekman, P. (1992). An argument for basic emotions. *Cognition & Emotion*, 6(3-4), 169-200.

Gneiting, T., & Raftery, A. E. (2007). Strictly proper scoring rules, prediction, and estimation. *Journal of the American Statistical Association*, 102(477), 359-378.

Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. In *Proceedings of the International Conference on Machine Learning* (pp. 1321-1330).

Naeini, M. P., Cooper, G., & Hauskrecht, M. (2015). Obtaining well calibrated probabilities using Bayesian binning. In *Proceedings of the AAAI Conference on Artificial Intelligence* (pp. 2901-2907).

Salovey, P., & Mayer, J. D. (1990). Emotional intelligence. *Imagination, Cognition and Personality*, 9(3), 185-211.

Savchenko, A. V. (2021). Facial expression and attributes recognition based on multi-task learning of lightweight neural networks. In *Proceedings of the IEEE International Symposium on Intelligent Systems and Informatics* (pp. 119-124).

---

**Document Information**

| Field | Value |
|-------|-------|
| Paper Number | 3 of 7 |
| Title | Phase 2 Comprehensive Review: Degree, PPE, and EQ |
| Version | 1.2 |
| Date | January 31, 2026 |
| Author | Russell Bray |
| Project | Reachy_EQ_PPE_Degree_Mini_01 |

---

*This paper is part of a seven-paper series documenting Project Reachy. Paper 4 covers Phase 3 (robotics integration), and Paper 6 provides statistical analysis of Phase 2 metrics.*
