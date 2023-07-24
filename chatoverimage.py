import streamlit as st
from PIL import Image
import requests
import base64
from imagecaption import ImageCaptioner
import asyncio

# Function to get bot response
async def get_bot_response(user_prompt, image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    print(user_prompt)
    raw_response = requests.post('http://192.168.1.144:5004/caption_question', json={'image': base64_image, 'text': user_prompt})
    response = raw_response.json()
    print(raw_response.status_code)
    print(raw_response.text)
    response = raw_response.json()

    print(response)
    return response


async def get_bot_caption(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    question = "What would a caption for this image be?"
    raw_response = requests.post('http://192.168.1.144:5004/caption', json={'image': base64_image, 'text': question})
    response = raw_response.json()
    print(response)
    return response


async def main():
    uploaded_file = st.sidebar.file_uploader("Choose an image file", type=['png', 'jpg', 'jpeg'], key="image_uploader")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if uploaded_file is not None:
        image_bytes = uploaded_file.read()

        with st.sidebar:
            add_image = st.image(uploaded_file, caption="uploaded pic")
            print(add_image)

        if prompt := st.chat_input("input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                print(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                for response in await get_bot_response(prompt, image_bytes):
                    full_response += response
                    message_placeholder.markdown(full_response + "▌")

                message_placeholder.markdown(full_response.replace("'''", "```"))
            st.session_state.messages.append({"role": "assistant", "content": full_response.replace("'''", "```")})


if __name__ == "__main__":
    asyncio.run(main())
