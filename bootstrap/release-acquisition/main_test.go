package main

import (
	"archive/tar"
	"bytes"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const testCommit = "0123456789abcdef0123456789abcdef01234567"

type archiveEntry struct {
	name     string
	mode     int64
	typeflag byte
	body     []byte
	linkname string
}

func makeSystemTar(t *testing.T, entries ...archiveEntry) []byte {
	t.Helper()
	var buffer bytes.Buffer
	writer := tar.NewWriter(&buffer)
	for _, entry := range entries {
		header := &tar.Header{
			Name:     entry.name,
			Mode:     entry.mode,
			Typeflag: entry.typeflag,
			Size:     int64(len(entry.body)),
			Linkname: entry.linkname,
		}
		if entry.typeflag == tar.TypeDir || entry.typeflag == tar.TypeSymlink || entry.typeflag == tar.TypeLink {
			header.Size = 0
		}
		if err := writer.WriteHeader(header); err != nil {
			t.Fatal(err)
		}
		if header.Size > 0 {
			if _, err := writer.Write(entry.body); err != nil {
				t.Fatal(err)
			}
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	return buffer.Bytes()
}

func validSystemTar(t *testing.T) []byte {
	t.Helper()
	return makeSystemTar(t,
		archiveEntry{name: "system/", mode: 0o755, typeflag: tar.TypeDir},
		archiveEntry{name: "system/entrypoint", mode: 0o755, typeflag: tar.TypeReg, body: []byte("#!/bin/sh\necho ordax-test\n")},
		archiveEntry{name: "system/version", mode: 0o644, typeflag: tar.TypeReg, body: []byte("prototype-test\n")},
	)
}

func writeTempArchive(t *testing.T, data []byte) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "system.tar")
	if err := os.WriteFile(path, data, 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func testKeys(t *testing.T) (TrustAnchor, ed25519.PublicKey, ed25519.PrivateKey) {
	t.Helper()
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	trust := TrustAnchor{
		Schema:       trustSchema,
		KeyID:        "prototype-1",
		PublicKeyB64: base64.StdEncoding.EncodeToString(pub),
	}
	return trust, pub, priv
}

func signedEnvelope(t *testing.T, manifest Manifest, keyID string, priv ed25519.PrivateKey) []byte {
	t.Helper()
	payload, err := json.Marshal(manifest)
	if err != nil {
		t.Fatal(err)
	}
	envelope := Envelope{
		Schema:    envelopeSchema,
		Payload:   payload,
		Signature: ed25519.Sign(priv, payload),
		KeyID:     keyID,
	}
	data, err := json.Marshal(envelope)
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func validPortableEROFS() []byte {
	data := make([]byte, 4096)
	copy(data[1024:1028], []byte{0xe2, 0xe1, 0xf5, 0xe0})
	copy(data[2048:], []byte("ORDAX-PORTABLE-EROFS-PROOF"))
	return data
}

func manifestForPortable(rawURL string, data []byte) Manifest {
	digest := sha256.Sum256(data)
	return Manifest{
		Schema:              manifestSchemaV2,
		SourceRepository:    defaultRepo,
		SourceCommit:        testCommit,
		ReleaseID:           testCommit,
		CreatedFromCIRecipe: "release/portable-usb-v2/1",
		ProductMode:         "usb",
		StorageProfile:      "portable-usb-v2",
		RuntimeFormat:       "erofs",
		Artifacts: []Artifact{{
			Name:   "system.erofs",
			Role:   "system-image",
			URL:    rawURL,
			SHA256: hex.EncodeToString(digest[:]),
			Size:   int64(len(data)),
		}},
	}
}

func manifestForPortableV3(systemURL, runtimeURL string, systemData, runtimeData []byte) Manifest {
	systemDigest := sha256.Sum256(systemData)
	runtimeDigest := sha256.Sum256(runtimeData)
	return Manifest{
		Schema:              manifestSchemaV3,
		SourceRepository:    defaultRepo,
		SourceCommit:        testCommit,
		ReleaseID:           testCommit,
		CreatedFromCIRecipe: "release/portable-usb-v2-runtime/1",
		ProductMode:         "usb",
		StorageProfile:      "portable-usb-v2",
		RuntimeFormat:       "erofs",
		Artifacts: []Artifact{
			{
				Name:   "system.erofs",
				Role:   "system-image",
				URL:    systemURL,
				SHA256: hex.EncodeToString(systemDigest[:]),
				Size:   int64(len(systemData)),
			},
			{
				Name:   "native-surface-runtime.erofs",
				Role:   "surface-runtime",
				URL:    runtimeURL,
				SHA256: hex.EncodeToString(runtimeDigest[:]),
				Size:   int64(len(runtimeData)),
			},
		},
	}
}

func manifestFor(rawURL string, data []byte) Manifest {
	digest := sha256.Sum256(data)
	return Manifest{
		Schema:              manifestSchema,
		SourceRepository:    defaultRepo,
		SourceCommit:        testCommit,
		ReleaseID:           testCommit,
		CreatedFromCIRecipe: "release-agent-test/1",
		Artifacts: []Artifact{{
			Name:   "system.tar",
			Role:   "system",
			URL:    rawURL,
			SHA256: hex.EncodeToString(digest[:]),
			Size:   int64(len(data)),
		}},
	}
}

func TestVerifyEnvelopeAcceptsExactSignedPayload(t *testing.T) {
	trust, pub, priv := testKeys(t)
	m := manifestFor("https://example.invalid/system.tar", []byte("payload"))
	data := signedEnvelope(t, m, trust.KeyID, priv)
	got, payload, err := verifyEnvelope(data, trust, pub, defaultRepo)
	if err != nil {
		t.Fatal(err)
	}
	if got.SourceCommit != testCommit || len(payload) == 0 {
		t.Fatalf("unexpected verified manifest: %#v", got)
	}
}

func TestVerifyEnvelopeRejectsTamperedPayload(t *testing.T) {
	trust, pub, priv := testKeys(t)
	m := manifestFor("https://example.invalid/system.tar", []byte("payload"))
	data := signedEnvelope(t, m, trust.KeyID, priv)
	var envelope Envelope
	if err := json.Unmarshal(data, &envelope); err != nil {
		t.Fatal(err)
	}
	envelope.Payload[0] ^= 1
	data, _ = json.Marshal(envelope)
	if _, _, err := verifyEnvelope(data, trust, pub, defaultRepo); err == nil {
		t.Fatal("tampered signed payload was accepted")
	}
}

func TestManifestRejectsNonHTTPSArtifact(t *testing.T) {
	m := manifestFor("http://example.invalid/system.tar", []byte("payload"))
	if err := validateManifest(m, defaultRepo); err == nil {
		t.Fatal("HTTP artifact URL was accepted")
	}
}

func TestManifestRequiresExactlyOneCanonicalSystemTar(t *testing.T) {
	m := manifestFor("https://example.invalid/system.tar", []byte("payload"))
	m.Artifacts[0].Name = "other.tar"
	if err := validateManifest(m, defaultRepo); err == nil {
		t.Fatal("non-canonical release artifact was accepted")
	}
	m = manifestFor("https://example.invalid/system.tar", []byte("payload"))
	m.Artifacts = append(m.Artifacts, m.Artifacts[0])
	if err := validateManifest(m, defaultRepo); err == nil {
		t.Fatal("multiple v1 release artifacts were accepted")
	}
	m = manifestFor("https://example.invalid/system.tar", []byte("payload"))
	if err := validateManifest(m, "someone/else"); err == nil {
		t.Fatal("repository mismatch was accepted")
	}
}

func TestExtractSystemArchiveRejectsTraversal(t *testing.T) {
	archive := makeSystemTar(t,
		archiveEntry{name: "system/", mode: 0o755, typeflag: tar.TypeDir},
		archiveEntry{name: "system/../escape", mode: 0o644, typeflag: tar.TypeReg, body: []byte("escape")},
		archiveEntry{name: "system/entrypoint", mode: 0o755, typeflag: tar.TypeReg, body: []byte("#!/bin/sh\n")},
	)
	root := t.TempDir()
	if err := extractSystemArchive(writeTempArchive(t, archive), root); err == nil {
		t.Fatal("path traversal archive was accepted")
	}
	if _, err := os.Stat(filepath.Join(root, "escape")); !os.IsNotExist(err) {
		t.Fatal("path traversal wrote outside system root")
	}
}

func TestExtractSystemArchiveRejectsSymlink(t *testing.T) {
	archive := makeSystemTar(t,
		archiveEntry{name: "system/", mode: 0o755, typeflag: tar.TypeDir},
		archiveEntry{name: "system/entrypoint", mode: 0o755, typeflag: tar.TypeReg, body: []byte("#!/bin/sh\n")},
		archiveEntry{name: "system/link", mode: 0o777, typeflag: tar.TypeSymlink, linkname: "/etc/passwd"},
	)
	if err := extractSystemArchive(writeTempArchive(t, archive), t.TempDir()); err == nil {
		t.Fatal("symlink archive entry was accepted")
	}
}

func TestExtractSystemArchiveRequiresBootableEntrypoint(t *testing.T) {
	archive := makeSystemTar(t,
		archiveEntry{name: "system/", mode: 0o755, typeflag: tar.TypeDir},
		archiveEntry{name: "system/version", mode: 0o644, typeflag: tar.TypeReg, body: []byte("no-entrypoint\n")},
	)
	if err := extractSystemArchive(writeTempArchive(t, archive), t.TempDir()); err == nil {
		t.Fatal("archive without system/entrypoint was accepted")
	}
}

func TestInspectReleaseVerifiesChannelWithoutDownloadingArtifact(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	artifactRequested := false
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		artifactRequested = true
		t.Fatal("inspect must not request release artifact")
	})

	receipt, err := inspectRelease(
		server.Client(),
		server.URL+"/release.json",
		trust,
		pub,
		defaultRepo,
	)
	if err != nil {
		t.Fatal(err)
	}
	if artifactRequested {
		t.Fatal("inspect downloaded artifact")
	}
	if receipt.Status != "verified" || receipt.SourceCommit != testCommit {
		t.Fatalf("unexpected inspect receipt: %#v", receipt)
	}
	if receipt.ReleaseID != testCommit || receipt.ArtifactName != "system.tar" {
		t.Fatalf("inspect receipt lost signed manifest identity: %#v", receipt)
	}
	if receipt.ArtifactURL != server.URL+"/system.tar" {
		t.Fatalf("unexpected artifact URL: %s", receipt.ArtifactURL)
	}
	if receipt.ArtifactSHA256 != m.Artifacts[0].SHA256 || receipt.ArtifactSize != int64(len(artifact)) {
		t.Fatalf("inspect receipt lost signed artifact integrity: %#v", receipt)
	}
}

func TestInspectReleaseRejectsTamperedEnvelopeWithoutArtifactRequest(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	envelope[len(envelope)/2] ^= 0x01
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("invalid inspect must not request release artifact")
	})

	if _, err := inspectRelease(
		server.Client(),
		server.URL+"/release.json",
		trust,
		pub,
		defaultRepo,
	); err == nil {
		t.Fatal("tampered release envelope was inspected as valid")
	}
}

