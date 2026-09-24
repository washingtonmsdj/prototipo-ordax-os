package main

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

type activationFixture struct {
	dir          string
	root         string
	privatePath  string
	trustPath    string
	envelopePath string
	packagePath  string
	release      releaseDescriptor
	slot         string
}

func writeComponentSlotCandidate(
	t *testing.T,
	dir string,
	privatePath string,
	trustPath string,
	version string,
	sourceCommit string,
) (string, string, releaseDescriptor) {
	t.Helper()

	runtimePath := "system/apps/internet/runtime.mjs"
	runtimeBytes := []byte("export const componentRuntime = { schema: \"ordax.component-runtime/1\" };\n")
	runtimeDigest := sha256.Sum256(runtimeBytes)

	manifest := componentPackageManifest{
		Schema: packageSchema,
		Status: "candidate",
		Component: packageComponent{
			ID:            "internet",
			Title:         "Internet",
			Kind:          "app",
			Version:       version,
			ReleaseMode:   "component-slot",
			Criticality:   "optional",
			FailureDomain: "app",
			RestartScope:  "component",
			HealthMode:    "runtime",
			Owner:         "system/apps/internet",
			Dependencies:  []string{"surface-shell"},
		},
		SourceCommit:                      sourceCommit,
		Entrypoint:                        runtimePath,
		SelfContainedSourceGraph:          true,
		RemoteRuntimeDependencies:         false,
		ActivationAllowed:                 false,
		SignatureRequiredBeforeActivation: true,
		NativeAdaptersPackaged:            false,
		CompositionPackaged:               false,
		Files: []packageFile{
			{
				Path:   runtimePath,
				SHA256: hex.EncodeToString(runtimeDigest[:]),
				Size:   int64(len(runtimeBytes)),
			},
		},
	}
	manifestBytes, err := marshalJSON(manifest)
	if err != nil {
		t.Fatal(err)
	}
	manifestDigest := sha256.Sum256(manifestBytes)

	packagePath := filepath.Join(dir, "internet-"+version+".zip")
	file, err := os.OpenFile(packagePath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o644)
	if err != nil {
		t.Fatal(err)
	}
	writer := zip.NewWriter(file)
	writeZipEntry(t, writer, packageManifestName, manifestBytes)
	writeZipEntry(t, writer, runtimePath, runtimeBytes)
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	if err := file.Close(); err != nil {
		t.Fatal(err)
	}

	packageHash, packageSize, err := sha256File(packagePath, maxPackageBytes)
	if err != nil {
		t.Fatal(err)
	}
	release := releaseDescriptor{
		Schema:            releaseSchema,
		SourceRepository:  sourceRepository,
		SourceCommit:      sourceCommit,
		CreatedFromRecipe: createdFromRecipe,
		Component: releaseComponent{
			ID:            "internet",
			Version:       version,
			ReleaseMode:   "component-slot",
			PackageSchema: packageSchema,
		},
		Package: packageBinding{
			Name:           "internet.zip",
			SHA256:         packageHash,
			Size:           packageSize,
			ManifestSHA256: hex.EncodeToString(manifestDigest[:]),
		},
		Activation: activationPolicy{
			DirectActivationAllowed: false,
			PendingHealthRequired:    true,
		},
	}

	// The canonical signed release requires the package basename to be <component>.zip.
	canonicalPackage := filepath.Join(dir, "internet.zip")
	if err := os.Rename(packagePath, canonicalPackage); err != nil {
		t.Fatal(err)
	}
	packagePath = canonicalPackage

	releasePath := filepath.Join(dir, "release-"+version+".json")
	releaseBytes, err := marshalJSON(release)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(releasePath, releaseBytes, 0o644); err != nil {
		t.Fatal(err)
	}

	envelopePath := filepath.Join(dir, "envelope-"+version+".json")
	if _, err := signRelease(
		releasePath,
		privatePath,
		trustPath,
		envelopePath,
		"runtime-components-activation-test-1",
	); err != nil {
		t.Fatal(err)
	}
	return packagePath, envelopePath, release
}

