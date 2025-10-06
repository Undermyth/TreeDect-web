#!/bin/bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc
git submodule init
git submodule update
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu118
pip install -r treedect/requirements.txt
cd treedect/sam2 && pip install --no-build-isolation .
export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download facebook/sam2-hiera-large
