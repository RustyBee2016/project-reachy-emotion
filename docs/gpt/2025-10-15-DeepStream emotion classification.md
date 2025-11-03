# DeepStream emotion classification

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/15/2025 20:20:30  
**Updated:** 10/15/2025 20:54:36  
**Exported:** 10/21/2025 20:36:17  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f03a4d-520c-832b-8b84-82c4f4f94a2d](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f03a4d-520c-832b-8b84-82c4f4f94a2d)  

## Prompt:
in project Reachy_Local_08.4, NVIDIA TAO Toolkit and NVIDIA DeepStream will be used to classify human emotions using the model named EmotionNet.  
While EmotionNet was trained on static images, NVIDIA documentation explains that DeepStream can be used to classify emotions represented in videos.  
Review the current documentation and explain how this achieved using DeepStream.
Begin with an overview of the process. Then provide a detailed explanation of how such a process can be implemented using the Jetson (edge) device.

## Response:
Thought for 57s

Here’s the simple truth: DeepStream turns an **image emotion classifier** (EmotionNet) into **video emotion inference** by (a) detecting faces every frame, (b) attaching a **stable object ID** with the tracker, and (c) running EmotionNet as a **secondary classifier** only when needed (first time seen or when the face box changes a lot). That “only when needed” part is what makes it work on streams without burning the GPU—DeepStream caches each object’s last classification and reuses it until there’s a meaningful change. [NVIDIA Docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvinfer.html?utm_source=chatgpt.com)

Overview — how DeepStream does it
=================================

