# Put your models here

Put the model files `*.gguf` and their vision projectors `mmproj-*.gguf` into this folder, then run `./install.sh` in the
repository root. A model without an `mmproj-...` file works but cannot see pictures.

The files themselves are not committed (see `.gitignore`). A different models folder can be set in `.env`: `MODELS_DIR=...`.