func makeActivationFixture(t *testing.T, version string, sourceCommit string) activationFixture {
	t.Helper()
	dir := t.TempDir()
	root := filepath.Join(dir, "slots")
	privatePath := filepath.Join(dir, "private.pem")
	trustPath := filepath.Join(dir, "trust.json")
	if _, err := generateKey(
		privatePath,
		trustPath,
		"runtime-components-activation-test-1",
	); err != nil {
		t.Fatal(err)
	}
	packagePath, envelopePath, release := writeComponentSlotCandidate(
		t,
		dir,
		privatePath,
		trustPath,
		version,
		sourceCommit,
	)
	_, slot, _, err := stageComponent(envelopePath, trustPath, packagePath, root)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { allowTestTreeCleanup(root) })
	return activationFixture{
		dir:          dir,
		root:         root,
		privatePath:  privatePath,
		trustPath:    trustPath,
		envelopePath: envelopePath,
		packagePath:  packagePath,
		release:      release,
		slot:         slot,
	}
}

func addActivationCandidate(
	t *testing.T,
	fixture activationFixture,
	version string,
	sourceCommit string,
) (releaseDescriptor, string) {
	t.Helper()
	// The previous canonical package is no longer needed after immutable staging.
	if err := os.Remove(fixture.packagePath); err != nil && !os.IsNotExist(err) {
		t.Fatal(err)
	}
	packagePath, envelopePath, release := writeComponentSlotCandidate(
		t,
		fixture.dir,
		fixture.privatePath,
		fixture.trustPath,
		version,
		sourceCommit,
	)
	_, slot, _, err := stageComponent(
		envelopePath,
		fixture.trustPath,
		packagePath,
		fixture.root,
	)
	if err != nil {
		t.Fatal(err)
	}
	return release, slot
}

func TestActivationRejectsBundledReleaseMode(t *testing.T) {
	fixture := makeFixture(t)
	root := filepath.Join(fixture.dir, "slots")
	t.Cleanup(func() { allowTestTreeCleanup(root) })
	_, slot, _, err := stageComponent(
		fixture.envelopePath,
		fixture.trustPath,
		fixture.packagePath,
		root,
	)
	if err != nil {
		t.Fatal(err)
	}
	_, err = armPendingState(slot, fixture.trustPath, root)
	if err == nil || !strings.Contains(err.Error(), "release_mode=component-slot") {
		t.Fatalf("bundled activation error = %v", err)
	}
}

func TestPendingRequiresExactHealthBeforePromotion(t *testing.T) {
	fixture := makeActivationFixture(t, "0.4.0", strings.Repeat("1", 40))
	state, err := armPendingState(fixture.slot, fixture.trustPath, fixture.root)
	if err != nil {
		t.Fatal(err)
	}
	if state.Pending == nil || state.PendingHealth != "unknown" || state.Current != nil {
		t.Fatalf("unexpected armed state: %+v", state)
	}

	if _, err := promotePendingState(fixture.root, "internet", fixture.trustPath); err == nil {
		t.Fatal("promotion succeeded without pending health")
	}
	if _, err := recordPendingHealth(
		fixture.root,
		"internet",
		slotIdentity{Version: "0.4.0", SourceCommit: strings.Repeat("2", 40)},
		"healthy",
	); err == nil {
		t.Fatal("health accepted for wrong source identity")
	}

	state, err = recordPendingHealth(
		fixture.root,
		"internet",
		identityFromRelease(fixture.release),
		"healthy",
	)
	if err != nil {
		t.Fatal(err)
	}
	if state.PendingHealth != "healthy" {
		t.Fatalf("pending health = %q", state.PendingHealth)
	}

	state, err = promotePendingState(fixture.root, "internet", fixture.trustPath)
	if err != nil {
		t.Fatal(err)
	}
	if state.Current == nil || !sameSlotIdentity(state.Current, &slotIdentity{
		Version:      "0.4.0",
		SourceCommit: strings.Repeat("1", 40),
	}) {
		t.Fatalf("unexpected current after promotion: %+v", state)
	}
	if state.Previous != nil || state.Pending != nil || state.PendingHealth != "unknown" {
		t.Fatalf("promotion left stale state: %+v", state)
	}
}

