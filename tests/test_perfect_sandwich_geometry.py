import unittest
import numpy as np
from PIL import Image, ImageDraw

from scripts.build_perfect_sandwich import (
    find_skew_projection,
    restore_text_image,
    is_color_image,
)


class TestPerfectSandwichGeometry(unittest.TestCase):
    def test_find_skew_projection(self):
        # Create synthetic image with horizontal text-like lines
        im = Image.new("L", (800, 1000), 255)
        draw = ImageDraw.Draw(im)
        for y in range(150, 850, 40):
            draw.line([(100, y), (700, y)], fill=0, width=4)

        # Rotate artificially by -1.2 degrees
        tilted = im.rotate(-1.2, fillcolor=255)
        detected_angle = find_skew_projection(tilted)
        
        # When an image is tilted clockwise by -1.2°, the correction angle is approx +1.20°
        self.assertAlmostEqual(detected_angle, 1.20, delta=0.08)

    def test_restore_text_image_snaps_to_white(self):
        # Create image with off-white / yellowed background (val ~ 220) and dark ink (val ~ 40)
        im = Image.new("L", (400, 400), 220)
        draw = ImageDraw.Draw(im)
        draw.text((100, 100), "Sanskrit Text Rigveda", fill=40)

        rest = restore_text_image(im, text_bbox=(50, 50, 350, 350, 400, 400), in_white=225)
        arr = np.array(rest)
        
        # Background outside text should snap to pure 255 (#FFFFFF)
        self.assertEqual(arr[10, 10], 255)
        self.assertEqual(arr[390, 390], 255)

    def test_asymmetric_margin_masking_verso_recto(self):
        # Verso page: inner gutter is on the right
        im_verso = Image.new("L", (500, 500), 255)
        draw = ImageDraw.Draw(im_verso)
        # Put simulated text in the middle
        draw.rectangle([100, 100, 400, 400], fill=50)
        # Put simulated gutter shadow on the right border
        draw.rectangle([460, 50, 490, 450], fill=80)

        # Content bbox for text
        text_bbox = (100, 100, 400, 400, 500, 500)
        rest_verso = restore_text_image(im_verso, text_bbox=text_bbox, is_even_page=True)
        arr_verso = np.array(rest_verso)

        # The gutter shadow on the right border (x > 450) must be completely whited out to 255
        self.assertEqual(arr_verso[250, 475], 255)

    def test_is_color_image(self):
        im_gray = Image.new("L", (100, 100), 128)
        self.assertFalse(is_color_image(im_gray))

        im_rgb_gray = Image.new("RGB", (100, 100), (128, 128, 128))
        self.assertFalse(is_color_image(im_rgb_gray))

        im_color = Image.new("RGB", (100, 100), (220, 50, 30))
        self.assertTrue(is_color_image(im_color))


if __name__ == "__main__":
    unittest.main()
