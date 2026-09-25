import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
QEMU_BOOT = (ROOT / "bootstrap/portable-v2/qemu_boot.py").read_text(encoding="utf-8")
PORTABLE_INIT = (ROOT / "bootstrap/initramfs/portable_init.sh").read_text(encoding="utf-8")


class PortableQemuGraphicsRendererContractTests(unittest.TestCase):
    def test_graphical_qemu_still_uses_real_virtio_drm_hardware(self):
        self.assertIn('if graphical_hardware:', QEMU_BOOT)
        self.assertIn('"-vga", "virtio"', QEMU_BOOT)
        self.assertIn('"-display", "none"', QEMU_BOOT)
        self.assertNotIn("WLR_RENDERER_ALLOW_SOFTWARE", QEMU_BOOT)

    def test_portable_init_allows_software_renderer_only_for_virtio_display(self):
        self.assertIn('VIRTIO_GRAPHICS=0', PORTABLE_INIT)
        self.assertIn('/sys/bus/pci/devices/*', PORTABLE_INIT)
        self.assertIn('"0x1af4"', PORTABLE_INIT)
        self.assertIn('0x03*) VIRTIO_GRAPHICS=1', PORTABLE_INIT)
        self.assertIn('if [ "$VIRTIO_GRAPHICS" -eq 1 ]; then', PORTABLE_INIT)
        self.assertIn('export WLR_RENDERER_ALLOW_SOFTWARE=1', PORTABLE_INIT)
        self.assertIn('ORDAX_VIRTIO_GPU_SOFTWARE_RENDERER_ALLOWANCE=YES', PORTABLE_INIT)

    def test_physical_loader_entries_do_not_force_software_rendering(self):
        boot_tree = ROOT / "boot/portable-v2"
        for path in boot_tree.rglob("*.conf"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("WLR_RENDERER_ALLOW_SOFTWARE", text, path.as_posix())
            self.assertNotIn("virtio", text.lower(), path.as_posix())


if __name__ == "__main__":
    unittest.main()