func TestFirstRollbackReturnsToBundledFallback(t *testing.T) {
	fixture := makeActivationFixture(t, "0.4.0", strings.Repeat("3", 40))
	if _, err := armPendingState(fixture.slot, fixture.trustPath, fixture.root); err != nil {
		t.Fatal(err)
	}
	if _, err := recordPendingHealth(
		fixture.root,
		"internet",
		identityFromRelease(fixture.release),
		"healthy",
	); err != nil {
		t.Fatal(err)
	}
	if _, err := promotePendingState(fixture.root, "internet", fixture.trustPath); err != nil {
		t.Fatal(err)
	}

	state, err := rollbackCurrentState(fixture.root, "internet", fixture.trustPath)
	if err != nil {
		t.Fatal(err)
	}
	if state.Current != nil || state.Previous != nil || state.Rejected == nil {
		t.Fatalf("rollback did not return to bundled fallback: %+v", state)
	}
	if state.Rejected.Version != "0.4.0" {
		t.Fatalf("rejected version = %q", state.Rejected.Version)
	}

	resolved, slot, bundled, err := resolveCurrentState(
		fixture.root,
		"internet",
		fixture.trustPath,
	)
	if err != nil {
		t.Fatal(err)
	}
	if !bundled || slot != "" || resolved.Current != nil {
		t.Fatalf("bundled fallback did not resolve: bundled=%t slot=%q state=%+v", bundled, slot, resolved)
	}
}

func TestSecondPromotionAndRollbackRestoreVerifiedPrevious(t *testing.T) {
	fixture := makeActivationFixture(t, "0.4.0", strings.Repeat("4", 40))
	if _, err := armPendingState(fixture.slot, fixture.trustPath, fixture.root); err != nil {
		t.Fatal(err)
	}
	if _, err := recordPendingHealth(
		fixture.root,
		"internet",
		identityFromRelease(fixture.release),
		"healthy",
	); err != nil {
		t.Fatal(err)
	}
	if _, err := promotePendingState(fixture.root, "internet", fixture.trustPath); err != nil {
		t.Fatal(err)
	}

	secondRelease, secondSlot := addActivationCandidate(
		t,
		fixture,
		"0.5.0",
		strings.Repeat("5", 40),
	)
	if _, err := armPendingState(secondSlot, fixture.trustPath, fixture.root); err != nil {
		t.Fatal(err)
	}
	if _, err := recordPendingHealth(
		fixture.root,
		"internet",
		identityFromRelease(secondRelease),
		"healthy",
	); err != nil {
		t.Fatal(err)
	}
	state, err := promotePendingState(fixture.root, "internet", fixture.trustPath)
	if err != nil {
		t.Fatal(err)
	}
	if state.Current == nil || state.Current.Version != "0.5.0" {
		t.Fatalf("second version not current: %+v", state)
	}
	if state.Previous == nil || state.Previous.Version != "0.4.0" {
		t.Fatalf("first version not preserved as previous: %+v", state)
	}

	state, err = rollbackCurrentState(fixture.root, "internet", fixture.trustPath)
	if err != nil {
		t.Fatal(err)
	}
	if state.Current == nil || state.Current.Version != "0.4.0" {
		t.Fatalf("rollback did not restore previous: %+v", state)
	}
	if state.Rejected == nil || state.Rejected.Version != "0.5.0" || state.Previous != nil {
		t.Fatalf("rollback state is invalid: %+v", state)
	}
}

