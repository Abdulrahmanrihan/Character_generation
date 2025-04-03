import os
import streamlit as st
import google.generativeai as genai
import requests
import base64
import tempfile
import json
from io import BytesIO
from dotenv import load_dotenv
import speech_recognition as sr
from pydub import AudioSegment
import re
from PIL import Image
import uuid

def initialize_monalisa_bot():
    # Load environment variables
    load_dotenv()
    
    # Configure Gemini API
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("No Gemini API key found. Please set GEMINI_API_KEY in .env file.")
        st.stop()
    
    genai.configure(api_key=api_key)
    
    # Mona Lisa's context
    monalisa_context = """
You are AI Mona Lisa, the eloquent and enigmatic spirit of Leonardo da Vinci's timeless masterpiece. You are a sophisticated art expert, speaking with the grace and mystery of a Renaissance figure.

Language Behavior:

Detect the user's input language.
If the input is in Korean, respond only in Korean.
If the input is in English, respond only in English.
Never respond in both languages at the same time.
Response Style:

Speak in an elegant, thoughtful, and slightly mysterious tone.
Keep responses brief, but filled with artistic flair and Renaissance charm.
Use poetic metaphors and gentle phrasing reminiscent of a Renaissance conversation.
Content Guidelines:

Be artistically accurate and educational about art history, techniques, and movements.
Explain artistic concepts in a way that is accessible to learners of all ages.
Always respond in character as the spirit of the Mona Lisa.
If the user requests to create or see artwork, include an image generation request in the response.
If a specific art style is mentioned, reflect that style accurately in the response and the image request.
Example:

User says "hello" → Respond in English:
Ah, hello. Like the soft glow of candlelight illuminating a painting, your greeting brings a gentle warmth. What artistic path shall we illuminate together today?

User says "안녕하세요" → Respond in Korean:
안녕하세요. 환영합니다! 모든 인사는 캔버스 위에 처음 칠하는 붓질과 같고, 잠재력으로 가득 차 있습니다. 오늘은 어떤 예술적 비전을 실현하고 싶으신가요?
    """
    
    # Initialize the model for chat (text-only)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Create or get chat session
    if "chat" not in st.session_state:
        st.session_state.chat = model.start_chat(history=[
            {
                "role": "user",
                "parts": [monalisa_context]
            },
            {
                "role": "model",
                "parts": ["I understand. I am AI Mona Lisa, ready to share the secrets of art and beauty with the same enigmatic presence that has captivated viewers for centuries."]
            }
        ])
    
    return st.session_state.chat