func TestActivateExactRevalidatesMaterializedReleaseAndPreservesPreviousCommit(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})

	root := t.TempDir()
	if _, err := materialize(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err != nil {
		t.Fatal(err)
	}

	previous := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	previousRoot := filepath.Join(root, "releases", previous, "system")
	if err := os.MkdirAll(previousRoot, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(previousRoot, "entrypoint"), []byte("#!/bin/sh\nexit 0\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join("releases", previous), filepath.Join(root, "current")); err != nil {
		t.Fatal(err)
	}

	receipt, err := activateExact(root, trust, pub, defaultRepo, testCommit)
	if err != nil {
		t.Fatal(err)
	}
	if receipt.Status != "activated-exact" || receipt.SourceCommit != testCommit {
		t.Fatalf("unexpected exact activation receipt: %#v", receipt)
	}
	if receipt.PreviousCommit != previous || receipt.Idempotent {
		t.Fatalf("exact activation lost previous known-good: %#v", receipt)
	}
	current, err := os.Readlink(filepath.Join(root, "current"))
	if err != nil {
		t.Fatal(err)
	}
	if current != filepath.Join("releases", testCommit) {
		t.Fatalf("exact activation selected unexpected current: %s", current)
	}
}

func TestActivateExactIsIdempotentForAlreadyCurrentVerifiedRelease(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})

	root := t.TempDir()
	if _, err := materialize(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join("releases", testCommit), filepath.Join(root, "current")); err != nil {
		t.Fatal(err)
	}

	receipt, err := activateExact(root, trust, pub, defaultRepo, testCommit)
	if err != nil {
		t.Fatal(err)
	}
	if !receipt.Idempotent || receipt.PreviousCommit != testCommit {
		t.Fatalf("already-current exact activation was not idempotent: %#v", receipt)
	}
}

