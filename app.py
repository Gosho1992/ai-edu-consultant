import streamlit as st
import requests
from time import sleep
from PIL import Image
import io
import base64

def set_image_background_with_fallback(main_url, fallback_url=None, overlay_opacity=0.85):
    """
    Robust background image implementation with multiple fallback mechanisms
    
    Parameters:
    - main_url: Primary image URL (GitHub raw content)
    - fallback_url: Secondary image URL (optional)
    - overlay_opacity: Transparency of white overlay (0-1)
    """
    # Convert opacity to 0-255 range for CSS
    overlay_alpha = int(overlay_opacity * 255)
    
    # Check if main URL is accessible
    main_image_available = False
    try:
        response = requests.head(main_url, timeout=3)
        if response.status_code == 200:
            main_image_available = True
    except:
        pass
    
    # Use fallback if main image unavailable
    final_url = main_url if main_image_available else (fallback_url or "")
    
    # Local fallback image in base64
    local_fallback = """
    iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
    """  # 1x1 transparent pixel
    
    css = f"""
    <style>
    /* Main container styling */
    [data-testid="stAppViewContainer"] > .main {{
        background-image: url("{final_url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    /* Semi-transparent overlay */
    [data-testid="stAppViewContainer"] > .main::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(255, 255, 255, {overlay_opacity});
        z-index: 0;
    }}
    
    /* Content container */
    [data-testid="stAppViewContainer"] > .main > div {{
        background-color: transparent;
        position: relative;
        z-index: 1;
    }}
    
    /* Header area */
    header {{
        background-color: rgba(255, 255, 255, 0.9) !important;
    }}
    
    /* Fallback if both URLs fail */
    {"[data-testid=\"stAppViewContainer\"] > .main { background-image: none !important; }" if not final_url else ""}
    </style>
    
    <!-- Local fallback as base64 -->
    <style id="localFallback">
    {"[data-testid=\"stAppViewContainer\"] > .main { background-image: url('data:image/png;base64,{local_fallback}') !important; }" if not final_url else ""}
    </style>
    """
    
    # Preload the image
    preload = f"""
    <link rel="preload" href="{final_url}" as="image" onerror="document.getElementById('localFallback').innerHTML = 
    '[data-testid=\\'stAppViewContainer\\'] > .main {{ background-image: url(\\'data:image/png;base64,{local_fallback}\\') !important; }}';">
    """ if final_url else ""
    
    # Combine all elements
    st.markdown(css + preload, unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="EduBot Pro",
        page_icon="🎓",
        layout="wide"
    )
    
    # Set background with multiple fallbacks
    set_image_background_with_fallback(
        main_url="https://raw.githubusercontent.com/Gosho1992/ai-edu-consultant/main/static/backgroundimage.png",
        fallback_url="https://example.com/fallback-image.jpg",
        overlay_opacity=0.82
    )
    
    # Your app content
    st.title("🎓 EduBot Pro")
    st.write("This text will appear clearly over the background")
    
    # Test content to verify layering
    with st.expander("Test Section"):
        st.write("This should be readable")
        st.button("Sample Button")

if __name__ == "__main__":
    main()
