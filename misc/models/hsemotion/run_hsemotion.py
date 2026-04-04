from hsemotion.facial_emotions import HSEmotionRecognizer
import cv2

# load pretrained model
model_name='enet_b0_8_best_vgaf'
fer=HSEmotionRecognizer(model_name=model_name,device='cpu') 

img_path = 'affectnet_00001.jpg'   
face_img = cv2.imread(img_path)

if face_img is None:
    raise FileNotFoundError(f"Could not read image: {img_path}")

# Run emotion prediction
emotion, scores = fer.predict_emotions(face_img, logits=True)

print("Predicted emotion:", emotion)
print("Scores:", scores)