func TestActivateExactRejectsTamperedReleaseWithoutChangingCurrent(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})

	root := t.TempDir()
	if _, err := materialize(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err != nil {
		t.Fatal(err)
	}
	previous := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	previousRoot := filepath.Join(root, "releases", previous, "system")
	if err := os.MkdirAll(previousRoot, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(previousRoot, "entrypoint"), []byte("#!/bin/sh\nexit 0\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join("releases", previous), filepath.Join(root, "current")); err != nil {
		t.Fatal(err)
	}

	tampered := filepath.Join(root, "releases", testCommit, "system", "version")
	if err := os.WriteFile(tampered, []byte("tampered\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := activateExact(root, trust, pub, defaultRepo, testCommit); err == nil {
		t.Fatal("tampered materialized release was activated")
	}
	current, err := os.Readlink(filepath.Join(root, "current"))
	if err != nil {
		t.Fatal(err)
	}
	if current != filepath.Join("releases", previous) {
		t.Fatalf("failed exact activation changed known-good current: %s", current)
	}
}

func TestActivateExactRejectsUnsafeCurrentPointerWithoutChangingIt(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})

	root := t.TempDir()
	if _, err := materialize(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink("/tmp/not-an-ordax-release", filepath.Join(root, "current")); err != nil {
		t.Fatal(err)
	}

	if _, err := activateExact(root, trust, pub, defaultRepo, testCommit); err == nil {
		t.Fatal("unsafe current pointer was accepted")
	}
	current, err := os.Readlink(filepath.Join(root, "current"))
	if err != nil {
		t.Fatal(err)
	}
	if current != "/tmp/not-an-ordax-release" {
		t.Fatalf("unsafe current pointer was mutated after rejection: %s", current)
	}
}

func TestInstallMaterializesBootableVerifiedRelease(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	var envelope []byte
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()
	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope = signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})
	root := t.TempDir()
	receipt, err := install(server.Client(), server.URL+"/release.json", root, trust, pub, defaultRepo)
	if err != nil {
		t.Fatal(err)
	}
	if receipt.Idempotent || receipt.SourceCommit != testCommit {
		t.Fatalf("unexpected receipt: %#v", receipt)
	}
	current, err := os.Readlink(filepath.Join(root, "current"))
	if err != nil {
		t.Fatal(err)
	}
	if current != filepath.Join("releases", testCommit) {
		t.Fatalf("unexpected current target: %s", current)
	}
	target := filepath.Join(root, "releases", testCommit)
	entrypoint := filepath.Join(target, "system", "entrypoint")
	entrypointInfo, err := os.Stat(entrypoint)
	if err != nil {
		t.Fatal(err)
	}
	if entrypointInfo.Mode().Perm() != 0o755 || entrypointInfo.Size() == 0 {
		t.Fatal("materialized entrypoint is not bootable")
	}
	archived, err := os.ReadFile(filepath.Join(target, "artifacts", "system.tar"))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(archived, artifact) {
		t.Fatal("preserved release artifact differs from verified system.tar")
	}
	version, err := os.ReadFile(filepath.Join(target, "system", "version"))
	if err != nil {
		t.Fatal(err)
	}
	if string(version) != "prototype-test\n" {
		t.Fatal("materialized system tree differs from archive")
	}
	second, err := install(server.Client(), server.URL+"/release.json", root, trust, pub, defaultRepo)
	if err != nil {
		t.Fatal(err)
	}
	if !second.Idempotent {
		t.Fatal("reinstall of identical release was not idempotent")
	}
}

func TestMaterializeDoesNotActivateCurrent(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()
	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})

	root := t.TempDir()
	old := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	if err := os.MkdirAll(filepath.Join(root, "releases", old), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join("releases", old), filepath.Join(root, "current")); err != nil {
		t.Fatal(err)
	}

	receipt, err := materialize(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	)
	if err != nil {
		t.Fatal(err)
	}
	if receipt.Status != "materialized" || receipt.SourceCommit != testCommit || receipt.Idempotent {
		t.Fatalf("unexpected materialize receipt: %#v", receipt)
	}
	current, err := os.Readlink(filepath.Join(root, "current"))
	if err != nil {
		t.Fatal(err)
	}
	if current != filepath.Join("releases", old) {
		t.Fatalf("materialize changed current pointer: %s", current)
	}
	target := filepath.Join(root, "releases", testCommit)
	if _, err := os.Stat(filepath.Join(target, "system", "entrypoint")); err != nil {
		t.Fatalf("verified release was not materialized: %v", err)
	}
	storedEnvelope, err := os.ReadFile(filepath.Join(target, "release-envelope.json"))
	if err != nil {
		t.Fatalf("verified release envelope was not persisted: %v", err)
	}
	if !bytes.Equal(storedEnvelope, envelope) {
		t.Fatal("persisted release envelope differs from verified signed bytes")
	}
	storedManifest, err := os.ReadFile(filepath.Join(target, "release-manifest.json"))
	if err != nil {
		t.Fatalf("verified release manifest was not persisted: %v", err)
	}
	var decoded Envelope
	if err := json.Unmarshal(envelope, &decoded); err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(storedManifest, decoded.Payload) {
		t.Fatal("persisted manifest differs from signed envelope payload")
	}

	second, err := materialize(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	)
	if err != nil {
		t.Fatal(err)
	}
	if !second.Idempotent {
		t.Fatal("second materialize was not idempotent")
	}
	current, err = os.Readlink(filepath.Join(root, "current"))
	if err != nil {
		t.Fatal(err)
	}
	if current != filepath.Join("releases", old) {
		t.Fatalf("idempotent materialize changed current pointer: %s", current)
	}
}

