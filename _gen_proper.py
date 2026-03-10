#!/usr/bin/env python3
"""過去の実績ある設定で画像生成（ComfyUI直接）"""
import sys, json, time, random, requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

model = 'cyberrealisticPony_v150 (1).safetensors'
loras = [
    ('Not Artists Styles for Pony Diffusion V6 XL.safetensors', 0.86),
    ('sdxl_lightning_2step_lora.safetensors', 0.76),
]

anatomy = (
    'perfect anatomy, correct anatomy, accurate anatomy, '
    'proper proportions, well-proportioned body, '
    'correct hands, perfect hands, detailed hands, '
    'correct feet, perfect feet, detailed feet, '
    'natural joints, correct joints, symmetrical body, balanced body, '
    'realistic body structure, accurate body structure'
)
quality = (
    'masterpiece, best quality, ultra detailed, 8k, '
    'cinematic lighting, depth of field, soft skin, beautiful anatomy'
)
character = 'Japanese, Japanese woman, 1girl, solo'
content = (
    'seductive pose, slim body, D cup, pale skin, '
    'nipples, nude, naked woman, lingerie pulled aside, '
    'lying on bed, spread legs, bedroom eyes, '
    'pleasure, wet, horny, mischievous expression'
)
trailing = 'realistic, photorealistic, high quality, detailed, sharp focus, 8k uhd'

prompt = f'{anatomy}, {quality}, {character}, {content}, perfect proportions, correct anatomy, beautiful, gorgeous, stunning, soft lighting, {trailing}'

neg = (
    'bad anatomy, bad proportions, bad body structure, deformed body, malformed limbs, '
    'incorrect anatomy, wrong anatomy, broken anatomy, distorted anatomy, '
    'bad hands, missing fingers, extra fingers, fused fingers, too many fingers, fewer digits, missing digits, '
    'bad feet, malformed feet, extra feet, missing feet, '
    'bad arms, malformed arms, extra arms, missing arms, '
    'bad legs, malformed legs, extra legs, missing legs, '
    'wrong hands, wrong feet, wrong limbs, disconnected limbs, floating limbs, '
    'bad joints, malformed joints, impossible joints, '
    'deformed face, bad face, asymmetric eyes, '
    'lowres, worst quality, low quality, normal quality, '
    'jpeg artifacts, signature, watermark, username, blurry, '
    'text, error, cropped, duplicate, ugly, deformed, '
    'poorly drawn, bad body, out of frame, extra limbs, '
    'disfigured, mutation, mutated, mutilated, bad art, bad structure'
)

seed = random.randint(0, 2**32 - 1)

workflow = {
    '1': {'inputs': {'ckpt_name': model}, 'class_type': 'CheckpointLoaderSimple'},
}

current_model = ['1', 0]
current_clip = ['1', 1]
nid = 8
for lora_name, strength in loras:
    workflow[str(nid)] = {
        'inputs': {
            'lora_name': lora_name,
            'strength_model': strength,
            'strength_clip': strength,
            'model': current_model,
            'clip': current_clip
        },
        'class_type': 'LoraLoader'
    }
    current_model = [str(nid), 0]
    current_clip = [str(nid), 1]
    nid += 1

workflow.update({
    '2': {'inputs': {'text': prompt, 'clip': current_clip}, 'class_type': 'CLIPTextEncode'},
    '3': {'inputs': {'text': neg, 'clip': current_clip}, 'class_type': 'CLIPTextEncode'},
    '4': {
        'inputs': {
            'seed': seed, 'steps': 50, 'cfg': 8.0,
            'sampler_name': 'euler_ancestral', 'scheduler': 'karras',
            'denoise': 1.0,
            'model': current_model,
            'positive': ['2', 0], 'negative': ['3', 0],
            'latent_image': ['5', 0]
        },
        'class_type': 'KSampler'
    },
    '5': {'inputs': {'width': 1024, 'height': 1024, 'batch_size': 1}, 'class_type': 'EmptyLatentImage'},
    '6': {'inputs': {'samples': ['4', 0], 'vae': ['1', 2]}, 'class_type': 'VAEDecode'},
    '7': {'inputs': {'filename_prefix': 'ComfyUI', 'images': ['6', 0]}, 'class_type': 'SaveImage'},
})

print(f'Model: {model}')
print(f'LoRAs: {[l[0] for l in loras]}')
print(f'1024x1024, 50 steps, CFG 8.0, euler_ancestral/karras')
print(f'Seed: {seed}')
print('Submitting...')

r = requests.post('http://127.0.0.1:8188/prompt', json={'prompt': workflow}, timeout=30)
print(f'Status: {r.status_code}')
data = r.json()
pid = data.get('prompt_id', '')
if not pid:
    print(f'Error: {data}')
    sys.exit(1)
print(f'Prompt ID: {pid}')

print('Generating...')
for i in range(120):
    time.sleep(5)
    try:
        hr = requests.get(f'http://127.0.0.1:8188/history/{pid}', timeout=10)
        if hr.status_code == 200:
            hdata = hr.json()
            if pid in hdata:
                st = hdata[pid].get('status', {})
                outputs = hdata[pid].get('outputs', {})
                if outputs:
                    print('=== DONE ===')
                    for n, out in outputs.items():
                        for img in out.get('images', []):
                            fname = img['filename']
                            print(f'File: {fname}')
                            dl = requests.get('http://127.0.0.1:8188/view',
                                params={'filename': fname, 'subfolder': '', 'type': 'output'}, timeout=30)
                            if dl.status_code == 200:
                                out_path = r'c:\Users\mana4\Desktop\manaos_integrations\generated_nsfw.png'
                                with open(out_path, 'wb') as f:
                                    f.write(dl.content)
                                print(f'Saved: {out_path} ({len(dl.content)} bytes)')
                    break
                elif st.get('status_str') == 'error':
                    print(f'Generation error: {st}')
                    break
                else:
                    if i % 6 == 0:
                        print(f'[{i*5}s] working...')
    except Exception as e:
        print(f'Poll error: {e}')
else:
    print('Timeout')