1.  **Decode & batch:** Frames from camera/files are decoded and batched by `nvstreammux`.
2.  **Face detect (PGIE):** A primary detector finds faces each frame.
3.  **Track:** `nvtracker` gives each face a stable ID across frames.
4.  **(Optional) Landmarks:** A facial-landmarks model predicts 68 (x,y) points per face (136 values) for alignment/normalization. TAO’s EmotionNet variant expects facial landmarks as input, so this is the common pairing. [NVIDIA Docs+1](https://docs.nvidia.com/tao/tao-toolkit-archive/tao-30-2202/text/facial_landmarks_estimation/facial_landmarks_estimation.html?utm_source=chatgpt.com)
5.  **Preprocess (if landmarks used):** `nvdspreprocess` can convert ROI/meta (landmarks) into the tensor EmotionNet expects. `nvinfer` can be told to consume **tensor-from-meta** instead of raw pixels. [NVIDIA Docs+2NVIDIA Docs+2](https://docs.nvidia.com/metropolis/deepstream/6.3/dev-guide/text/DS_plugin_gst-nvdspreprocess.html?utm_source=chatgpt.com)
6.  **Emotion classify (SGIE):** EmotionNet runs as a **secondary GIE** on each tracked face, with **caching** so it doesn’t re-run every frame. (Re-infer happens on first sighting or if the face box grows by ~20%.) [NVIDIA Docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvinfer.html?utm_source=chatgpt.com)
7.  **Overlay / publish:** Draw labels or emit JSON events with the emotion, confidence, face ID, timestamps, etc.

NVIDIA’s TAO docs explicitly say TAO models (including EmotionNet) are deployable in DeepStream “out of the box,” and EmotionNet’s intended usage includes **photos and videos** with appropriate decoding/pre-processing. [NVIDIA Docs+1](https://docs.nvidia.com/tao/archive/5.3.0/text/ds_tao/deepstream_tao_integration.html?utm_source=chatgpt.com)

Jetson (edge) implementation — the practical path
=================================================

Below is a concrete, Jetson-centric setup that matches your Reachy\_Local\_08.4 spec (DeepStream 6.x + TensorRT 8.6+). It uses: Face detector → Landmarks → EmotionNet (2-class happy/sad after fine-tune) → JSON event upstream. (Your requirements already earmark **DeepStream on the Jetson** with EmotionNet TRT engines. [NVIDIA Docs+3NVIDIA Docs+3NVIDIA Docs+3](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvinfer.html?utm_source=chatgpt.com) requirements\_08.4.2)

1) Prepare the models
---------------------

*   **Face detector (PGIE):** Any TAO face detector compatible with DeepStream.
*   **Facial landmarks (SGIE-1):** TAO FPENet (68 points → 136-length vector). [NVIDIA Docs](https://docs.nvidia.com/tao/tao-toolkit-archive/tao-30-2202/text/facial_landmarks_estimation/facial_landmarks_estimation.html?utm_source=chatgpt.com)
*   **EmotionNet (SGIE-2):** Your fine-tuned 2-class (happy, sad) EmotionNet exported to ONNX or ETLT, then built as a TRT engine (FP16 recommended). TAO→DeepStream export paths are documented here. [NVIDIA Docs](https://docs.nvidia.com/tao/archive/5.3.0/text/ds_tao/deepstream_tao_integration.html?utm_source=chatgpt.com)

> Note: EmotionNet (TAO 5.3) states it “can be used… from photos and **videos**” and “takes facial landmarks as input,” which is why we include the landmarks stage and a preprocess step to form the **136×1** tensor. [NVIDIA Docs](https://docs.nvidia.com/tao/archive/5.3.0/text/model_zoo/cv_models/emotionnet.html?utm_source=chatgpt.com)

2) Install DeepStream on Jetson
-------------------------------

*   Use the JetPack-matched DeepStream (6.x on JetPack 5.x for Xavier NX). NVIDIA’s DeepStream doc covers the plugin set we’ll use: `nvstreammux`, `nvinfer`, `nvtracker`, `nvdspreprocess`, `nvosd`. [NVIDIA Docs+1](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvinfer.html?utm_source=chatgpt.com)

3) Compose the pipeline
-----------------------

**GStreamer layout (conceptual):**  
`camera → decode → nvstreammux → nvinfer (PGIE face) → nvtracker → nvinfer (SGIE-1 landmarks) → nvdspreprocess (pack 136) → nvinfer (SGIE-2 emotion) → nvosd → sink + message broker`

Key ideas the config must express:

*   `PGIE` (primary) runs per frame.
*   `nvtracker` sits after PGIE to give each face a **unique ID**.
*   `SGIE-1` landmarks sets `process-mode=2` (secondary), `operate-on-gie-id=<PGIE id>`.
*   `nvdspreprocess` groups per-object landmarks and emits a tensor;
*   `SGIE-2` EmotionNet sets `process-mode=2`, `input-tensor-from-meta=1` (consume tensors from `nvdspreprocess`), and a **labels file** with your 2 classes. [NVIDIA Developer Forums](https://forums.developer.nvidia.com/t/no-detections-on-deepstream-nvinfer-with-nvdspreprocess-plugin-add/307509?utm_source=chatgpt.com)

### Example: Emotion SGIE (nvinfer) snippet

_(This shows the DeepStream knobs you’ll actually set for EmotionNet; tweak paths/precisions as needed.)_

```
[property]
gpu-id=0
process-mode=2                  # secondary
gie-unique-id=3
operate-on-gie-id=1             # run on PGIE faces
# If you restrict to specific face class id(s):
# operate-on-class-ids=0

# EmotionNet engine
onnx-file=/opt/models/emotionnet_2cls.onnx
model-engine-file=/opt/models/emotionnet_2cls.onnx_b16_gpu0_fp16.engine
network-mode=2                  # 0=FP32,1=INT8,2=FP16
batch-size=16
# EmotionNet expects a 136x1 vector (68 landmarks * 2)
# This comes from tensor meta produced by nvdspreprocess:
input-tensor-from-meta=1

labelfile-path=/opt/models/labels_emotion_2cls.txt   # happy\nsad
# Enable tensor meta propagation if needed:
output-tensor-meta=1

[class-attrs-all]
classifier-threshold=0.50
```

Why this works for streams: **nvinfer’s secondary-with-tracker caching** means EmotionNet doesn’t rerun every frame for the same tracked face; it only re-runs when the object is new or its box changes size substantially. That’s the video magic with an image classifier. [NVIDIA Docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvinfer.html?utm_source=chatgpt.com)

### Example: Landmarks (SGIE-1) and Preprocess

```
# SGIE-1: landmarks
[property]
process-mode=2
gie-unique-id=2
operate-on-gie-id=1
# ... (model paths / dims for FPENet landmarks)

# Preprocess to pack 136 floats from landmarks meta
# (see DeepStream nvdspreprocess docs)
[preprocess]
enable=1
config-file=/opt/configs/landmarks_to_emotion_tensor.yml
```

DeepStream’s `nvdspreprocess` doc shows how to emit custom tensors per object and feed them to `nvinfer` via `input-tensor-from-meta=1`. [NVIDIA Docs+1](https://docs.nvidia.com/metropolis/deepstream/6.3/dev-guide/text/DS_plugin_gst-nvdspreprocess.html?utm_source=chatgpt.com)

### Example: App-level config

Your `deepstream_app_config.txt` (or YAML) wires these sections together with:

*   **Source:** `v4l2src` / `nvarguscamerasrc`
*   **PGIE:** face detector config
*   **Tracker:** NvDCF recommended (stable IDs help caching & temporal smoothing)
*   **SGIE-1:** landmarks (operate on faces)
*   **Preprocess:** pack landmark meta → tensor
*   **SGIE-2:** EmotionNet (consume tensor)
*   **OSD/Mux/Sink** as desired.

NVIDIA’s TAO–DeepStream integration pages outline the general export→engine→nvinfer configuration loop if you need a refresher. [NVIDIA Docs](https://docs.nvidia.com/tao/archive/5.3.0/text/ds_tao/deepstream_tao_integration.html?utm_source=chatgpt.com)

4) Temporal behavior & smoothing (what you’ll tune)
---------------------------------------------------

*   **Built-in caching** (secondary+tracker) avoids per-frame re-inference. [NVIDIA Docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvinfer.html?utm_source=chatgpt.com)
*   **Frame interval:** You can raise `interval` on PGIE (or SGIEs) to skip frames deterministically if needed.
*   **EMA / vote at app layer:** Keep a small per-object ring buffer of last N predictions and smooth (EMA or majority vote).
*   **Tracker choice:** NvDCF (with ReID) yields steadier IDs through occlusion; this improves temporal consistency. [RidgeRun Developer Wiki](https://developer.ridgerun.com/wiki/index.php/ReID_and_Target_Reassociation_using_NVIDIA_Deepstream?utm_source=chatgpt.com)

5) Emitting events to your stack
--------------------------------

On the Jetson, attach a pad-probe after SGIE-2 and emit the JSON your gateway expects (device\_id, emotion, confidence, inference\_ms, window, model\_version). Your own requirement already shows the event skeleton and the model meta key you want to publish. requirements\_08.4.2

6) Gotchas & notes
------------------

*   **EmotionNet inputs:** The TAO 5.3 card clarifies the **landmarks input**; if you fine-tune a pixel-input variant instead, you can skip the landmarks+preprocess and run EmotionNet as a standard image classifier SGIE on the face crop. (Same caching logic applies.) [NVIDIA Docs+1](https://docs.nvidia.com/tao/archive/5.3.0/text/model_zoo/cv_models/emotionnet.html?utm_source=chatgpt.com)
*   **Feeding tensors from meta:** Use `nvdspreprocess` and set `input-tensor-from-meta=1` on the consuming `nvinfer`. NVIDIA forum notes confirm the key name and behavior. [NVIDIA Developer Forums+1](https://forums.developer.nvidia.com/t/issue-report-input-tensor-meta-or-input-tensor-from-meta/202993?utm_source=chatgpt.com)
*   **Sample references:** NVIDIA’s DeepStream TAO sample repos and forum threads show the **emotion app** chaining facial landmarks with an emotion head; the command examples reference `deepstream-emotion-app` and a `sample_faciallandmarks_config.txt`. Useful for validating your wiring. [NVIDIA Developer Forums](https://forums.developer.nvidia.com/t/emotion-net-config-for-deepstream/238629)

* * *

TL;DR (what you actually do next)
---------------------------------

1.  Export TRT engines for: **face** (PGIE), **landmarks** (SGIE-1), **EmotionNet (2-class)** (SGIE-2). [NVIDIA Docs](https://docs.nvidia.com/tao/archive/5.3.0/text/ds_tao/deepstream_tao_integration.html?utm_source=chatgpt.com)
2.  Build a DeepStream 6.x pipeline on the Jetson: `PGIE(face) → tracker → SGIE-1(landmarks) → nvdspreprocess → SGIE-2(EmotionNet)`.
3.  In SGIE-2 set `process-mode=2`, `operate-on-gie-id=<PGIE>`, `input-tensor-from-meta=1`, and your **labels\_emotion\_2cls.txt**.
4.  Rely on **secondary+tracker caching** for stream efficiency; add a short **EMA** over the last ~1–2 seconds for even steadier UI. [NVIDIA Docs](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_plugin_gst-nvinfer.html?utm_source=chatgpt.com)

This keeps your **training** world (TAO with images) happily separate from your **serving** world (DeepStream on live video), while getting the temporal behavior “for free” from tracking+caching and, if needed, a tiny smoothing step at the app edge.

## Prompt:
you wrote: This keeps your training world (TAO with images) happily separate from your serving world (DeepStream on live video), while getting the temporal behavior “for free” from tracking+caching and, if needed, a tiny smoothing step at the app edge.
______________
Recall TAO Toolkit 4.0 will be used to fine-tune the model using synthetic videos generated by a video generation model (Luma AI). 
Question: 
when you wrote 'This keeps your training world (TAO with images) happily separate from your serving world (DeepStream on live video),' do you mean that TAO 4.0 will classify the training videos by randomly selecting an individual frame and classifying entire video accordingly?

## Response:
Exactly — that’s the key distinction.

When TAO 4.0 trains or fine-tunes **EmotionNet**, it’s doing _image-based classification_. Even if your dataset originates from **videos**, TAO doesn’t process temporal sequences directly (no recurrent or temporal modeling here). Instead, it expects each **training sample** to be a _single image_ (or a preprocessed tensor, e.g. landmarks + embedding) labeled with one emotion class.

So, when you train EmotionNet with synthetic **videos** from Luma AI, one of two strategies is normally used:

1.  **Frame sampling approach (most common)**  
    You extract one or more representative frames from each video — often the middle frame, or several frames uniformly sampled across the clip. Each extracted frame is treated as an independent training image with the video’s label (“happy” or “sad”).
    *   TAO sees these as separate images.
    *   If multiple frames per video are used, they act as data augmentation for that label.
2.  **Pre-averaged labeling approach**  
    You may pre-analyze the whole video (e.g., by averaging frame-level emotion scores) to assign a single dominant label, then train EmotionNet on sampled frames consistent with that dominant emotion.

Either way, **TAO 4.0 doesn’t “watch” the full video** — it just learns from stills. That’s why I said your _training world_ (TAO) remains image-based, while the _serving world_ (DeepStream) handles the continuous video domain by:

*   tracking faces across frames,
*   caching inference results per tracked object, and
*   updating the displayed emotion only when visual change is detected or over a smoothing window.

So the pipeline works like this:

*   **Training (TAO 4.0):** fine-tune on labeled frames → produce an image classifier.
*   **Inference (DeepStream):** apply that classifier repeatedly on tracked face crops from video streams → smooth or cache results to approximate temporal consistency.

In short: yes — TAO 4.0 classifies per-frame; DeepStream is what turns those frame-wise classifications into a coherent, temporally stable video-level interpretation.

## Prompt:
Assume I configure TAO to fine-tune on 10 random frames from each 5-second video.  I think you stated TAO considers each frame a separate training image.
Will I have an opportunity to verify the whether TAO classified each frame correctly?

## Response:
Yes — but it takes a little setup and expectation-management.

TAO doesn’t automatically give you **per-frame validation results** unless you build the dataset that way. By default, when you fine-tune EmotionNet, TAO only evaluates at the **image-level**, using the validation split you supply (it doesn’t know those images came from the same video).

So here’s what actually happens:

1.  **You sample 10 frames per video.**  
    Each of those 10 frames becomes its own labeled example in the training manifest. TAO randomly shuffles and batches them like any other images.
2.  **TAO trains and validates on those individual frames.**  
    The metrics you’ll see — accuracy, loss, confusion matrix — reflect _frame-level_ performance, not per-video performance.
3.  **If you want to verify correctness per frame:**
    *   After training, run **TAO evaluation** or **TAO inference** on the same 10 frames (or a held-out set).
    *   The CLI or Jupyter notebook export gives predictions with the true label vs predicted label.
    *   You can then map those results back to the originating video IDs yourself, e.g.:
        ```python
        # pseudo-example
        df.groupby("video_id").emotion_pred.value_counts(normalize=True)
        ```
    That lets you see whether most frames from a given video were classified correctly (majority vote), or if certain frames systematically fail.
4.  **If you want an easy sanity check during training:**  
    TAO supports **`visualize_model`** or **`evaluate`** commands that can dump misclassified examples. Those are still individual frames, but you can view them side-by-side with their labels to spot pattern errors (e.g., lighting, pose, blur).
5.  **For true per-video verification:**  
    You’ll need to aggregate TAO’s frame-level outputs yourself — TAO won’t automatically compute “video accuracy.”

So, yes — you _can_ verify whether TAO classified each sampled frame correctly.  
You just do it by running inference afterward and comparing predictions to the ground-truth labels you assigned in your manifest.

## Prompt:
you wrote: The CLI or Jupyter notebook export gives predictions with the true label vs predicted label....That lets you see whether most frames from a given video were classified correctly (majority vote), or if certain frames systematically fail.
___________________
Does this mean each fine-tuning video must be correctly labeled prior to fine-tuning?  Will I need to attach the (label) metadata to each video beforehand?

## Response:
Exactly.  
Every sample TAO learns from — even if it comes from a video — must have a **label** attached _before_ training. TAO doesn’t infer the emotion label on its own during fine-tuning; it only optimizes toward whatever ground-truth you’ve declared.

So in your workflow:

1.  **Before fine-tuning:**
    *   Each video should already have a known emotion class (e.g., _happy_, _sad_).
    *   When you extract frames (10 per 5-second clip, in your case), each frame inherits that same label.
    *   You record this in the **dataset manifest** — a CSV or text file TAO uses with columns like:
        ```
        path/to/frame_0001.jpg, happy
        path/to/frame_0002.jpg, happy
        ...
        ```
    *   TAO reads that manifest to know which category each training image belongs to.
2.  **During fine-tuning:**
    *   TAO treats each frame as a separate image sample.
    *   It doesn’t care that ten of them came from the same video — it only cares about the image → label mapping.
3.  **After fine-tuning:**
    *   When you evaluate or run inference, you can re-aggregate predictions back to their video of origin (via your own metadata mapping) to see whether all frames from that video agree with the original label.
    *   This is where your pre-attached metadata (the video ID and label) becomes critical for analysis and for downstream use in DeepStream.

So yes — you’ll need to attach and persist the label metadata _beforehand_, ideally at the video level first, and then propagate that label to every frame extracted from that video. TAO’s training process itself doesn’t assign or verify labels; it simply learns from whatever you provide.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)