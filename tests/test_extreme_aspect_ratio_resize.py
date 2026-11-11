# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

"""Regression test for thumbor/thumbor#1711 (course issue #4).

A request at an aspect ratio far from the source's could crop the image down
to zero pixels on one side. The resize then produced either a fully
transparent picture (the source is transparent, so every pixel came back
transparent) or a 500. Every request for a size of at least one pixel per
side must return a real, correctly sized picture.
"""

from io import BytesIO
from os.path import abspath, dirname, join

from PIL import Image
from tornado.testing import gen_test

from tests.handlers.test_base_handler import BaseImagingTestCase
from thumbor.config import Config
from thumbor.context import Context, ServerParameters
from thumbor.importer import Importer

# rainbow.png and 940x2.png are the sources the issue names; both live in
# the course image folder, not in tests/fixtures/images.
COURSE_IMAGES_PATH = abspath(
    join(dirname(__file__), "../course/images/")
)


class ExtremeAspectRatioResizeTestCase(BaseImagingTestCase):
    def get_context(self):
        cfg = Config(SECURITY_KEY="ACME-SEC")
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.FILE_LOADER_ROOT_PATH = COURSE_IMAGES_PATH
        cfg.ENGINE = "thumbor.engines.pil"
        cfg.USE_GIFSICLE_ENGINE = False

        importer = Importer(cfg)
        importer.import_modules()
        server = ServerParameters(
            8889, "localhost", "thumbor.conf", None, "info", None
        )
        server.security_key = "ACME-SEC"
        return Context(server, cfg, importer)

    @gen_test
    async def test_extreme_aspect_ratio_resize_returns_a_real_picture(self):
        # /unsafe/800x20/rainbow.png: a 16x16 transparent source stretched
        # into a very wide, very short strip. The pixels must not all come
        # back transparent, the way an empty crop leaves them today.
        response = await self.async_fetch("/unsafe/800x20/rainbow.png")

        assert response.code == 200

        image = Image.open(BytesIO(response.body))

        assert image.size == (800, 20)
        assert image.convert("RGBA").getchannel("A").getextrema() != (0, 0)

        # /unsafe/fit-in/1x1/940x2.png: a 940x2 source fit into 1x1.
        response = await self.async_fetch("/unsafe/fit-in/1x1/940x2.png")

        assert response.code == 200

        image = Image.open(BytesIO(response.body))

        assert image.size == (1, 1)

        # /unsafe/fit-in/100x0/940x2.png: width only, height proportional.
        response = await self.async_fetch("/unsafe/fit-in/100x0/940x2.png")

        assert response.code == 200

        image = Image.open(BytesIO(response.body))

        assert image.size == (100, 1)