func TestMaterializeRejectsUnexpectedCommitBeforeRootMutation(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()
	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("artifact must not be requested when signed commit mismatches")
	})

	root := filepath.Join(t.TempDir(), "ordax-root")
	unexpected := "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	if _, err := materialize(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		unexpected,
	); err == nil {
		t.Fatal("signed release for a different commit was materialized")
	}
	if _, err := os.Lstat(root); !os.IsNotExist(err) {
		t.Fatal("commit mismatch mutated the OrdaX root")
	}
}

func TestExistingReleaseRejectsPersistedEnvelopeTampering(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()
	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})
	root := t.TempDir()
	if _, err := materialize(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err != nil {
		t.Fatal(err)
	}
	envelopePath := filepath.Join(root, "releases", testCommit, "release-envelope.json")
	persisted, err := os.ReadFile(envelopePath)
	if err != nil {
		t.Fatal(err)
	}
	persisted[len(persisted)/2] ^= 0x01
	if err := os.WriteFile(envelopePath, persisted, 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := materialize(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err == nil || !strings.Contains(err.Error(), "release envelope differs") {
		t.Fatalf("tampered persisted envelope was accepted: %v", err)
	}
}

func TestExistingReleaseRejectsMaterializedTreeTampering(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validSystemTar(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()
	m := manifestFor(server.URL+"/system.tar", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})
	root := t.TempDir()
	if _, err := install(server.Client(), server.URL+"/release.json", root, trust, pub, defaultRepo); err != nil {
		t.Fatal(err)
	}
	tampered := filepath.Join(root, "releases", testCommit, "system", "version")
	if err := os.WriteFile(tampered, []byte("tampered\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := install(server.Client(), server.URL+"/release.json", root, trust, pub, defaultRepo); err == nil {
		t.Fatal("tampered materialized release was accepted as idempotent")
	}
	current, err := os.Readlink(filepath.Join(root, "current"))
	if err != nil {
		t.Fatal(err)
	}
	if current != filepath.Join("releases", testCommit) {
		t.Fatalf("current pointer changed after tamper detection: %s", current)
	}
}

func TestFailedNewReleasePreservesCurrentKnownGood(t *testing.T) {
	trust, pub, priv := testKeys(t)
	declared := validSystemTar(t)
	served := append([]byte(nil), declared...)
	served[len(served)/2] ^= 0xff
	var envelope []byte
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()
	m := manifestFor(server.URL+"/system.tar", declared)
	envelope = signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.tar", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(served)
	})
	root := t.TempDir()
	old := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	if err := os.MkdirAll(filepath.Join(root, "releases", old), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join("releases", old), filepath.Join(root, "current")); err != nil {
		t.Fatal(err)
	}
	if _, err := install(server.Client(), server.URL+"/release.json", root, trust, pub, defaultRepo); err == nil {
		t.Fatal("corrupt release was installed")
	}
	current, err := os.Readlink(filepath.Join(root, "current"))
	if err != nil {
		t.Fatal(err)
	}
	if current != filepath.Join("releases", old) {
		t.Fatalf("known-good current changed after failed update: %s", current)
	}
	if _, err := os.Stat(filepath.Join(root, "releases", testCommit)); !os.IsNotExist(err) {
		t.Fatal("failed release target survived verification failure")
	}
}

func TestLoadTrustRejectsSymlink(t *testing.T) {
	trust, _, _ := testKeys(t)
	data, _ := json.Marshal(trust)
	dir := t.TempDir()
	real := filepath.Join(dir, "trust.json")
	link := filepath.Join(dir, "trust-link.json")
	if err := os.WriteFile(real, data, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(real, link); err != nil {
		t.Fatal(err)
	}
	if _, _, err := loadTrust(link); err == nil {
		t.Fatal("symlink trust anchor was accepted")
	}
}

func TestManifestV2RequiresExactPortableUSBIdentity(t *testing.T) {
	m := manifestForPortable("https://example.invalid/system.erofs", validPortableEROFS())
	if err := validateManifest(m, defaultRepo); err != nil {
		t.Fatal(err)
	}
	m.StorageProfile = "native-disk"
	if err := validateManifest(m, defaultRepo); err == nil || !strings.Contains(err.Error(), "portable-usb-v2") {
		t.Fatalf("wrong portable storage profile accepted: %v", err)
	}
}

func TestInspectReleaseAcceptsPortableV2WithoutDownloadingArtifact(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validPortableEROFS()
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortable(server.URL+"/system.erofs", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("inspect must not download portable system image")
	})

	receipt, err := inspectRelease(server.Client(), server.URL+"/release.json", trust, pub, defaultRepo)
	if err != nil {
		t.Fatal(err)
	}
	if receipt.ManifestSchema != manifestSchemaV2 ||
		receipt.ProductMode != "usb" ||
		receipt.StorageProfile != "portable-usb-v2" ||
		receipt.RuntimeFormat != "erofs" ||
		receipt.ArtifactName != "system.erofs" ||
		receipt.ArtifactRole != "system-image" {
		t.Fatalf("portable inspect identity mismatch: %#v", receipt)
	}
}

func TestMaterializePortableStoresVerifiedAtomicReleaseWithoutActivation(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validPortableEROFS()
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortable(server.URL+"/system.erofs", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})

	root := filepath.Join(t.TempDir(), ".ordax")
	receipt, err := materializePortable(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	)
	if err != nil {
		t.Fatal(err)
	}
	if receipt.Status != "materialized-portable" || receipt.Idempotent || receipt.ActivationAllowed {
		t.Fatalf("unexpected portable materialize receipt: %#v", receipt)
	}
	expected := filepath.Join(root, "releases", testCommit)
	if receipt.ReleasePath != expected || receipt.ArtifactPath != filepath.Join(expected, "system.erofs") {
		t.Fatalf("portable release path mismatch: %#v", receipt)
	}
	stored, err := os.ReadFile(filepath.Join(expected, "system.erofs"))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(stored, artifact) {
		t.Fatal("stored portable image differs from signed bytes")
	}
	if _, err := os.Lstat(filepath.Join(root, "current")); !os.IsNotExist(err) {
		t.Fatal("portable materialization created a current activation pointer")
	}

	second, err := materializePortable(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	)
	if err != nil {
		t.Fatal(err)
	}
	if !second.Idempotent || second.ActivationAllowed {
		t.Fatalf("portable re-materialization is not safely idempotent: %#v", second)
	}
}

