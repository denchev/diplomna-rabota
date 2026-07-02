from transformers import AutoProcessor, Gemma3ForConditionalGeneration
import torch

model_id = "INSAIT-Institute/BgGPT-Gemma-3-27B-IT"

processor = AutoProcessor.from_pretrained(model_id)
model = Gemma3ForConditionalGeneration.from_pretrained(
    model_id, device_map="auto"
).eval()

messages = [
    {
        "role": "user",
        "content": [{"type": "text", "text": "Кога е основан Софийският университет?"}],
    },
]

inputs = processor.apply_chat_template(
    messages, add_generation_prompt=True, tokenize=True,
    return_dict=True, return_tensors="pt"
).to(model.device, dtype=torch.bfloat16)

input_len = inputs["input_ids"].shape[-1]

with torch.inference_mode():
    generation = model.generate(**inputs, max_new_tokens=512, do_sample=True, temperature=0.2)
    generation = generation[0][input_len:]

print(processor.decode(generation, skip_special_tokens=True))