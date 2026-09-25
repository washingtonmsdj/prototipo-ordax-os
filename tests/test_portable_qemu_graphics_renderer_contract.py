import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
QEMU_BOOT = (ROOT / "bootstrap/portable-v2/qemu_boot.py").read_text(encoding="utf-8")
PORTABLE_INIT = (ROOT / "bootstrap/initramfs/portable_init.sh").read_text(encoding="utf-8")


class PortableQemuGraphicsRendererContractTests(unittest.TestCase):
    def test_graphical_qemu_adds_explicit_proof_only_kernel_flag(self):
        self.assertIn('QEMU_SOFTWARE_RENDERER_FLAG = "ordax.qemu_allow_software_renderer=1"', QEMU_BOOT)
        self.assertIn('if graphical_hardware:', QEMU_BOOT)
        self.assertIn('kernel_append += " " + QEMU_SOFTWARE_RENDERER_FLAG', QEMU_BOOT)
        self.assertIn('"-append", kernel_append,', QEMU_BOOT)

    def test_portable_init_exports_wlroots_allowance_only_for_exact_flag(self):
        self.assertIn('QEMU_ALLOW_SOFTWARE_RENDERER=0', PORTABLE_INIT)
        self.assertIn('*" ordax.qemu_allow_software_renderer=1 "*) QEMU_ALLOW_SOFTWARE_RENDERER=1 ;;', PORTABLE_INIT)
        self.assertIn('if [ "$QEMU_ALLOW_SOFTWARE_RENDERER" -eq 1 ]; then', PORTABLE_INIT)
        self.assertIn('export WLR_RENDERER_ALLOW_SOFTWARE=1', PORTABLE_INIT)
        self.assertIn('ORDAX_QEMU_SOFTWARE_RENDERER_ALLOWANCE=YES', PORTABLE_INIT)

    def test_proof_flag_is_not_part_of_portable_loader_entries(self):
        boot_tree = ROOT / "boot/portable-v2"
        for path in boot_tree.rglob("*.conf"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("ordax.qemu_allow_software_renderer", text, path.as_posix())


if __name__ == "__main__":
    unittest.main()
