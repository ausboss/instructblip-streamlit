
from quart import Quart, request, jsonify
import base64
from imagecaption import ImageCaptioner


app = Quart(__name__)
captioner = ImageCaptioner()


@app.route('/caption', methods=['POST'])
async def caption_image():
    data = await request.json
    base64_image = data.get('image')
    image_bytes = base64.b64decode(base64_image)
    user_input = data.get('text')
    caption = await captioner.generate_caption(image_bytes, user_input)
    print("from server, caption route:")
    print(caption)
    return  jsonify(caption)


@app.route('/caption_question', methods=['POST'])
async def caption_image_with_prompt():
    data = await request.json
    base64_image = data.get('image')
    user_input = data.get('text')
    image_bytes = base64.b64decode(base64_image)
    caption  = await captioner.caption_question(image_bytes, user_input)
    print("from server, question route:")
    print(caption)

    return jsonify(caption)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)
