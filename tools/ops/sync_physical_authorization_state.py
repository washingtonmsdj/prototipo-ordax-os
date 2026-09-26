#!/usr/bin/env python3
"""One-shot canonical snapshot transition after explicit owner authorization."""

from pathlib import Path
import re
import textwrap

AUTH_CONTEXT = "b5803154eed8a85962b5c2dddbfff29f2ff408c92b63247ca62d1c5ca71eda10"


def regex_replace(path: str, pattern: str, replacement: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{path}: expected one regex replacement, got {count}")
    target.write_text(updated, encoding="utf-8")


def replace_required(path: str, old: str, new: str, *, count: int | None = None) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    found = text.count(old)
    if count is not None and found != count:
        raise SystemExit(f"{path}: expected {count} occurrences of {old!r}, got {found}")
    if found == 0:
        raise SystemExit(f"{path}: missing {old!r}")
    target.write_text(text.replace(old, new), encoding="utf-8")


def replace_if_present(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old in text:
        target.write_text(text.replace(old, new), encoding="utf-8")


current_state_method = textwrap.indent(
    textwrap.dedent(
        f'''\
def test_physical_authorization_is_bound_but_physical_proof_remains_fail_closed(self):
    self.assertEqual(self.authorization["status"], "authorized")
    self.assertTrue(self.authorization["physical_write_allowed"])
    self.assertTrue(self.authorization["explicit_owner_authorization"])
    self.assertEqual(
        self.authorization["scope"],
        "first-real-stable-mvp-usb-proof",
    )
    self.assertEqual(self.authorization["release_sequence"], 1)
    self.assertEqual(
        self.authorization["authorization_context_sha256"],
        "{AUTH_CONTEXT}",
    )
    self.assertTrue(
        self.authorization["requirements"][
            "writer_requires_exact_17_artifact_readback"
        ]
    )
    self.assertEqual(
        self.authorization["release_binding"]["source_commit"],
        "b924ff8d74d1761232381ae3f9604bba17497cfd",
    )
    self.assertIn("CANONICAL_V4_RELEASE_PROOF_BINDING=PASS", self.current)
    self.assertIn("PHYSICAL_AUTHORIZATION_ELIGIBLE=YES", self.current)
    self.assertIn(
        "CANONICAL_V4_RELEASE_PROOF=PASS_SIGNED_MATERIALIZED_EXACT",
        self.current,
    )
    self.assertIn("PHYSICAL_OWNER_AUTHORIZATION_RECORDED=YES_BOUND_CONTEXT", self.current)
    self.assertIn("PHYSICAL_WRITE_ALLOWED=YES_BOUND_OWNER_AUTHORIZATION", self.current)
    self.assertIn("PHYSICAL_TARGET_SELECTED=NO", self.current)
    self.assertIn("PHYSICAL_TARGET_DESTRUCTIVE_CONFIRMATION=PENDING", self.current)
    self.assertIn(
        "CANONICAL_SIGNED_RELEASE_BOOT_PROVEN=NO_PHYSICAL_STABLE_MVP_PENDING",
        self.current,
    )
    self.assertIn("MVP_SURFACE_SMOKE_HARNESS=PASS_SOURCE", self.current)
    self.assertIn("MVP_SURFACE_SMOKE_PHYSICAL=PENDING", self.current)
    self.assertIn("CANONICAL_STABLE_GRAPHICAL_MODE=PENDING", self.current)
    self.assertIn("PUBLIC_PHYSICAL_APPLY=NO", self.current)
    self.assertIn("all 12 manual tour items", self.current)
    self.assertIn("verified Stable runtime", self.current)
'''
    ),
    "    ",
)
regex_replace(
    "tests/test_current_state_first_run_input.py",
    r"    def test_physical_authorization_is_fail_closed_after_v4_proof_binding\(self\):.*?(?=\n\nif __name__ == \"__main__\":)",
    current_state_method,
)

current = Path("docs/CURRENT-STATE.md")
text = current.read_text(encoding="utf-8")
text, count = re.subn(
    r"The authorization contract is now `blocked-explicit-physical-authorization-pending`, with every source/release binding resolved and `physical_write_allowed=false`; read-only preflight reaches fresh owner consent, but no new consent has been recorded\. No USB is selected or erasable;",
    f"The authorization contract is now `authorized`, bound to authorization context SHA-256 `{AUTH_CONTEXT}` across 73 governed source files, with every source/release binding resolved and `physical_write_allowed=true` for the separately gated physical proof flow. Fresh owner consent has been recorded, but no target-specific consent has been recorded and no USB has been selected or written;",
    text,
    count=1,
)
if count != 1:
    raise SystemExit(f"docs/CURRENT-STATE.md: authorization prose transition count={count}")
text, count = re.subn(
    r"No destructive authority has been granted: fresh owner consent is\s+still absent for the exact 17-artifact v4 release\. The physical Creator",
    "Explicit owner authorization has now been recorded for the exact 17-artifact v4 release\nand current authorization context. That authorization permits materialization of the bound\ncandidate only; no USB target has been selected, no target-specific destructive confirmation\nhas been recorded and no physical write/proof has occurred. The physical Creator",
    text,
    count=1,
)
if count != 1:
    raise SystemExit(f"docs/CURRENT-STATE.md: pre-USB authorization prose transition count={count}")
required_markers = {
    "STABLE_MVP_USB_READINESS_CURRENT_STAGE=FRESH_OWNER_AUTHORIZATION_AND_PHYSICAL_USB_PENDING": "STABLE_MVP_USB_READINESS_CURRENT_STAGE=AUTHORIZED_CANDIDATE_READY_FOR_SEPARATE_PHYSICAL_FLOW",
    "PHYSICAL_OWNER_AUTHORIZATION_REACHABLE=YES_FRESH_CONSENT_REQUIRED": "PHYSICAL_OWNER_AUTHORIZATION_RECORDED=YES_BOUND_CONTEXT",
    "FIRST_STABLE_MVP_USB_WRITE=HOLD_NO_USB_AND_NO_FRESH_AUTHORIZATION": "FIRST_STABLE_MVP_USB_WRITE=HOLD_NO_PHYSICAL_TARGET_SELECTED",
    "PHYSICAL_WRITE_AUTHORITY=NO_EXPLICIT_OWNER_AUTHORIZATION": "PHYSICAL_WRITE_AUTHORITY=AUTHORIZED_CANDIDATE_ONLY_TARGET_CONFIRMATION_REQUIRED",
    "PHYSICAL_WRITE_ALLOWED=NO_EXPLICIT_OWNER_AUTHORIZATION": "PHYSICAL_WRITE_ALLOWED=YES_BOUND_OWNER_AUTHORIZATION",
}
for old, new in required_markers.items():
    if old not in text:
        raise SystemExit(f"docs/CURRENT-STATE.md: missing marker {old}")
    text = text.replace(old, new)
current.write_text(text, encoding="utf-8")

replace_required(
    "docs/MVP-PRE-PHYSICAL-HANDOFF.md",
    "PHYSICAL_WRITE_AUTHORIZATION=PENDING_EXPLICIT_OWNER_CONSENT",
    "PHYSICAL_WRITE_AUTHORIZATION=PASS_EXPLICIT_OWNER_CONSENT_BOUND_CONTEXT",
    count=1,
)
replace_required(
    "docs/MVP-PRE-PHYSICAL-HANDOFF.md",
    "At the current `explicit-owner-authorization-pending` stage, the remaining gates are:",
    "At the current `authorized-candidate-ready-for-separate-physical-flow` stage, owner authorization is complete. The remaining gates are:",
    count=1,
)
old_list = """1. record fresh explicit owner authorization for the exact bound v4 release and authorization context;
2. select the physical USB and revalidate its live identity immediately before destructive work;
3. require target-specific destructive confirmation and Windows UAC;
4. execute the physical write and verify all 17 canonical artifacts by exact SHA-256 and size/readback;
5. boot the canonical Stable/MVP USB on the target notebook and complete the OOBE -> Surface -> first-party-app smoke tour;
6. prove real cold-health, commit `current/known-good`, reboot offline and confirm the known-good boot;
7. exercise a broken candidate and prove physical rollback/recovery without losing the known-good release;
8. only after the required physical evidence, promote the approved release into the Stable public channel/catalog."""
new_list = """1. select the physical USB and revalidate its live identity immediately before destructive work;
2. require target-specific destructive confirmation and Windows UAC;
3. execute the physical write and verify all 17 canonical artifacts by exact SHA-256 and size/readback;
4. boot the canonical Stable/MVP USB on the target notebook and complete the OOBE -> Surface -> first-party-app smoke tour;
5. prove real cold-health, commit `current/known-good`, reboot offline and confirm the known-good boot;
6. exercise a broken candidate and prove physical rollback/recovery without losing the known-good release;
7. only after the required physical evidence, promote the approved release into the Stable public channel/catalog."""
replace_required("docs/MVP-PRE-PHYSICAL-HANDOFF.md", old_list, new_list, count=1)
replace_required(
    "docs/MVP-PRE-PHYSICAL-HANDOFF.md",
    "Authorization closes only step 1. It does not select media, confirm a target, invoke the writer, establish physical proof, or publish a Stable release.",
    "Authorization is now recorded. It does not select media, confirm a target, invoke the writer, establish physical proof, or publish a Stable release.",
    count=1,
)

replace_if_present(
    "PLANO-03-FECHAMENTO-PRE-USB-NOVA-ORDAX.md",
    "Até haver USB e consentimento explícito novo para o contexto atual:",
    "Com o consentimento explícito novo já registrado para o contexto atual, até haver USB e confirmação destrutiva específica do alvo:",
)
replace_if_present(
    "PLANO-03-FECHAMENTO-PRE-USB-NOVA-ORDAX.md",
    "FIRST_STABLE_MVP_USB_WRITE=HOLD_NO_USB_AND_NO_FRESH_AUTHORIZATION",
    "FIRST_STABLE_MVP_USB_WRITE=HOLD_NO_PHYSICAL_TARGET_SELECTED",
)
replace_if_present(
    "PLANO-03-FECHAMENTO-PRE-USB-NOVA-ORDAX.md",
    "PHYSICAL_WRITE_AUTHORITY=NO_EXPLICIT_OWNER_AUTHORIZATION",
    "PHYSICAL_WRITE_AUTHORITY=AUTHORIZED_CANDIDATE_ONLY_TARGET_CONFIRMATION_REQUIRED",
)
replace_if_present(
    "MVP.md",
    "FIRST_STABLE_MVP_USB_WRITE=HOLD_NO_USB_AND_NO_FRESH_AUTHORIZATION",
    "FIRST_STABLE_MVP_USB_WRITE=HOLD_NO_PHYSICAL_TARGET_SELECTED",
)
replace_if_present(
    "docs/PROMOTION-GATES.md",
    "The current contract is `blocked-explicit-physical-authorization-pending`; the prerelease did not become the stable `latest` release, and no physical write is authorized.",
    "The current contract is `authorized` for the exact bound v4 context; the prerelease did not become the stable `latest` release, no physical target has been selected or written, and Stable promotion remains pending physical proof.",
)
replace_if_present(
    "AGENTS.md",
    "fresh owner authorization for the current 17-artifact / 39-operation writer context\n",
    "",
)