func TestMaterializePortableRejectsInvalidEROFSAndLeavesNoRelease(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := make([]byte, 4096)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortable(server.URL+"/system.erofs", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})

	root := filepath.Join(t.TempDir(), ".ordax")
	if _, err := materializePortable(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err == nil || !strings.Contains(err.Error(), "EROFS") {
		t.Fatalf("invalid EROFS candidate was accepted: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, "releases", testCommit)); !os.IsNotExist(err) {
		t.Fatal("failed portable release survived verification")
	}
	if _, err := os.Lstat(filepath.Join(root, "current")); !os.IsNotExist(err) {
		t.Fatal("failed portable materialization changed activation state")
	}
}

func TestLegacyMaterializeRejectsPortableV2BeforeArtifactDownload(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validPortableEROFS()
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortable(server.URL+"/system.erofs", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("legacy materialize must reject v2 before artifact download")
	})

	root := filepath.Join(t.TempDir(), "ordax")
	if _, err := materialize(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err == nil || !strings.Contains(err.Error(), "materialize-portable") {
		t.Fatalf("legacy materialize accepted portable v2: %v", err)
	}
	if _, err := os.Stat(root); !os.IsNotExist(err) {
		t.Fatal("legacy v2 rejection mutated release root")
	}
}

func TestActivateExactExplicitlyRejectsPortableV2(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validPortableEROFS()
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortable(server.URL+"/system.erofs", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})
	root := filepath.Join(t.TempDir(), ".ordax")
	if _, err := materializePortable(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err != nil {
		t.Fatal(err)
	}

	if _, err := activateExact(root, trust, pub, defaultRepo, testCommit); err == nil ||
		!strings.Contains(err.Error(), "dedicated boot handoff") {
		t.Fatalf("portable v2 activation was not rejected explicitly: %v", err)
	}
	if _, err := os.Lstat(filepath.Join(root, "current")); !os.IsNotExist(err) {
		t.Fatal("portable v2 activation rejection created current pointer")
	}
}

func TestVerifyPortableExactRevalidatesStoredSignedReleaseOffline(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validPortableEROFS()
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortable(server.URL+"/system.erofs", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})
	root := filepath.Join(t.TempDir(), ".ordax")
	if _, err := materializePortable(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err != nil {
		t.Fatal(err)
	}

	receipt, err := verifyPortableExact(root, trust, pub, defaultRepo, testCommit)
	if err != nil {
		t.Fatal(err)
	}
	if receipt.Status != "verified-portable-exact" ||
		receipt.SourceCommit != testCommit ||
		receipt.ActivationAllowed {
		t.Fatalf("unexpected exact portable verification receipt: %#v", receipt)
	}
	if receipt.ArtifactPath != filepath.Join(root, "releases", testCommit, "system.erofs") {
		t.Fatalf("unexpected exact portable artifact path: %s", receipt.ArtifactPath)
	}
}

func TestVerifyPortableExactRejectsTamperedStoredImage(t *testing.T) {
	trust, pub, priv := testKeys(t)
	artifact := validPortableEROFS()
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortable(server.URL+"/system.erofs", artifact)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(artifact)
	})
	root := filepath.Join(t.TempDir(), ".ordax")
	if _, err := materializePortable(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	); err != nil {
		t.Fatal(err)
	}

	image := filepath.Join(root, "releases", testCommit, "system.erofs")
	data, err := os.ReadFile(image)
	if err != nil {
		t.Fatal(err)
	}
	data[len(data)-1] ^= 0x01
	if err := os.WriteFile(image, data, 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := verifyPortableExact(root, trust, pub, defaultRepo, testCommit); err == nil ||
		!strings.Contains(err.Error(), "digest") {
		t.Fatalf("tampered stored portable image was accepted: %v", err)
	}
}


func TestManifestV3RequiresCanonicalSystemAndSurfaceRuntime(t *testing.T) {
	systemData := validPortableEROFS()
	runtimeData := validPortableEROFS()
	runtimeData[len(runtimeData)-1] = 0x7f
	m := manifestForPortableV3(
		"https://example.invalid/system.erofs",
		"https://example.invalid/native-surface-runtime.erofs",
		systemData,
		runtimeData,
	)
	if err := validateManifest(m, defaultRepo); err != nil {
		t.Fatal(err)
	}
	m.Artifacts[0], m.Artifacts[1] = m.Artifacts[1], m.Artifacts[0]
	if err := validateManifest(m, defaultRepo); err == nil {
		t.Fatal("release-manifest/3 accepted reordered artifacts")
	}
}

func TestInspectReleaseV3ExposesBothSignedArtifactsWithoutDownloadingThem(t *testing.T) {
	trust, pub, priv := testKeys(t)
	systemData := validPortableEROFS()
	runtimeData := validPortableEROFS()
	runtimeData[len(runtimeData)-1] = 0x22
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortableV3(
		server.URL+"/system.erofs",
		server.URL+"/native-surface-runtime.erofs",
		systemData,
		runtimeData,
	)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("inspect must not download v3 system image")
	})
	mux.HandleFunc("/native-surface-runtime.erofs", func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("inspect must not download v3 Surface runtime")
	})

	receipt, err := inspectRelease(server.Client(), server.URL+"/release.json", trust, pub, defaultRepo)
	if err != nil {
		t.Fatal(err)
	}
	if receipt.ManifestSchema != manifestSchemaV3 || len(receipt.Artifacts) != 2 {
		t.Fatalf("v3 inspect lost artifact set: %#v", receipt)
	}
	if receipt.Artifacts[1].Name != "native-surface-runtime.erofs" ||
		receipt.Artifacts[1].Role != "surface-runtime" {
		t.Fatalf("v3 inspect lost Surface runtime identity: %#v", receipt.Artifacts)
	}
}

