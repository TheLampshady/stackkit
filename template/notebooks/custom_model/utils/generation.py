import base64
import json
import logging
import random
from io import BytesIO

import torch
from accelerate import Accelerator
from diffusers import StableDiffusion3Pipeline, StableDiffusionPipeline

logger = logging.getLogger(__name__)

IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024


LORA_LIST = [
    {
        "pretrained_model_name_or_path_or_dict": "your-org/your-lora-1",
        "weight_name": "your-lora-1.safetensors",
        "weight_scale": 1,
        "adapter_name": "style-a",
    },
    {
        "pretrained_model_name_or_path_or_dict": "your-org/your-lora-2",
        "weight_name": "your-lora-2.safetensors",
        "weight": 1,
        "adapter_name": "style-b",
    },
]

DEFAULT_PIPE_CONFIGS = {
    "num_inference_steps": 35,
    "guidance_scale": 3.5,
    "negative_prompt": "",
}


class ImageClient:
    def __init__(self, model_name: str | None = None):
        self.pipe = self.get_pipe(model_name)

    @staticmethod
    def get_pipe(model_name: str) -> StableDiffusionPipeline:
        """
        Loads the initial model into a pipe

        :param model_name: Name to pull from
        :return: a pipe
        """
        pipe = StableDiffusion3Pipeline.from_pretrained(
            model_name, torch_dtype=torch.bfloat16
        )
        accelerator = Accelerator()
        device = accelerator.device
        return pipe.to(device)

    def get_latents(self) -> torch.Tensor:
        """
        Loads latents that initialized the generation with noise
        - Adds randomness
        :return:
        """
        seed = random.randint(0, 2**32 - 1)

        return self.pipe.prepare_latents(
            batch_size=1,
            num_channels_latents=16,
            width=IMAGE_WIDTH,
            height=IMAGE_HEIGHT,
            dtype=torch.bfloat16,
            generator=torch.manual_seed(seed),
            device=self.pipe._execution_device,  # TODO private, what is proper?
        )

    def load_loras(self):
        """
        Loads Lora weights for model usage
        :return:
        """
        for entry in LORA_LIST:
            self.pipe.load_lora_weights(**entry)

    def predict_image(self, prompt: str, lora: str, config: dict | None = None) -> str:
        """
        Takes prompt and settings to generate an image.

        :param prompt: The user prompt
        :param lora: The lora name to load lora weights for maodel
        :param config: configs for model generation
        :return: an encoded image to byte string
        """
        self.pipe.set_adapters(lora)  # Loads lora weights for topic

        latents = self.get_latents()  # Loads random noise

        # Loads defaults and overrides the sent configs
        # Dont send params that are included below
        config = config or {}
        config = dict(DEFAULT_PIPE_CONFIGS).update(config)
        logger.info(f"Gen config: {json.dumps(config)}")

        image = self.pipe(
            prompt,
            width=IMAGE_WIDTH,
            height=IMAGE_HEIGHT,
            latents=latents,
            **config or {},
        ).images[0]

        buffered = BytesIO()
        image.save(buffered, format="PNG", optimize=True)

        return base64.b64encode(buffered.getvalue()).decode("utf-8")
