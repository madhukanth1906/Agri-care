import os
import torch
from scipy.io.wavfile import write as write_wav
from transformers import AutoTokenizer
from parler_tts import ParlerTTSForConditionalGeneration

# --- The model path we confirmed earlier ---
TTS_MODEL_PATH = r"E:\models\indic_parler_tts"

def main():
    """
    Main function to load the model and generate audio.
    """
    # Verify that the model path exists before continuing
    if not os.path.exists(TTS_MODEL_PATH):
        raise FileNotFoundError(f"❌ Model path not found. Please run the download script first.\nPath: {TTS_MODEL_PATH}")

    print(f"🧠 Loading model and tokenizer from: {TTS_MODEL_PATH}")
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Explicitly load the ParlerTTS model
        model = ParlerTTSForConditionalGeneration.from_pretrained(TTS_MODEL_PATH).to(device)
        tokenizer = AutoTokenizer.from_pretrained(TTS_MODEL_PATH)
        
        print("✅ Model and tokenizer loaded successfully!")
        
        # --- Generate Audio in Tamil ---
        print("\n🔊 Generating audio...")
        
        # The text to be spoken
        text_to_speak = "வணக்கம், உலகம் எப்படி இருக்கிறது?"

        # Prepare inputs for the model (without the prompt)
        inputs = tokenizer(text_to_speak, return_tensors="pt")
        
        # --- ADDED THIS LINE FOR DEBUGGING ---
        print("--- DEBUG: CONFIRMING SCRIPT IS UPDATED ---")
        
        inputs = {key: value.to(device) for key, value in inputs.items()}

        # Generate audio waveform
        with torch.no_grad():
            audio_waveform = model.generate(**inputs, do_sample=True, temperature=0.3).cpu().numpy().squeeze()

        # Save the audio to a file
        output_filename = "output_tamil.wav"
        sample_rate = model.config.sampling_rate
        write_wav(output_filename, rate=sample_rate, data=audio_waveform)
        
        print(f"✅ Audio saved successfully as '{output_filename}'")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main()