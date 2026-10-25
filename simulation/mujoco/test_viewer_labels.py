import unittest

import mujoco

from viewer_labels import label_rectangle, uuid_label_image


class LabelTests(unittest.TestCase):
    def test_label_pixel_size_is_fixed_across_window_sizes_and_camera_zoom(self):
        image = uuid_label_image("849b54b6-5d57-44a5-95be-c94742903b37", (0.3, 0.7, 0.9))
        self.assertLessEqual(image.shape[0], 24)
        camera = mujoco.MjvGLCamera()
        camera.pos[:] = (0, -5, 0)
        camera.forward[:] = (0, 1, 0)
        camera.up[:] = (0, 0, 1)
        camera.frustum_near = 0.1
        camera.frustum_top = 0.05
        camera.frustum_bottom = -0.05
        for width, height, distance in ((640, 480, 5), (1600, 1000, 5), (1600, 1000, 20)):
            with self.subTest(width=width, height=height, distance=distance):
                camera.pos[1] = -distance
                rect = label_rectangle(camera, mujoco.MjrRect(0, 0, width, height), (0, 0, 0), image.shape)
                self.assertIsNotNone(rect)
                self.assertEqual(rect[2:], (image.shape[1], image.shape[0]))

    def test_labels_behind_camera_are_hidden(self):
        camera = mujoco.MjvGLCamera()
        camera.forward[:] = (0, 1, 0)
        camera.frustum_near = 0.1
        self.assertIsNone(label_rectangle(camera, mujoco.MjrRect(0, 0, 640, 480),
                                          (0, -2, 0), (20, 300, 3)))


if __name__ == "__main__":
    unittest.main()