func TestMaterializePortableV3StoresRuntimeByDigestWithoutActivation(t *testing.T) {
	trust, pub, priv := testKeys(t)
	systemData := validPortableEROFS()
	runtimeData := validPortableEROFS()
	runtimeData[len(runtimeData)-1] = 0x33
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortableV3(
		server.URL+"/system.erofs",
		server.URL+"/native-surface-runtime.erofs",
		systemData,
		runtimeData,
	)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(systemData)
	})
	mux.HandleFunc("/native-surface-runtime.erofs", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(runtimeData)
	})

	root := filepath.Join(t.TempDir(), ".ordax")
	receipt, err := materializePortableV3(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	)
	if err != nil {
		t.Fatal(err)
	}
	if receipt.Status != "materialized-portable-v3" ||
		receipt.Idempotent ||
		receipt.ActivationAllowed ||
		receipt.RuntimeReused {
		t.Fatalf("unexpected v3 materialize receipt: %#v", receipt)
	}
	runtimeDigest := m.Artifacts[1].SHA256
	expectedRuntime := filepath.Join(root, "runtimes", "sha256", runtimeDigest, "native-surface-runtime.erofs")
	if receipt.RuntimePath != expectedRuntime {
		t.Fatalf("runtime path mismatch: got=%s expected=%s", receipt.RuntimePath, expectedRuntime)
	}
	refBytes, err := os.ReadFile(filepath.Join(root, "releases", testCommit, "surface-runtime.sha256"))
	if err != nil {
		t.Fatal(err)
	}
	if string(refBytes) != runtimeDigest+"\n" {
		t.Fatalf("stored runtime reference = %q", refBytes)
	}
	if _, err := os.Lstat(filepath.Join(root, "current")); !os.IsNotExist(err) {
		t.Fatal("v3 materialization created an activation pointer")
	}

	verified, err := verifyPortableV3Exact(root, trust, pub, defaultRepo, testCommit)
	if err != nil {
		t.Fatal(err)
	}
	if verified.RuntimePath != expectedRuntime || verified.ActivationAllowed {
		t.Fatalf("unexpected v3 exact verification receipt: %#v", verified)
	}
}

func TestMaterializePortableV3ReusesRuntimeAcrossDifferentSystemReleases(t *testing.T) {
	trust, pub, priv := testKeys(t)
	systemA := validPortableEROFS()
	systemB := append([]byte(nil), systemA...)
	systemB[len(systemB)-2] = 0x44
	runtimeData := append([]byte(nil), systemA...)
	runtimeData[len(runtimeData)-1] = 0x55
	const secondCommit = "1111111111111111111111111111111111111111"

	var activeEnvelope []byte
	var systemData []byte
	systemRequests := 0
	runtimeRequests := 0
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(activeEnvelope)
	})
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) {
		systemRequests++
		_, _ = w.Write(systemData)
	})
	mux.HandleFunc("/native-surface-runtime.erofs", func(w http.ResponseWriter, r *http.Request) {
		runtimeRequests++
		_, _ = w.Write(runtimeData)
	})

	first := manifestForPortableV3(
		server.URL+"/system.erofs",
		server.URL+"/native-surface-runtime.erofs",
		systemA,
		runtimeData,
	)
	activeEnvelope = signedEnvelope(t, first, trust.KeyID, priv)
	systemData = systemA
	root := filepath.Join(t.TempDir(), ".ordax")
	if _, err := materializePortableV3(server.Client(), server.URL+"/release.json", root, trust, pub, defaultRepo, testCommit); err != nil {
		t.Fatal(err)
	}

	second := manifestForPortableV3(
		server.URL+"/system.erofs",
		server.URL+"/native-surface-runtime.erofs",
		systemB,
		runtimeData,
	)
	second.SourceCommit = secondCommit
	second.ReleaseID = secondCommit
	activeEnvelope = signedEnvelope(t, second, trust.KeyID, priv)
	systemData = systemB
	receipt, err := materializePortableV3(server.Client(), server.URL+"/release.json", root, trust, pub, defaultRepo, secondCommit)
	if err != nil {
		t.Fatal(err)
	}
	if !receipt.RuntimeReused {
		t.Fatalf("second release did not report runtime reuse: %#v", receipt)
	}
	if runtimeRequests != 1 {
		t.Fatalf("Surface runtime downloaded %d times; want exactly once", runtimeRequests)
	}
	if systemRequests != 2 {
		t.Fatalf("system image downloaded %d times; want once per release", systemRequests)
	}
	if _, err := os.Stat(filepath.Join(root, "releases", secondCommit, "system.erofs")); err != nil {
		t.Fatal(err)
	}
}

