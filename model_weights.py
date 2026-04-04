# Install the library
# pip install hsemotion

from hsemotion.facial_emotions import HSEmotionRecognizer

# Initializing this will trigger the download of enet_b0_8_best_vgaf
model_name = 'enet_b0_8_best_vgaf'
fer = HSEmotionRecognizer(model_name=model_name, device='cpu') 