func TestResolveCurrentReverifiesSlotAndDetectsTampering(t *testing.T) {
	fixture := makeActivationFixture(t, "0.4.0", strings.Repeat("6", 40))
	if _, err := armPendingState(fixture.slot, fixture.trustPath, fixture.root); err != nil {
		t.Fatal(err)
	}
	if _, err := recordPendingHealth(
		fixture.root,
		"internet",
		identityFromRelease(fixture.release),
		"healthy",
	); err != nil {
		t.Fatal(err)
	}
	if _, err := promotePendingState(fixture.root, "internet", fixture.trustPath); err != nil {
		t.Fatal(err)
	}

	state, slot, bundled, err := resolveCurrentState(fixture.root, "internet", fixture.trustPath)
	if err != nil {
		t.Fatal(err)
	}
	if bundled || state.Current == nil || filepath.Clean(slot) != filepath.Clean(fixture.slot) {
		t.Fatalf("current slot did not resolve: bundled=%t slot=%q state=%+v", bundled, slot, state)
	}

	runtimePath := filepath.Join(slot, "system", "apps", "internet", "runtime.mjs")
	if runtime.GOOS != "windows" {
		if err := os.Chmod(runtimePath, 0o644); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(runtimePath, []byte("tampered\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, _, _, err := resolveCurrentState(fixture.root, "internet", fixture.trustPath); err == nil {
		t.Fatal("tampered current slot unexpectedly resolved")
	}
}

func TestPendingMustBeRejectedBeforeRollback(t *testing.T) {
	fixture := makeActivationFixture(t, "0.4.0", strings.Repeat("7", 40))
	if _, err := armPendingState(fixture.slot, fixture.trustPath, fixture.root); err != nil {
		t.Fatal(err)
	}
	if _, err := rollbackCurrentState(fixture.root, "internet", fixture.trustPath); err == nil {
		t.Fatal("rollback accepted while a pending candidate exists")
	}

	wrong := slotIdentity{Version: "0.4.0", SourceCommit: strings.Repeat("8", 40)}
	if _, err := rejectPendingState(fixture.root, "internet", wrong); err == nil {
		t.Fatal("reject accepted the wrong pending identity")
	}
	state, err := rejectPendingState(
		fixture.root,
		"internet",
		identityFromRelease(fixture.release),
	)
	if err != nil {
		t.Fatal(err)
	}
	if state.Pending != nil || state.Rejected == nil || state.PendingHealth != "unknown" {
		t.Fatalf("pending rejection state invalid: %+v", state)
	}
}

func TestActivationLockAndCorruptStateFailClosed(t *testing.T) {
	fixture := makeActivationFixture(t, "0.4.0", strings.Repeat("9", 40))
	componentRoot := filepath.Join(fixture.root, "internet")
	lockPath := filepath.Join(componentRoot, activationLockName)
	if err := os.Mkdir(lockPath, 0o700); err != nil {
		t.Fatal(err)
	}
	if _, err := armPendingState(fixture.slot, fixture.trustPath, fixture.root); err == nil ||
		!strings.Contains(err.Error(), "already locked") {
		t.Fatalf("stale lock error = %v", err)
	}
	if err := os.Remove(lockPath); err != nil {
		t.Fatal(err)
	}

	statePath := filepath.Join(componentRoot, activationStateName)
	if err := os.WriteFile(statePath, []byte("{broken\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := readActivationState(fixture.root, "internet"); err == nil {
		t.Fatal("corrupt activation state unexpectedly loaded")
	}
}

func TestFailedPendingCannotBecomeHealthyWithoutRejection(t *testing.T) {
	fixture := makeActivationFixture(t, "0.4.0", strings.Repeat("a", 40))
	if _, err := armPendingState(fixture.slot, fixture.trustPath, fixture.root); err != nil {
		t.Fatal(err)
	}
	identity := identityFromRelease(fixture.release)
	state, err := recordPendingHealth(
		fixture.root,
		"internet",
		identity,
		"failed",
	)
	if err != nil {
		t.Fatal(err)
	}
	if state.PendingHealth != "failed" {
		t.Fatalf("pending health = %q", state.PendingHealth)
	}
	if _, err := recordPendingHealth(
		fixture.root,
		"internet",
		identity,
		"healthy",
	); err == nil || !strings.Contains(err.Error(), "must be rejected") {
		t.Fatalf("failed -> healthy error = %v", err)
	}
	if _, err := promotePendingState(fixture.root, "internet", fixture.trustPath); err == nil {
		t.Fatal("failed candidate unexpectedly promoted")
	}
}

func TestRejectedIdentityCannotBeRearmed(t *testing.T) {
	fixture := makeActivationFixture(t, "0.4.0", strings.Repeat("b", 40))
	if _, err := armPendingState(fixture.slot, fixture.trustPath, fixture.root); err != nil {
		t.Fatal(err)
	}
	identity := identityFromRelease(fixture.release)
	if _, err := rejectPendingState(fixture.root, "internet", identity); err != nil {
		t.Fatal(err)
	}
	if _, err := armPendingState(fixture.slot, fixture.trustPath, fixture.root); err == nil ||
		!strings.Contains(err.Error(), "previously rejected") {
		t.Fatalf("rearm rejected candidate error = %v", err)
	}
}
