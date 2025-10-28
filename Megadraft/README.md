# Megadraft Bot?

Last Edited: 10/27/25 by landontu


## Dependencies

[![Python][Python.org]][Python-url] for development
[![PyTorch][PyTorch.org]][PyTorch-url] for machine learning
Eventually probably Docker once everything works

## Files

### `main.py`

The main file. Right now, it just imports `boardGenerator.py` and contains some testing for the `Board` class.

### `boardGenerator.py`

Contains a few global variables that could be useful. Contains a `Board` class that can generate a new megadraft board. 

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[PyTorch.org]: https://img.shields.io/badge/pytorch-green?style=for-the-badge&logo=pytorch&link=https%3A%2F%2Fpytorch.org%2F
[PyTorch-url]: https://pytorch.org
[Docker.com]: https://img.shields.io/badge/Docker-yellow?style=for-the-badge&logo=Docker&link=https%3A%2F%2Fwww.docker.com%2F
[Docker-url]: https://www.docker.com/
[Python.org]: https://img.shields.io/badge/Python-white?style=for-the-badge&logo=python&link=https%3A%2F%2Fwww.python.org%2F
[Python-url]: https://www.python.org/