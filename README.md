# TreeDect-web

A tool for detecting and counting trees from drones.

This project is sponsored by Fujian Agricultural And Forestry University.

> [!WARNING]
> This repo is still in early stage of developing. Any bug is possible.

# Requirements

- RAM > 8G
- Nvidia GPU with VRAM >= 8G
- CUDA >= 11.x

# Installation

Scripts for environment setup is included in `setup.sh` and `node.sh`.

To launch the frontend, run `npm run dev` and visit http://localhost:5173.

To launch the backend, enter `treedect/` subfolder and run `python api.py`. The default backend is launched at http://localhost:8000.
