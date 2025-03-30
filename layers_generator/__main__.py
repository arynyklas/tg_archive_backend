import itertools
import os
import sys
import shutil
import typing

from pathlib import Path

from .parsers import find_layer, parse_errors, parse_methods, parse_tl  # type: ignore
from .generators import generate_tlobjects  # type: ignore


sys.path.insert(0, os.path.dirname(__file__))


class TempWorkDir:
    def __init__(self, new: str | Path | None=None):
        self.original = None
        self.new = new or Path(__file__).parent

    def __enter__(self):
        self.original = Path('.')

        os.makedirs(self.new, exist_ok=True)
        os.chdir(self.new)

        return self

    def __exit__(self, *args: typing.Any):
        if self.original:
            os.chdir(self.original)


GENERATOR_DIR = Path(__file__).parent
GENERATED_LAYERS_DIR = Path(__file__).parent.parent / 'layers'

BASE_TLOBJECT_IN_TLS = [GENERATOR_DIR / "data" / "mtproto.tl"]
GENERATOR_LAYERS_DIRPATH = GENERATOR_DIR / "data" / "layers"
GENERATOR_TO_COPY_DIRPATH = GENERATOR_DIR / "to_copy"

IMPORT_DEPTH = 2


def main() -> None:
    if not GENERATED_LAYERS_DIR.exists():
        GENERATED_LAYERS_DIR.mkdir()

    for layer_dirpath in GENERATOR_LAYERS_DIRPATH.iterdir():
        generated_layer_dir = GENERATED_LAYERS_DIR / layer_dirpath.name
        layer_tlobject_dir = generated_layer_dir / "tl"

        api_tl_filepath = layer_dirpath / "api.tl"

        layer = find_layer(api_tl_filepath)  # type: ignore

        if layer != int(layer_dirpath.name):
            raise ValueError(f"Layer mismatch: File Layer {layer} != Directory Layer {layer_dirpath.name}")

        layer_tlobject_dir.mkdir(parents=True, exist_ok=True)

        layer_errors_in = layer_dirpath / "errors.csv"
        layer_methods_in = layer_dirpath / "methods.csv"
        layer_friendly_in = layer_dirpath / "friendly.csv"

        errors = list(parse_errors(layer_errors_in))
        methods = list(parse_methods(layer_methods_in, layer_friendly_in, {e.str_code: e for e in errors}))

        tlobjects = list(itertools.chain(*(parse_tl(file, layer, methods) for file in [  # type: ignore
            layer_dirpath / "api.tl",
            *BASE_TLOBJECT_IN_TLS
        ])))  # type: ignore

        print("Generating TLObjects...")

        generate_tlobjects(tlobjects, layer, IMPORT_DEPTH, layer_tlobject_dir)

        shutil.copytree(
            GENERATOR_TO_COPY_DIRPATH,
            generated_layer_dir,
            dirs_exist_ok = True
        )

        # print("Generating RPCErrors...")

        # with ERRORS_OUT.open('w') as file:
        #     generate_errors(errors, file)

    (GENERATED_LAYERS_DIR / "__init__.py").touch()


main()
