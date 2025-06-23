import unittest
from collections import defaultdict

from openbus_light.plot._cmap import create_colormap


class CreateColormapTestCase(unittest.TestCase):
    def test_dict_returned_without_default(self) -> None:
        cmap = create_colormap(["a", "b"])
        self.assertIsInstance(cmap, dict)
        self.assertNotIsInstance(cmap, defaultdict)
        with self.assertRaises(KeyError):
            _ = cmap["missing"]

    def test_defaultdict_returned_with_default_color(self) -> None:
        cmap = create_colormap(["a", "b"], default_color="red")
        self.assertIsInstance(cmap, defaultdict)
        self.assertEqual(cmap["missing"], "red")
        self.assertNotEqual(cmap["a"], "red")


if __name__ == "__main__":
    unittest.main()