func TestVerifyPortableV3ExactRejectsTamperedContentAddressedRuntime(t *testing.T) {
	trust, pub, priv := testKeys(t)
	systemData := validPortableEROFS()
	runtimeData := append([]byte(nil), systemData...)
	runtimeData[len(runtimeData)-1] = 0x66
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()
	m := manifestForPortableV3(
		server.URL+"/system.erofs",
		server.URL+"/native-surface-runtime.erofs",
		systemData,
		runtimeData,
	)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(envelope) })
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(systemData) })
	mux.HandleFunc("/native-surface-runtime.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(runtimeData) })

	root := filepath.Join(t.TempDir(), ".ordax")
	receipt, err := materializePortableV3(server.Client(), server.URL+"/release.json", root, trust, pub, defaultRepo, testCommit)
	if err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(receipt.RuntimePath)
	if err != nil {
		t.Fatal(err)
	}
	data[len(data)-1] ^= 0x01
	if err := os.WriteFile(receipt.RuntimePath, data, 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := verifyPortableV3Exact(root, trust, pub, defaultRepo, testCommit); err == nil ||
		!strings.Contains(err.Error(), "digest") {
		t.Fatalf("tampered content-addressed runtime was accepted: %v", err)
	}
}


func validLocalAIBindingFixture() *LocalAIBinding {
	return &LocalAIBinding{
		Contract:              "ordax.local-ai/1",
		SourceLockSchema:      "prototype-ordax.local-ai-source-lock/1",
		SourceLockSHA256:      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
		EngineID:              "llama.cpp",
		EngineRepository:      "https://github.com/ggml-org/llama.cpp",
		EngineSourceCommit:    "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2",
		EngineLicense:         "MIT",
		ModelID:               "qwen3.5-0.8b-q4_0",
		ModelRepository:       "ggml-org/Qwen3.5-0.8B-GGUF",
		ModelFilename:         "Qwen3.5-0.8B-Q4_0.gguf",
		ModelUpstreamRevision: "9447f74",
		ModelSHA256:           "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
		ModelSize:             563036064,
		ModelLicense:          "Apache-2.0",
	}
}

func manifestForPortableV4(systemURL, runtimeURL, aiURL string, systemData, runtimeData, aiData []byte) Manifest {
	systemDigest := sha256.Sum256(systemData)
	runtimeDigest := sha256.Sum256(runtimeData)
	aiDigest := sha256.Sum256(aiData)
	return Manifest{
		Schema:              manifestSchemaV4,
		SourceRepository:    defaultRepo,
		SourceCommit:        testCommit,
		ReleaseID:           testCommit,
		CreatedFromCIRecipe: "release/portable-usb-v2-local-ai/1",
		ProductMode:         "usb",
		StorageProfile:      "portable-usb-v2",
		RuntimeFormat:       "erofs",
		Artifacts: []Artifact{
			{
				Name:   "system.erofs",
				Role:   "system-image",
				URL:    systemURL,
				SHA256: hex.EncodeToString(systemDigest[:]),
				Size:   int64(len(systemData)),
			},
			{
				Name:   "native-surface-runtime.erofs",
				Role:   "surface-runtime",
				URL:    runtimeURL,
				SHA256: hex.EncodeToString(runtimeDigest[:]),
				Size:   int64(len(runtimeData)),
			},
			{
				Name:   "local-ai-runtime.erofs",
				Role:   "local-ai-runtime",
				URL:    aiURL,
				SHA256: hex.EncodeToString(aiDigest[:]),
				Size:   int64(len(aiData)),
			},
		},
		LocalAI: validLocalAIBindingFixture(),
	}
}

func TestManifestV4RequiresCanonicalAIArtifactAndBinding(t *testing.T) {
	systemData := validPortableEROFS()
	runtimeData := append([]byte(nil), systemData...)
	runtimeData[len(runtimeData)-1] = 0x71
	aiData := append([]byte(nil), systemData...)
	aiData[len(aiData)-1] = 0x72
	m := manifestForPortableV4(
		"https://example.invalid/system.erofs",
		"https://example.invalid/native-surface-runtime.erofs",
		"https://example.invalid/local-ai-runtime.erofs",
		systemData,
		runtimeData,
		aiData,
	)
	if err := validateManifest(m, defaultRepo); err != nil {
		t.Fatal(err)
	}
	m.Artifacts[1], m.Artifacts[2] = m.Artifacts[2], m.Artifacts[1]
	if err := validateManifest(m, defaultRepo); err == nil {
		t.Fatal("release-manifest/4 accepted reordered runtimes")
	}
	m = manifestForPortableV4(
		"https://example.invalid/system.erofs",
		"https://example.invalid/native-surface-runtime.erofs",
		"https://example.invalid/local-ai-runtime.erofs",
		systemData,
		runtimeData,
		aiData,
	)
	m.LocalAI = nil
	if err := validateManifest(m, defaultRepo); err == nil {
		t.Fatal("release-manifest/4 accepted missing local_ai binding")
	}
	m = manifestForPortableV4(
		"https://example.invalid/system.erofs",
		"https://example.invalid/native-surface-runtime.erofs",
		"https://example.invalid/local-ai-runtime.erofs",
		systemData,
		runtimeData,
		aiData,
	)
	m.LocalAI.ModelSHA256 = "bad"
	if err := validateManifest(m, defaultRepo); err == nil {
		t.Fatal("release-manifest/4 accepted invalid model binding")
	}
}

func TestInspectReleaseV4ExposesAllArtifactsAndBindingWithoutDownloadingThem(t *testing.T) {
	trust, pub, priv := testKeys(t)
	systemData := validPortableEROFS()
	runtimeData := append([]byte(nil), systemData...)
	runtimeData[len(runtimeData)-1] = 0x73
	aiData := append([]byte(nil), systemData...)
	aiData[len(aiData)-1] = 0x74
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortableV4(
		server.URL+"/system.erofs",
		server.URL+"/native-surface-runtime.erofs",
		server.URL+"/local-ai-runtime.erofs",
		systemData,
		runtimeData,
		aiData,
	)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write(envelope)
	})
	for _, path := range []string{"/system.erofs", "/native-surface-runtime.erofs", "/local-ai-runtime.erofs"} {
		p := path
		mux.HandleFunc(p, func(w http.ResponseWriter, r *http.Request) {
			t.Fatalf("inspect must not download v4 artifact %s", p)
		})
	}

	receipt, err := inspectRelease(server.Client(), server.URL+"/release.json", trust, pub, defaultRepo)
	if err != nil {
		t.Fatal(err)
	}
	if receipt.ManifestSchema != manifestSchemaV4 || len(receipt.Artifacts) != 3 || receipt.LocalAI == nil {
		t.Fatalf("v4 inspect lost signed identity: %#v", receipt)
	}
	if receipt.LocalAI.ModelID != "qwen3.5-0.8b-q4_0" ||
		receipt.Artifacts[2].Role != "local-ai-runtime" {
		t.Fatalf("v4 inspect lost local AI binding: %#v", receipt)
	}
}

