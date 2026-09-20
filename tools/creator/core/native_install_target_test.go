package creatorcore

import "testing"

func nativeInstallTargetFixture() NativeInstallTargetIdentity {
	target, err := FinalizeNativeInstallTarget(NativeInstallTargetIdentity{
		StableID:           "wwn-0x5000cca123456789",
		DevicePath:         "/dev/nvme0n1",
		Model:              "Example NVMe",
		Serial:             "NVME1234",
		Transport:          "nvme",
		PhysicalBytes:      64 * 1024 * 1024 * 1024,
		LogicalSectorBytes: 512,
	})
	if err != nil {
		panic(err)
	}
	return target
}

func TestFinalizeNativeInstallTargetBindsExactIdentity(t *testing.T) {
	target := nativeInstallTargetFixture()
	if !target.Eligible {
		t.Fatal("normal writable non-source target must be eligible")
	}
	if len(target.ConfirmationToken) != 64 {
		t.Fatalf("unexpected confirmation token: %q", target.ConfirmationToken)
	}
	confirmed, err := MatchConfirmedNativeInstallTarget(
		[]NativeInstallTargetIdentity{target},
		target.ConfirmationToken,
	)
	if err != nil {
		t.Fatal(err)
	}
	if confirmed.StableID != target.StableID || confirmed.PhysicalBytes != target.PhysicalBytes {
		t.Fatal("confirmed target identity changed")
	}
}

func TestNativeInstallTargetRejectsSourceBootMedia(t *testing.T) {
	target, err := FinalizeNativeInstallTarget(NativeInstallTargetIdentity{
		StableID:           "usb-ordax-source",
		DevicePath:         "/dev/sdb",
		PhysicalBytes:      32 * 1024 * 1024 * 1024,
		LogicalSectorBytes: 512,
		Removable:          true,
		SourceBootMedia:    true,
	})
	if err != nil {
		t.Fatal(err)
	}
	if target.Eligible {
		t.Fatal("the booted OrdaX USB must never be an eligible Native install target")
	}
	if _, err := MatchConfirmedNativeInstallTarget(
		[]NativeInstallTargetIdentity{target},
		target.ConfirmationToken,
	); err == nil {
		t.Fatal("source boot media confirmation must fail closed")
	}
}

func TestNativeInstallTargetRejectsStaleOrChangedIdentity(t *testing.T) {
	target := nativeInstallTargetFixture()
	token := target.ConfirmationToken
	target.PhysicalBytes += 512
	if _, err := MatchConfirmedNativeInstallTarget(
		[]NativeInstallTargetIdentity{target},
		token,
	); err == nil {
		t.Fatal("mutated target identity must invalidate confirmation")
	}
}

func TestPlanNativeInstallationForTargetRemainsNonDestructive(t *testing.T) {
	target := nativeInstallTargetFixture()
	plan, err := PlanNativeInstallationForTarget(target, target.ConfirmationToken)
	if err != nil {
		t.Fatal(err)
	}
	if plan.Schema != "prototype-ordax.native-install-bound-plan/1" {
		t.Fatalf("unexpected schema: %s", plan.Schema)
	}
	if plan.Installation.Storage.Profile != "native-disk" {
		t.Fatalf("unexpected storage profile: %s", plan.Installation.Storage.Profile)
	}
	if plan.Target.ConfirmationToken != target.ConfirmationToken {
		t.Fatal("bound plan lost exact target confirmation")
	}
	if plan.PhysicalDeviceTouched || plan.PhysicalApplyAllowed {
		t.Fatal("target-bound planning must never touch or authorize the device")
	}
}

func TestNativeInstallTargetRequiresCurrentMVP512ByteSectors(t *testing.T) {
	if _, err := FinalizeNativeInstallTarget(NativeInstallTargetIdentity{
		StableID:           "disk-4k",
		DevicePath:         "/dev/sda",
		PhysicalBytes:      64 * 1024 * 1024 * 1024,
		LogicalSectorBytes: 4096,
	}); err == nil {
		t.Fatal("4K logical-sector Native target must fail until storage planner supports it")
	}
}
