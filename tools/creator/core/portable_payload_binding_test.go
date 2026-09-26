package creatorcore

import (
	"strings"
	"testing"
)

func TestPortablePayloadBindingsIdentityMatchesApplicationPlan(t *testing.T) {
	ids := []string{
		"systemd-boot", "loader-config", "loader-normal", "loader-recovery",
		"kernel", "initramfs", "bootstrap-capsule", "release-trust",
		"stable-base", "persistent-state", "system-image", "surface-runtime-image",
		"surface-runtime-ref", "local-ai-runtime-image", "local-ai-runtime-ref",
		"release-manifest", "release-envelope",
	}
	bindings := PortableMediaBindings{Schema: PortableMediaBindingsSchema}
	for i, id := range ids {
		bindings.Artifacts = append(bindings.Artifacts, PortableMediaArtifactBinding{
			ID: id,
			SHA256: strings.Repeat(string("0123456789abcdef"[i%16]), 64),
			SizeBytes: uint64(i + 1),
		})
	}
	bindingSHA, err := PortableMediaBindingsSHA256(bindings)
	if err != nil {
		t.Fatal(err)
	}
	media, err := PlanPortableMedia(8<<30, "0123456789abcdef0123456789abcdef01234567", bindings)
	if err != nil {
		t.Fatal(err)
	}
	application, err := PlanPortableApplication(media)
	if err != nil {
		t.Fatal(err)
	}
	applicationSHA, err := PortableApplicationBindingsSHA256(application)
	if err != nil {
		t.Fatal(err)
	}
	if applicationSHA != bindingSHA {
		t.Fatalf("payload identity drifted across planning: bindings=%s application=%s", bindingSHA, applicationSHA)
	}

	application.Operations[3].SHA256 = strings.Repeat("f", 64)
	mutatedSHA, err := PortableApplicationBindingsSHA256(application)
	if err != nil {
		t.Fatal(err)
	}
	if mutatedSHA == bindingSHA {
		t.Fatal("mutated payload retained owner-authorized binding identity")
	}
}

func TestPortablePayloadBindingsRejectIncompleteOrDuplicateSet(t *testing.T) {
	bindings := portableBindingsFixture()
	bindings.Artifacts = bindings.Artifacts[:16]
	if _, err := PortableMediaBindingsSHA256(bindings); err == nil {
		t.Fatal("incomplete Portable payload was accepted")
	}

	bindings = portableBindingsFixture()
	bindings.Artifacts[1].ID = bindings.Artifacts[0].ID
	if _, err := PortableMediaBindingsSHA256(bindings); err == nil {
		t.Fatal("duplicate Portable payload artifact id was accepted")
	}
}
