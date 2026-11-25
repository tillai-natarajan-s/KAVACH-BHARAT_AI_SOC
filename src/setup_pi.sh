#!/usr/bin/env bash
# KAVACH setup for Raspberry Pi 5 (Raspberry Pi OS 64-bit). Run once:  bash setup_pi.sh
set -e
sudo apt update
sudo apt install -y python3-venv python3-pip git
python3 -m venv ~/kavach-env
source ~/kavach-env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p models/llama
echo ""
echo "Setup done. Now copy the Stage-2 files into models/llama/ :"
echo "  models/llama/kavach_llama_fp16.pte"
echo "  models/llama/kavach_tokenizer/   (all tokenizer files)"
echo "Then run:  source ~/kavach-env/bin/activate && streamlit run app.py --server.address 0.0.0.0"
