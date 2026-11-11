# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

from io import BytesIO

from PIL import Image

from thumbor.config import Config
from thumbor.context import Context
from thumbor.engines.pil import Engine


def make_transparent_palette_gif():
    """A palette GIF that marks one palette entry as transparent."""
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for x in range(8, 24):
        for y in range(8, 24):
            image.putpixel((x, y), (0, 0, 255, 255))

    buffer = BytesIO()
    image.save(buffer, "GIF", transparency=0)
    return buffer.getvalue()


def get_context():
    cfg = Config(
        SECURITY_KEY="ACME-SEC",
        ENGINE="thumbor.engines.pil",
        PILLOW_PRESERVE_INDEXED_MODE=True,
    )
    cfg.LOADER = "thumbor.loaders.file_loader"
    cfg.STORAGE = "thumbor.storages.no_storage"

    return Context(config=cfg)


def test_resized_palette_gif_keeps_transparency():
    engine = Engine(get_context())
    engine.load(make_transparent_palette_gif(), ".gif")

    engine.resize(240, 160)
    output = engine.read(".gif")

    resized = Image.open(BytesIO(output))

    assert "transparency" in resized.info
    assert resized.convert("RGBA").getchannel("A").getextrema()[0] == 0
