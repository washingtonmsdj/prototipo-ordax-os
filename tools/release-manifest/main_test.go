package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

const testCommit = "0123456789abcdef0123456789abcdef01234567"

func makeArtifact(t *testing.T) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "system.tar")
	if err := os.WriteFile(path, []byte("deterministic-system-tar\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestBuildManifestPinsArtifactIdentity(t *testing.T) {
	artifact := makeArtifact(t)
	manifest, err := buildManifest(artifact, testCommit, "https://example.invalid/system.tar", defaultRepo, defaultRecipe)
	if err != nil {
		t.Fatal(err)
	}
	data, _ := os.ReadFile(artifact)
	digest := sha256.Sum256(data)
	if manifest.Schema != manifestSchema || manifest.SourceCommit != testCommit || manifest.ReleaseID != testCommit {
		t.Fatalf("unexpected manifest identity: %#v", manifest)
	}
	if len(manifest.Artifacts) != 1 {
		t.Fatalf("artifact count = %d", len(manifest.Artifacts))
	}
	got := manifest.Artifacts[0]
	if got.Name != "system.tar" || got.Role != "system" || got.Size != int64(len(data)) || got.SHA256 != hex.EncodeToString(digest[:]) {
		t.Fatalf("unexpected artifact identity: %#v", got)
	}
}

func TestManifestOutputIsDeterministic(t *testing.T) {
	manifest, err := buildManifest(makeArtifact(t), testCommit, "https://example.invalid/system.tar", defaultRepo, defaultRecipe)
	if err != nil {
		t.Fatal(err)
	}
	outA := filepath.Join(t.TempDir(), "a.json")
	outB := filepath.Join(t.TempDir(), "b.json")
	if err := writeManifest(outA, manifest); err != nil {
		t.Fatal(err)
	}
	if err := writeManifest(outB, manifest); err != nil {
		t.Fatal(err)
	}
	a, _ := os.ReadFile(outA)
	b, _ := os.ReadFile(outB)
	if !bytes.Equal(a, b) {
		t.Fatal("manifest JSON changed between identical writes")
	}
	var decoded Manifest
	if err := json.Unmarshal(a, &decoded); err != nil {
		t.Fatal(err)
	}
	if decoded.SourceCommit != testCommit {
		t.Fatal("written manifest lost source commit")
	}
}

func TestNonHTTPSArtifactURLIsRejected(t *testing.T) {
	if _, err := buildManifest(makeArtifact(t), testCommit, "http://example.invalid/system.tar", defaultRepo, defaultRecipe); err == nil {
		t.Fatal("non-HTTPS artifact URL was accepted")
	}
}

func TestInvalidSourceCommitIsRejected(t *testing.T) {
	if _, err := buildManifest(makeArtifact(t), "ABC", "https://example.invalid/system.tar", defaultRepo, defaultRecipe); err == nil {
		t.Fatal("invalid source commit was accepted")
	}
}

func TestArtifactMustBeNamedSystemTar(t *testing.T) {
	path := filepath.Join(t.TempDir(), "other.tar")
	if err := os.WriteFile(path, []byte("payload"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := buildManifest(path, testCommit, "https://example.invalid/system.tar", defaultRepo, defaultRecipe); err == nil {
		t.Fatal("non-canonical artifact filename was accepted")
	}
}

func TestArtifactSymlinkIsRejected(t *testing.T) {
	root := t.TempDir()
	real := filepath.Join(root, "real.tar")
	if err := os.WriteFile(real, []byte("payload"), 0o644); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(root, "system.tar")
	if err := os.Symlink(real, link); err != nil {
		if runtime.GOOS == "windows" {
			t.Skipf("symlink unavailable: %v", err)
		}
		t.Fatal(err)
	}
	if _, err := buildManifest(link, testCommit, "https://example.invalid/system.tar", defaultRepo, defaultRecipe); err == nil {
		t.Fatal("symlink artifact was accepted")
	}
}

func TestOutputOverwriteIsRejected(t *testing.T) {
	manifest, err := buildManifest(makeArtifact(t), testCommit, "https://example.invalid/system.tar", defaultRepo, defaultRecipe)
	if err != nil {
		t.Fatal(err)
	}
	out := filepath.Join(t.TempDir(), "release-manifest.json")
	if err := os.WriteFile(out, []byte("sentinel"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := writeManifest(out, manifest); err == nil {
		t.Fatal("existing manifest output was overwritten")
	}
	data, _ := os.ReadFile(out)
	if string(data) != "sentinel" {
		t.Fatal("existing output changed")
	}
}

func TestBuildPortableManifestPinsEROFSIdentityWithoutChangingV1(t *testing.T) {
	root := t.TempDir()
	artifact := filepath.Join(root, "system.erofs")
	payload := []byte("deterministic-erofs-candidate\n")
	if err := os.WriteFile(artifact, payload, 0o644); err != nil {
		t.Fatal(err)
	}
	manifest, err := buildPortableManifest(
		artifact,
		testCommit,
		"https://example.invalid/system.erofs",
		defaultRepo,
		defaultPortableRecipe,
	)
	if err != nil {
		t.Fatal(err)
	}
	digest := sha256.Sum256(payload)
	if manifest.Schema != manifestSchemaV2 {
		t.Fatalf("portable schema = %q", manifest.Schema)
	}
	if manifest.ProductMode != "usb" || manifest.StorageProfile != "portable-usb-v2" || manifest.RuntimeFormat != "erofs" {
		t.Fatalf("portable identity mismatch: %#v", manifest)
	}
	if len(manifest.Artifacts) != 1 {
		t.Fatalf("portable artifact count = %d", len(manifest.Artifacts))
	}
	got := manifest.Artifacts[0]
	if got.Name != "system.erofs" || got.Role != "system-image" || got.SHA256 != hex.EncodeToString(digest[:]) || got.Size != int64(len(payload)) {
		t.Fatalf("portable artifact mismatch: %#v", got)
	}

	v1, err := buildManifest(makeArtifact(t), testCommit, "https://example.invalid/system.tar", defaultRepo, defaultRecipe)
	if err != nil {
		t.Fatal(err)
	}
	if v1.Schema != manifestSchema || v1.ProductMode != "" || v1.StorageProfile != "" || v1.RuntimeFormat != "" {
		t.Fatalf("v1 semantics drifted: %#v", v1)
	}
}

func TestPortableManifestRejectsWrongArtifactName(t *testing.T) {
	path := filepath.Join(t.TempDir(), "other.erofs")
	if err := os.WriteFile(path, []byte("payload"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := buildPortableManifest(
		path,
		testCommit,
		"https://example.invalid/system.erofs",
		defaultRepo,
		defaultPortableRecipe,
	); err == nil {
		t.Fatal("portable manifest accepted non-canonical artifact name")
	}
}


func TestBuildPortableRuntimeManifestV3PinsCanonicalSystemAndRuntime(t *testing.T) {
	root := t.TempDir()
	systemPath := filepath.Join(root, "system.erofs")
	runtimePath := filepath.Join(root, "native-surface-runtime.erofs")
	systemPayload := []byte("deterministic-system-erofs\n")
	runtimePayload := []byte("deterministic-surface-runtime-erofs\n")
	if err := os.WriteFile(systemPath, systemPayload, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(runtimePath, runtimePayload, 0o644); err != nil {
		t.Fatal(err)
	}

	manifest, err := buildPortableRuntimeManifest(
		systemPath,
		runtimePath,
		testCommit,
		"https://example.invalid/system.erofs",
		"https://example.invalid/native-surface-runtime.erofs",
		defaultRepo,
		defaultPortableRuntimeRecipe,
	)
	if err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != manifestSchemaV3 ||
		manifest.ProductMode != "usb" ||
		manifest.StorageProfile != "portable-usb-v2" ||
		manifest.RuntimeFormat != "erofs" {
		t.Fatalf("unexpected v3 identity: %#v", manifest)
	}
	if len(manifest.Artifacts) != 2 {
		t.Fatalf("v3 artifact count = %d", len(manifest.Artifacts))
	}
	systemDigest := sha256.Sum256(systemPayload)
	runtimeDigest := sha256.Sum256(runtimePayload)
	if got := manifest.Artifacts[0]; got.Name != "system.erofs" ||
		got.Role != "system-image" ||
		got.SHA256 != hex.EncodeToString(systemDigest[:]) ||
		got.Size != int64(len(systemPayload)) {
		t.Fatalf("unexpected v3 system artifact: %#v", got)
	}
	if got := manifest.Artifacts[1]; got.Name != "native-surface-runtime.erofs" ||
		got.Role != "surface-runtime" ||
		got.SHA256 != hex.EncodeToString(runtimeDigest[:]) ||
		got.Size != int64(len(runtimePayload)) {
		t.Fatalf("unexpected v3 runtime artifact: %#v", got)
	}

	v2, err := buildPortableManifest(
		systemPath,
		testCommit,
		"https://example.invalid/system.erofs",
		defaultRepo,
		defaultPortableRecipe,
	)
	if err != nil {
		t.Fatal(err)
	}
	if v2.Schema != manifestSchemaV2 || len(v2.Artifacts) != 1 {
		t.Fatalf("v2 semantics drifted after v3 support: %#v", v2)
	}
}

func TestPortableRuntimeManifestV3RejectsWrongRuntimeNameAndNonHTTPSURL(t *testing.T) {
	root := t.TempDir()
	systemPath := filepath.Join(root, "system.erofs")
	runtimePath := filepath.Join(root, "wrong-runtime.erofs")
	if err := os.WriteFile(systemPath, []byte("system"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(runtimePath, []byte("runtime"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := buildPortableRuntimeManifest(
		systemPath,
		runtimePath,
		testCommit,
		"https://example.invalid/system.erofs",
		"https://example.invalid/native-surface-runtime.erofs",
		defaultRepo,
		defaultPortableRuntimeRecipe,
	); err == nil {
		t.Fatal("v3 accepted non-canonical Surface runtime filename")
	}

	runtimePath = filepath.Join(root, "native-surface-runtime.erofs")
	if err := os.WriteFile(runtimePath, []byte("runtime"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := buildPortableRuntimeManifest(
		systemPath,
		runtimePath,
		testCommit,
		"https://example.invalid/system.erofs",
		"http://example.invalid/native-surface-runtime.erofs",
		defaultRepo,
		defaultPortableRuntimeRecipe,
	); err == nil {
		t.Fatal("v3 accepted non-HTTPS Surface runtime URL")
	}
}


func validLocalAISourceLockFixture() []byte {
	return []byte(`{
  "$schema": "prototype-ordax.local-ai-source-lock/1",
  "engine": {
    "id": "llama.cpp",
    "repository": "https://github.com/ggml-org/llama.cpp",
    "commit": "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2",
    "license": "MIT"
  },
  "model": {
    "id": "qwen3.5-0.8b-q4_0",
    "repository": "ggml-org/Qwen3.5-0.8B-GGUF",
    "filename": "Qwen3.5-0.8B-Q4_0.gguf",
    "sha256": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
    "size_bytes": 563036064,
    "license": "Apache-2.0",
    "upstream_revision": "9447f74"
  }
}
`)
}

func TestBuildPortableAIManifestV4PinsRuntimeAndSourceLock(t *testing.T) {
	root := t.TempDir()
	systemPath := filepath.Join(root, "system.erofs")
	runtimePath := filepath.Join(root, "native-surface-runtime.erofs")
	aiPath := filepath.Join(root, "local-ai-runtime.erofs")
	lockPath := filepath.Join(root, "source-lock.json")
	systemPayload := []byte("system-v4\n")
	runtimePayload := []byte("surface-v4\n")
	aiPayload := []byte("local-ai-v4\n")
	for path, payload := range map[string][]byte{
		systemPath: systemPayload,
		runtimePath: runtimePayload,
		aiPath: aiPayload,
		lockPath: validLocalAISourceLockFixture(),
	} {
		if err := os.WriteFile(path, payload, 0o644); err != nil {
			t.Fatal(err)
		}
	}

	manifest, err := buildPortableAIManifest(
		systemPath,
		runtimePath,
		aiPath,
		lockPath,
		testCommit,
		"https://example.invalid/system.erofs",
		"https://example.invalid/native-surface-runtime.erofs",
		"https://example.invalid/local-ai-runtime.erofs",
		defaultRepo,
		defaultPortableAIRuntimeRecipe,
	)
	if err != nil {
		t.Fatal(err)
	}
	if manifest.Schema != manifestSchemaV4 || len(manifest.Artifacts) != 3 {
		t.Fatalf("unexpected v4 manifest identity: %#v", manifest)
	}
	if got := manifest.Artifacts[2]; got.Name != "local-ai-runtime.erofs" || got.Role != "local-ai-runtime" {
		t.Fatalf("unexpected v4 local AI artifact: %#v", got)
	}
	aiDigest := sha256.Sum256(aiPayload)
	if manifest.Artifacts[2].SHA256 != hex.EncodeToString(aiDigest[:]) ||
		manifest.Artifacts[2].Size != int64(len(aiPayload)) {
		t.Fatalf("local AI artifact identity drifted: %#v", manifest.Artifacts[2])
	}
	if manifest.LocalAI == nil {
		t.Fatal("v4 manifest lost local_ai binding")
	}
	lockDigest := sha256.Sum256(validLocalAISourceLockFixture())
	if manifest.LocalAI.SourceLockSHA256 != hex.EncodeToString(lockDigest[:]) {
		t.Fatalf("source lock digest mismatch: %#v", manifest.LocalAI)
	}
	if manifest.LocalAI.Contract != "ordax.local-ai/1" ||
		manifest.LocalAI.EngineID != "llama.cpp" ||
		manifest.LocalAI.EngineSourceCommit != "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2" ||
		manifest.LocalAI.ModelID != "qwen3.5-0.8b-q4_0" ||
		manifest.LocalAI.ModelSHA256 != "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf" ||
		manifest.LocalAI.ModelSize != 563036064 {
		t.Fatalf("local AI source/model binding drifted: %#v", manifest.LocalAI)
	}
}

func TestPortableAIManifestV4RejectsInvalidSourceLock(t *testing.T) {
	root := t.TempDir()
	systemPath := filepath.Join(root, "system.erofs")
	runtimePath := filepath.Join(root, "native-surface-runtime.erofs")
	aiPath := filepath.Join(root, "local-ai-runtime.erofs")
	lockPath := filepath.Join(root, "source-lock.json")
	for path, payload := range map[string][]byte{
		systemPath: []byte("system"),
		runtimePath: []byte("surface"),
		aiPath: []byte("ai"),
	} {
		if err := os.WriteFile(path, payload, 0o644); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(lockPath, []byte(`{"$schema":"prototype-ordax.local-ai-source-lock/1","engine":{"id":"llama.cpp","repository":"https://github.com/ggml-org/llama.cpp","commit":"bad","license":"MIT"},"model":{"id":"m","repository":"r","filename":"m.gguf","sha256":"bad","size_bytes":1,"license":"Apache-2.0","upstream_revision":"9447f74"}}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := buildPortableAIManifest(
		systemPath,
		runtimePath,
		aiPath,
		lockPath,
		testCommit,
		"https://example.invalid/system.erofs",
		"https://example.invalid/native-surface-runtime.erofs",
		"https://example.invalid/local-ai-runtime.erofs",
		defaultRepo,
		defaultPortableAIRuntimeRecipe,
	); err == nil {
		t.Fatal("v4 accepted invalid local AI source lock")
	}
}
