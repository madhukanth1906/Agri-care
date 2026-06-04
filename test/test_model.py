import torch
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import soundfile as sf
import os

# --- 1. Configuration ---
# Set the path to your locally downloaded model folder.
LOCAL_MODEL_PATH = r"G:\models\indic-parler-tts"

print(f"Attempting to load model from: {LOCAL_MODEL_PATH}")

# Check if the path exists
if not os.path.exists(LOCAL_MODEL_PATH):
    print(f"❌ ERROR: The path '{LOCAL_MODEL_PATH}' does not exist.")
    print("Please make sure you have downloaded the model to the correct location.")
else:
    try:
        # --- 2. Load the Model and Tokenizers from the Local Path ---
        # Set the device (uses your GPU if available, otherwise CPU)
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")

        # Load the main model
        model = ParlerTTSForConditionalGeneration.from_pretrained(LOCAL_MODEL_PATH).to(device)
        
        # Load the tokenizer for the prompt (the text to speak)
        prompt_tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH)
        
        # Load the tokenizer for the description (the voice style)
        description_tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH, subfolder="text_encoder")
        
        print("✅ Model and tokenizers loaded successfully from local path!")

        # --- NEW SECTION: Display Supported Languages ---
        print("\n" + "="*50)
        print("🗣️ Supported Languages by indic-parler-tts Model")
        print("="*50)
        
        officially_supported = [
            "Assamese", "Bengali", "Bodo", "Dogri", "English", "Gujarati", 
            "Hindi", "Kannada", "Konkani", "Maithili", "Malayalam", "Manipuri", 
            "Marathi", "Nepali", "Odia", "Sanskrit", "Santali", "Sindhi", 
            "Tamil", "Telugu", "Urdu"
        ]
        
        unofficially_supported = ["Chhattisgarhi", "Kashmiri", "Punjabi"]

        print("\n✅ Officially Supported (21 languages):")
        # Print in 4 columns for readability
        for i in range(0, len(officially_supported), 4):
            print("  ".join(f"{lang:<15}" for lang in officially_supported[i:i+4]))

        print("\n⚠️ Unofficially Supported (3 languages):")
        print("  " + "  ".join(f"{lang:<15}" for lang in unofficially_supported))
        print("="*50 + "\n")
        # --- END OF NEW SECTION ---

        # --- 3. Define Inputs and Generate Speech ---
        # The text you want to convert to speech
        prompt = "नमस्ते, यह एक परीक्षण है।" # (Hindi for "Hello, this is a test.")
        
        # A description of the desired voice
        description = "A high-quality, female voice speaking in Hindi with a clear tone."
        
        print(f"Generating audio for text: '{prompt}'")

        # Prepare the inputs for the model
        prompt_input_ids = prompt_tokenizer(prompt, return_tensors="pt").to(device)
        description_input_ids = description_tokenizer(description, return_tensors="pt").to(device)

        # Generate the audio waveform
        generation = model.generate(
            input_ids=description_input_ids.input_ids,
            prompt_input_ids=prompt_input_ids.input_ids
        )
        audio_arr = generation.cpu().numpy().squeeze()

        # --- 4. Save the Audio File ---
        output_filename = "test_output.wav"
        sampling_rate = model.config.sampling_rate
        sf.write(output_filename, audio_arr, sampling_rate)

        print(f"\n🎉 SUCCESS! Audio file saved as '{output_filename}' in the same directory as the script.")
        print("You can now listen to the file to verify the model is working.")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check that the model files are not corrupted and all libraries are installed correctly.")