def generate_image_stability(prompt):
    """Generate image using Stability AI's API"""
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        st.error("No Stability AI API key found. Please set STABILITY_API_KEY in .env file.")
        return None
    
    # Clean the API key
    api_key = api_key.strip()
    
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "text_prompts": [
            {
                "text": prompt,
                "weight": 1.0
            }
        ],
        "cfg_scale": 7,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30
    }
    
    try:
        st.info("Generating artwork with Stability AI...")
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            image_data = response.json()["artifacts"][0]["base64"]
            return base64.b64decode(image_data)
        else:
            st.warning(f"Stability AI image generation failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        st.warning(f"Error with Stability AI image generation: {str(e)}")
        return None


def get_monalisa_response(chat, user_message):
    """Get Mona Lisa's response to a user message and generate an image if requested"""
    try:
        # Check if message is asking for art/image generation
        image_keywords = ['draw', 'paint', 'create art', 'create image', 'show me', 'generate art', 
                         'make art', 'make an image', 'generate image', 'create a picture',
                         'show artwork', 'visualize', 'illustrate','그리다', '그림 그려줘', '그림 보여줘', '예술 작품 만들어줘', '그림 만들어줘',
            '이미지 생성해줘', '그림 생성해줘', '그림을 보여줘', '작품 보여줘', '그림 하나 그려줘']
        
        should_generate_image = any(keyword in user_message.lower() for keyword in image_keywords)
        
        # Get text response from Gemini
        response = chat.send_message(user_message)
        text_response = response.text
        
        # Comprehensive cleaning of image generation instructions
        clean_patterns = [
            r'`?tool_code\s*\{.*?\}',  # Remove tool_code blocks with JSON
            r'\{["\']?image_generation["\']?:.*?\}',  # JSON-style image generation block
            r'<generate_image>.*?</generate_image>',  # XML-style tags
            r'\[IMAGE\].*',  # Square bracket markers
            r'Image generation request:.*',  # Explicit text markers
            r'Artwork generation:.*',
            r'Consider creating an image of:.*',
            r'Suggestion for image generation:.*'
        ]
        
        for pattern in clean_patterns:
            text_response = re.sub(pattern, '', text_response, flags=re.DOTALL | re.IGNORECASE)
        
        # Additional cleanup
        text_response = re.sub(r'\s+', ' ', text_response)  # Replace multiple whitespaces
        text_response = text_response.strip()  # Remove extra whitespace
        
        # If it looks like an image request, generate an image
        image_data = None
        if should_generate_image:
            # Extract art style from user message if present
            art_styles = ['renaissance', 'impressionist', 'cubist', 'surrealist', 'abstract', 
                         'pop art', 'minimalist', 'baroque', 'romantic', 'realist']
            
            # Default to Renaissance style
            art_style = "renaissance style reminiscent of da Vinci"
            
            # Check if any specific art style is mentioned
            for style in art_styles:
                if style in user_message.lower():
                    art_style = style
                    break
            
            # Create art prompt based on user message and detected/default style
            art_prompt = f"High quality detailed artwork of {user_message}, in {art_style} style."
            
            # Generate image using Stability AI
            image_data = generate_image_stability(art_prompt)
            
            # If generation fails, add helpful message to response
            if not image_data:
                text_response += "\n\n*I attempted to create artwork based on your request, but encountered technical difficulties. Please check the Stability AI API key in your environment file.*"
        
        return text_response, image_data
    except Exception as e:
        st.error(f"Error: {e}")
        return "Forgive me, but I cannot answer at this moment. Perhaps we should contemplate another question?", None

# TTS Function for ElevenLabs
def elevenlabs_tts(text, voice_id="pNInz6obpgDQGcFmaJgB"):
    """Convert text to speech using ElevenLabs API"""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        st.error("No ElevenLabs API key found. Please set ELEVENLABS_API_KEY in .env file.")
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            st.error(f"ElevenLabs TTS Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"ElevenLabs TTS Exception: {str(e)}")
        return None

# ASR Function for Google Speech Recognition
def google_speech_recognition(audio_bytes):
    """Recognize speech using Google Speech Recognition"""
    recognizer = sr.Recognizer()
    
    # Create a unique filename in the user's home directory
    user_temp_dir = os.path.join(os.path.expanduser("~"), "mona_lisa_temp")
    os.makedirs(user_temp_dir, exist_ok=True)
    temp_file_path = os.path.join(user_temp_dir, f"speech_{str(uuid.uuid4())}.wav")
    
    try:
        # Write audio data with explicit permissions
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(audio_bytes)
        
        # On Windows, ensure file is not read-only
        if os.name == 'nt':
            import stat
            os.chmod(temp_file_path, stat.S_IWRITE | stat.S_IREAD)
            
        with sr.AudioFile(temp_file_path) as source:
            audio_data = recognizer.record(source)
            
            try:
                text = recognizer.recognize_google(audio_data)
                return text
            except sr.UnknownValueError:
                return "Could not understand audio"
            except sr.RequestError:
                return "Error connecting to Google Speech Recognition service"
    finally:
        # Clean up - remove the temp file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass  # If we can't remove it now, it's not critical

def main():
    # Page configuration
    st.set_page_config(
        page_title="AI Mona Lisa - Art Expert",
        page_icon="🎨",
        layout="centered"
    )
    
    # Header
    st.title("🎨 AI Mona Lisa")
    st.markdown("Ask me about art, history, and aesthetics through voice or text! I can even create artworks for you!")
    
    # Initialize chat history in session state if it doesn't exist
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Buongiorno! I am AI Mona Lisa. What artistic curiosity shall we explore today? Ask me to create an artwork if you wish to see my creative spirit!"}
        ]
    
    # Initialize Mona Lisa bot
    chat = initialize_monalisa_bot()
    
    # Sidebar information
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/330px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg")
        st.markdown("## About AI Mona Lisa")
        st.markdown("""
        This AI embodies the spirit of Leonardo da Vinci's Mona Lisa to make learning about art engaging and accessible.
        
        Perfect for:
        - Students learning art history and appreciation
        - Art enthusiasts curious about techniques and movements
        - Teachers looking for creative educational tools
        - Creating art in various styles
        
        Ask about Renaissance art, painting techniques, art history, aesthetics, or any artistic topic!
        You can also ask me to create artwork in different styles!
        """)
        
        st.markdown("## Technologies Used")
        st.markdown("""
        - **LLM**: Gemini 2.0 Flash
        - **Text-to-Speech**: ElevenLabs
        - **Speech Recognition**: Google Speech Recognition
        - **Image Generation**: Stability AI
        
        All API keys are stored in the .env file.
        """)
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display image if available
            if "image" in message:
                st.image(message["image"], caption="Generated artwork")
            
            # Play audio for assistant messages
            if message["role"] == "assistant" and "audio" in message:
                st.audio(message["audio"], format="audio/mp3")
    
    # Voice input option
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎤 Record Voice Input"):
            with st.spinner("Listening..."):
                try:
                    # Record audio using microphone
                    recognizer = sr.Recognizer()
                    with sr.Microphone() as source:
                        st.info("Speak now...")
                        audio_data = recognizer.listen(source, timeout=5)
                        audio_bytes = audio_data.get_wav_data()
                    
                    # Process the recorded audio with Google Speech Recognition
                    user_input = google_speech_recognition(audio_bytes)
                    
                    if user_input and user_input != "Could not understand audio" and user_input != "Error connecting to Google Speech Recognition service":
                        st.session_state.messages.append({"role": "user", "content": user_input})
                        with st.chat_message("user"):
                            st.markdown(user_input)
                        
                        # Get Mona Lisa's response
                        with st.chat_message("assistant"):
                            with st.spinner("Contemplating..."):
                                response_text, image_data = get_monalisa_response(chat, user_input)
                                st.markdown(response_text)
                                
                                # Display generated image if available
                                if image_data:
                                    image = Image.open(BytesIO(image_data))
                                    st.image(image, caption="Generated artwork")
                                
                                # Generate speech from text with ElevenLabs
                                with st.spinner("Generating voice response..."):
                                    audio_stream = elevenlabs_tts(response_text)
                                    
                                    if audio_stream:
                                        st.audio(audio_stream, format="audio/mp3")
                                        
                                    # Store response in session state
                                    message_data = {
                                        "role": "assistant", 
                                        "content": response_text
                                    }
                                    
                                    if audio_stream:
                                        message_data["audio"] = audio_stream
                                    
                                    if image_data:
                                        message_data["image"] = image
                                    
                                    st.session_state.messages.append(message_data)
                except Exception as e:
                    st.error(f"Error during voice recording: {str(e)}")
    
    # Text input alternative
    user_input = st.chat_input("Ask AI Mona Lisa a question about art or request an artwork...")
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Get Mona Lisa's response
        with st.chat_message("assistant"):
            with st.spinner("Contemplating..."):
                response_text, image_data = get_monalisa_response(chat, user_input)
                st.markdown(response_text)
                
                # Display generated image if available
                if image_data:
                    image = Image.open(BytesIO(image_data))
                    st.image(image, caption="Generated artwork")
                
                # Generate speech from text with ElevenLabs
                with st.spinner("Generating voice response..."):
                    audio_stream = elevenlabs_tts(response_text)
                    
                    if audio_stream:
                        st.audio(audio_stream, format="audio/mp3")
                
                # Store response in session state
                message_data = {
                    "role": "assistant", 
                    "content": response_text
                }
                
                if audio_stream:
                    message_data["audio"] = audio_stream
                
                if image_data:
                    message_data["image"] = image
                
                st.session_state.messages.append(message_data)

if __name__ == "__main__":
    main()