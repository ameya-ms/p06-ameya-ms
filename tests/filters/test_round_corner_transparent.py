# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

from tornado.testing import gen_test

from tests.base import FilterTestCase


class RoundCornerTransparentTestCase(FilterTestCase):
    @gen_test
    async def test_round_corner_transparent_preserves_edge_colors(self):
        """
        Regression test for thumbor/thumbor#1687: transparent rounded corners
        carry a dark ring.
        
        Bug: When transparent=1, the C code multiplies edge pixel RGB values
        by (1-aa_factor) where aa can be up to 0.75. This darkens pixels 
        toward black, creating a visible dark ring outline along curved corners.
        
        This test compares pixels in the corner region between the original
        unfiltered image and the filtered image. Pixels that remain OPAQUE
        (alpha=255) in the filtered image should keep approximately the same
        RGB values as the original. If they're significantly darkened, that
        indicates the multiplication bug.
        """
        # Get the original unfiltered image
        original_img = self.get_fixture("source.jpg", mode="RGBA")
        orig_pixels = original_img.load()
        
        # Apply round_corner with transparent=1
        image = await self.get_filtered(
            "source.jpg",
            "thumbor.filters.round_corner",
            "round_corner(50,255,255,255,1)",  # radius 50, white fill, transparent
            mode="RGBA",
        )
        
        assert image.mode == "RGBA"
        pixels = image.load()
        
        # The dark ring bug affects the AA blending region
        # Look for opaque pixels in the corner area that have been darkened
        darkened_opaque_pixels = []
        normal_opaque_pixels = []
        
        # Check corner region and a bit beyond where AA happens
        for x in range(0, min(100, image.size[0])):
            for y in range(0, min(100, image.size[1])):
                r, g, b, a = pixels[x, y]
                
                # Only check fully opaque pixels (alpha=255)
                if a == 255:
                    # Get original color
                    orig_r, orig_g, orig_b, orig_a = orig_pixels[x, y]
                    
                    # Calculate color difference
                    r_diff = abs(int(r) - int(orig_r))
                    g_diff = abs(int(g) - int(orig_g))
                    b_diff = abs(int(b) - int(orig_b))
                    total_diff = r_diff + g_diff + b_diff
                    
                    # With the bug, RGB gets multiplied by (1-aa) values like 0.25-0.75
                    # E.g., if original is (25, 26, 254) and multiplied by 0.15,
                    # result is (3, 3, 38), a difference of 22+23+216 = 261
                    #
                    # After the fix, opaque pixels should preserve their colors
                    # Allow small tolerance (15) for legitimate color compression
                    if total_diff > 15:
                        darkened_opaque_pixels.append({
                            'pos': (x, y),
                            'filtered_rgb': (r, g, b),
                            'original_rgb': (orig_r, orig_g, orig_b),
                            'alpha': a,
                            'color_diff': total_diff
                        })
                    else:
                        normal_opaque_pixels.append((x, y, total_diff))
        
        print(f"\n\nOpaque pixels in corner region with small diff (normal): {len(normal_opaque_pixels)}")
        print(f"Opaque pixels with large RGB darkening (bug indicator): {len(darkened_opaque_pixels)}")
        
        if darkened_opaque_pixels:
            print(f"\nExamples of darkened opaque pixels:")
            for px in darkened_opaque_pixels[:5]:
                print(f"  pos={px['pos']}: original RGB={px['original_rgb']}, "
                      f"filtered RGB={px['filtered_rgb']}, diff={px['color_diff']}")
        
        # THIS ASSERTION SHOULD FAIL WITH THE CURRENT BUGGY CODE
        # The bug darkens opaque pixels along the AA edge
        assert len(darkened_opaque_pixels) == 0, \
            f"DARK RING ARTIFACT DETECTED: Found {len(darkened_opaque_pixels)} opaque " \
            f"pixels in the corner region with severely darkened RGB values. " \
            f"This indicates RGB is being multiplied by (1-aa_factor) instead of being preserved. " \
            f"With the fix, opaque pixels should keep their original colors. " \
            f"Examples: {darkened_opaque_pixels[:3]}"

        # The corner must stay anti-aliased: along the curve there should be
        # semi-transparent pixels, so a hard (aliased) edge fails too.
        semi_transparent = 0
        for x in range(0, min(100, image.size[0])):
            for y in range(0, min(100, image.size[1])):
                alpha = pixels[x, y][3]
                if 0 < alpha < 255:
                    semi_transparent += 1

        assert semi_transparent > 0, (
            "ROUNDED CORNER IS NOT ANTI-ALIASED: found no pixels with "
            "0 < alpha < 255 along the curve, so the transparent edge is a "
            "hard edge."
        )