func TestMaterializePortableV4StoresAIByDigestWithoutActivation(t *testing.T) {
	trust, pub, priv := testKeys(t)
	systemData := validPortableEROFS()
	runtimeData := append([]byte(nil), systemData...)
	runtimeData[len(runtimeData)-1] = 0x75
	aiData := append([]byte(nil), systemData...)
	aiData[len(aiData)-1] = 0x76
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortableV4(
		server.URL+"/system.erofs",
		server.URL+"/native-surface-runtime.erofs",
		server.URL+"/local-ai-runtime.erofs",
		systemData,
		runtimeData,
		aiData,
	)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(envelope) })
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(systemData) })
	mux.HandleFunc("/native-surface-runtime.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(runtimeData) })
	mux.HandleFunc("/local-ai-runtime.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(aiData) })

	root := filepath.Join(t.TempDir(), ".ordax")
	receipt, err := materializePortableV4(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	)
	if err != nil {
		t.Fatal(err)
	}
	if receipt.Status != "materialized-portable-v4" ||
		receipt.Idempotent ||
		receipt.ActivationAllowed ||
		receipt.RuntimeReused ||
		receipt.AIRuntimeReused {
		t.Fatalf("unexpected v4 materialize receipt: %#v", receipt)
	}
	expectedRuntime := filepath.Join(root, "runtimes", "sha256", m.Artifacts[1].SHA256, "native-surface-runtime.erofs")
	expectedAI := filepath.Join(root, "ai-runtimes", "sha256", m.Artifacts[2].SHA256, "local-ai-runtime.erofs")
	if receipt.RuntimePath != expectedRuntime || receipt.AIRuntimePath != expectedAI {
		t.Fatalf("v4 runtime paths mismatch: %#v", receipt)
	}
	releaseRoot := filepath.Join(root, "releases", testCommit)
	aiRef, err := os.ReadFile(filepath.Join(releaseRoot, "local-ai-runtime.sha256"))
	if err != nil {
		t.Fatal(err)
	}
	if string(aiRef) != m.Artifacts[2].SHA256+"\n" {
		t.Fatalf("stored local AI reference = %q", aiRef)
	}
	if _, err := os.Lstat(filepath.Join(root, "current")); !os.IsNotExist(err) {
		t.Fatal("v4 materialization created an activation pointer")
	}
	verified, err := verifyPortableV4Exact(root, trust, pub, defaultRepo, testCommit)
	if err != nil {
		t.Fatal(err)
	}
	if verified.RuntimePath != expectedRuntime ||
		verified.AIRuntimePath != expectedAI ||
		verified.ActivationAllowed {
		t.Fatalf("unexpected v4 exact verification receipt: %#v", verified)
	}
}

func TestMaterializePortableV4WithRealAIRuntimeFromEnv(t *testing.T) {
	realAIPath := os.Getenv("ORDAX_TEST_REAL_LOCAL_AI_RUNTIME")
	if realAIPath == "" {
		t.Skip("ORDAX_TEST_REAL_LOCAL_AI_RUNTIME is not set")
	}
	aiData, err := os.ReadFile(realAIPath)
	if err != nil {
		t.Fatal(err)
	}
	if len(aiData) < 4096 {
		t.Fatal("real local AI runtime fixture is unexpectedly small")
	}

	systemData := validPortableEROFS()
	runtimeData := append([]byte(nil), systemData...)
	runtimeData[len(runtimeData)-1] = 0x79

	trust, pub, priv := testKeys(t)
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()

	m := manifestForPortableV4(
		server.URL+"/system.erofs",
		server.URL+"/native-surface-runtime.erofs",
		server.URL+"/local-ai-runtime.erofs",
		systemData,
		runtimeData,
		aiData,
	)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(envelope) })
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(systemData) })
	mux.HandleFunc("/native-surface-runtime.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(runtimeData) })
	mux.HandleFunc("/local-ai-runtime.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(aiData) })

	root := filepath.Join(t.TempDir(), ".ordax")
	first, err := materializePortableV4(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	)
	if err != nil {
		t.Fatal(err)
	}
	if first.ActivationAllowed || first.AIRuntimeReused || first.Idempotent {
		t.Fatalf("unexpected first real-AI materialization receipt: %#v", first)
	}
	expectedDigest := sha256.Sum256(aiData)
	expectedHex := hex.EncodeToString(expectedDigest[:])
	expectedAI := filepath.Join(
		root,
		"ai-runtimes",
		"sha256",
		expectedHex,
		"local-ai-runtime.erofs",
	)
	if first.AIRuntimePath != expectedAI {
		t.Fatalf("real local AI runtime path mismatch: got=%s expected=%s", first.AIRuntimePath, expectedAI)
	}
	stored, err := os.ReadFile(expectedAI)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(stored, aiData) {
		t.Fatal("materialized real local AI runtime differs from source bytes")
	}

	verified, err := verifyPortableV4Exact(root, trust, pub, defaultRepo, testCommit)
	if err != nil {
		t.Fatal(err)
	}
	if verified.AIRuntimePath != expectedAI || verified.ActivationAllowed {
		t.Fatalf("unexpected real-AI exact verification receipt: %#v", verified)
	}
	if _, err := os.Lstat(filepath.Join(root, "current")); !os.IsNotExist(err) {
		t.Fatal("real-AI v4 materialization unexpectedly activated current")
	}

	second, err := materializePortableV4(
		server.Client(),
		server.URL+"/release.json",
		root,
		trust,
		pub,
		defaultRepo,
		testCommit,
	)
	if err != nil {
		t.Fatal(err)
	}
	if !second.Idempotent || !second.AIRuntimeReused || !second.RuntimeReused || second.ActivationAllowed {
		t.Fatalf("real-AI v4 materialization is not idempotent/reused: %#v", second)
	}
	t.Logf("PORTABLE_V4_REAL_AI_MATERIALIZATION=PASS sha256=%s size=%d", expectedHex, len(aiData))
}

func TestVerifyPortableV4ExactRejectsTamperedAIRuntime(t *testing.T) {
	trust, pub, priv := testKeys(t)
	systemData := validPortableEROFS()
	runtimeData := append([]byte(nil), systemData...)
	runtimeData[len(runtimeData)-1] = 0x77
	aiData := append([]byte(nil), systemData...)
	aiData[len(aiData)-1] = 0x78
	mux := http.NewServeMux()
	server := httptest.NewTLSServer(mux)
	defer server.Close()
	m := manifestForPortableV4(
		server.URL+"/system.erofs",
		server.URL+"/native-surface-runtime.erofs",
		server.URL+"/local-ai-runtime.erofs",
		systemData,
		runtimeData,
		aiData,
	)
	envelope := signedEnvelope(t, m, trust.KeyID, priv)
	mux.HandleFunc("/release.json", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(envelope) })
	mux.HandleFunc("/system.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(systemData) })
	mux.HandleFunc("/native-surface-runtime.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(runtimeData) })
	mux.HandleFunc("/local-ai-runtime.erofs", func(w http.ResponseWriter, r *http.Request) { _, _ = w.Write(aiData) })

	root := filepath.Join(t.TempDir(), ".ordax")
	receipt, err := materializePortableV4(server.Client(), server.URL+"/release.json", root, trust, pub, defaultRepo, testCommit)
	if err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(receipt.AIRuntimePath)
	if err != nil {
		t.Fatal(err)
	}
	data[len(data)-1] ^= 0x01
	if err := os.WriteFile(receipt.AIRuntimePath, data, 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := verifyPortableV4Exact(root, trust, pub, defaultRepo, testCommit); err == nil ||
		!strings.Contains(err.Error(), "digest") {
		t.Fatalf("tampered local AI runtime was accepted: %v", err)
	}
}
