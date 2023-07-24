from PIL import Image
import io
from transformers import InstructBlipProcessor, InstructBlipForConditionalGeneration
import torch

class ImageCaptioner:

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name_or_path = "Salesforce/instructblip-vicuna-13b"
        self.model = InstructBlipForConditionalGeneration.from_pretrained(self.model_name_or_path, device_map={"":0}, load_in_4bit=True)
        self.processor = InstructBlipProcessor.from_pretrained(self.model_name_or_path)
        self.do_sample=False
        self.num_beams=5
        self.max_length=256
        self.min_length=1
        self.top_p=0.9
        self.repetition_penalty=1.5
        self.length_penalty=1.0
        self.temperature=1


    async def generate_caption(self, base64_image, prompt):
        converted_image = Image.open(io.BytesIO(base64_image))
        image = converted_image.convert('RGB')
        print(prompt)
        inputs = self.processor(images=image, text=prompt, return_tensors="pt").to(self.device, torch.float16)

        outputs = self.model.generate(
            **inputs,
            do_sample=self.do_sample,
            num_beams=self.num_beams,
            max_length=self.max_length,
            min_length=self.min_length,
            top_p=self.top_p,
            repetition_penalty=self.repetition_penalty,
            length_penalty=self.length_penalty,
            temperature=self.temperature,
        )
        


        generated_text = self.processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()
        print(generated_text)
        return generated_text


    async def caption_question(self, base64_image, prompt):
        converted_image = Image.open(io.BytesIO(base64_image))
        image = converted_image.convert('RGB')
        inputs = self.processor(images=image, text=prompt, return_tensors="pt").to(self.device, torch.float16)

        outputs = self.model.generate(
            **inputs,
            do_sample=self.do_sample,
            num_beams=self.num_beams,
            max_length=self.max_length,
            min_length=self.min_length,
            top_p=self.top_p,
            repetition_penalty=self.repetition_penalty,
            length_penalty=self.length_penalty,
            temperature=self.temperature,
        )

        generated_text = self.processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()
        print(generated_text)
        return generated_text

