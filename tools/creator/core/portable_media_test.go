package creatorcore

import (
	"encoding/json"
	"strings"
	"testing"
)

func portableBindingsFixture() PortableMediaBindings {
	ids := []string{"systemd-boot","loader-config","loader-normal","loader-recovery","kernel","initramfs","bootstrap-capsule","release-trust","stable-base","persistent-state","system-image","release-manifest","release-envelope"}
	value := PortableMediaBindings{Schema: PortableMediaBindingsSchema, Artifacts: make([]PortableMediaArtifactBinding, 0, len(ids))}
	for index, id := range ids {
		value.Artifacts = append(value.Artifacts, PortableMediaArtifactBinding{ID: id, SHA256: strings.Repeat(string("abcdef0123456789"[index%16]), 64), SizeBytes: uint64(index + 1)})
	}
	return value
}

func TestPlanPortableMediaOwnsExactFinalDestinations(t *testing.T) {
	const commit = "0123456789abcdef0123456789abcdef01234567"
	plan, err := PlanPortableMedia(8<<30, commit, portableBindingsFixture())
	if err != nil { t.Fatal(err) }
	if plan.Schema != PortableMediaPlanSchema || plan.Profile != "portable-usb" { t.Fatalf("unexpected plan identity: %#v", plan) }
	if plan.PhysicalWriteAuthorized { t.Fatal("portable media plan must not authorize physical write") }
	if len(plan.Artifacts) != 13 { t.Fatalf("artifact count=%d want=13", len(plan.Artifacts)) }
	got := map[string]PortableMediaArtifactPlan{}
	for _, artifact := range plan.Artifacts { got[artifact.ID] = artifact }
	expected := map[string][2]string{
		"systemd-boot": {"ORDAX-ESP","/EFI/BOOT/BOOTX64.EFI"},
		"loader-config": {"ORDAX-ESP","/loader/loader.conf"},
		"loader-normal": {"ORDAX-ESP","/loader/entries/ordax-portable.conf"},
		"loader-recovery": {"ORDAX-ESP","/loader/entries/ordax-portable-recovery.conf"},
		"kernel": {"ORDAX-ESP","/ordax/vmlinuz"},
		"initramfs": {"ORDAX-ESP","/ordax/initrd.gz"},
		"bootstrap-capsule": {"ORDAX-ESP","/ordax/bootstrap/bootstrap.erofs"},
		"release-trust": {"ORDAX-ESP","/ordax/bootstrap/trust/release-ed25519.json"},
		"stable-base": {"ORDAX-DATA","/.ordax/base/stable-base.erofs"},
		"persistent-state": {"ORDAX-DATA","/.ordax/state/persistent-state.img"},
		"system-image": {"ORDAX-DATA","/.ordax/releases/"+commit+"/system.erofs"},
		"release-manifest": {"ORDAX-DATA","/.ordax/releases/"+commit+"/release-manifest.json"},
		"release-envelope": {"ORDAX-DATA","/.ordax/releases/"+commit+"/release-envelope.json"},
	}
	for id, want := range expected {
		artifact, ok := got[id]
		if !ok { t.Fatalf("missing artifact %q", id) }
		if artifact.Partition != want[0] || artifact.TargetPath != want[1] { t.Fatalf("%s destination=%s:%s want=%s:%s", id, artifact.Partition, artifact.TargetPath, want[0], want[1]) }
	}
}

func TestPlanPortableMediaRejectsInvalidBindings(t *testing.T) {
	const commit = "0123456789abcdef0123456789abcdef01234567"
	b := portableBindingsFixture(); b.Artifacts = b.Artifacts[:len(b.Artifacts)-1]
	if _, err := PlanPortableMedia(8<<30, commit, b); err == nil { t.Fatal("missing binding accepted") }
	b = portableBindingsFixture(); b.Artifacts[0].ID = "unknown"
	if _, err := PlanPortableMedia(8<<30, commit, b); err == nil { t.Fatal("unknown binding accepted") }
	b = portableBindingsFixture(); b.Artifacts[1].ID = b.Artifacts[0].ID
	if _, err := PlanPortableMedia(8<<30, commit, b); err == nil { t.Fatal("duplicate binding accepted") }
	b = portableBindingsFixture(); b.Artifacts[0].SHA256 = "AA"
	if _, err := PlanPortableMedia(8<<30, commit, b); err == nil { t.Fatal("invalid digest accepted") }
	if _, err := PlanPortableMedia(8<<30, "not-a-commit", portableBindingsFixture()); err == nil { t.Fatal("invalid source commit accepted") }
}

func TestParsePortableMediaBindingsIsStrict(t *testing.T) {
	payload, err := json.Marshal(portableBindingsFixture())
	if err != nil { t.Fatal(err) }
	parsed, err := ParsePortableMediaBindings(payload)
	if err != nil { t.Fatal(err) }
	if len(parsed.Artifacts) != 13 { t.Fatalf("artifact count=%d", len(parsed.Artifacts)) }
	payload = append(payload, []byte("\n{}")...)
	if _, err := ParsePortableMediaBindings(payload); err == nil { t.Fatal("trailing JSON accepted") }
}
