package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func trustAnchorForTest(t *testing.T, keyID string) (TrustAnchor, ed25519.PublicKey, ed25519.PrivateKey, []byte) {
	t.Helper()
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	trust := TrustAnchor{
		Schema:       trustSchema,
		KeyID:        keyID,
		PublicKeyB64: base64.StdEncoding.EncodeToString(pub),
	}
	data, err := json.MarshalIndent(trust, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	data = append(data, '\n')
	return trust, pub, priv, data
}

func signedTrustTransitionForTest(
	t *testing.T,
	currentTrust TrustAnchor,
	currentTrustBytes []byte,
	currentPrivate ed25519.PrivateKey,
	nextTrust TrustAnchor,
	sequence uint64,
) []byte {
	t.Helper()
	nextBytes, _, err := canonicalTrustBytesForTransition(nextTrust)
	if err != nil {
		t.Fatal(err)
	}
	currentDigest := sha256.Sum256(currentTrustBytes)
	nextDigest := sha256.Sum256(nextBytes)
	transition := TrustTransition{
		Schema:              trustTransitionSchema,
		SourceRepository:    defaultRepo,
		Sequence:            sequence,
		PreviousKeyID:       currentTrust.KeyID,
		PreviousTrustSHA256: hex.EncodeToString(currentDigest[:]),
		NextTrust:           nextTrust,
		NextTrustSHA256:     hex.EncodeToString(nextDigest[:]),
	}
	payload, err := json.MarshalIndent(transition, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	payload = append(payload, '\n')
	envelope := TrustTransitionEnvelope{
		Schema:    trustTransitionEnvelopeSchema,
		Payload:   payload,
		Signature: ed25519.Sign(currentPrivate, payload),
		KeyID:     currentTrust.KeyID,
	}
	data, err := json.MarshalIndent(envelope, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	return append(data, '\n')
}

func TestReleaseAgentVerifiesSignedTrustTransition(t *testing.T) {
	currentTrust, currentPub, currentPriv, currentBytes := trustAnchorForTest(t, "prototype-1")
	nextTrust, _, _, _ := trustAnchorForTest(t, "prototype-2")
	envelope := signedTrustTransitionForTest(
		t,
		currentTrust,
		currentBytes,
		currentPriv,
		nextTrust,
		1,
	)

	transition, nextBytes, err := verifyTrustTransitionBytes(
		envelope,
		currentBytes,
		currentTrust,
		currentPub,
		defaultRepo,
		1,
	)
	if err != nil {
		t.Fatalf("verifyTrustTransitionBytes: %v", err)
	}
	if transition.Sequence != 1 ||
		transition.PreviousKeyID != "prototype-1" ||
		transition.NextTrust.KeyID != "prototype-2" {
		t.Fatalf("unexpected transition: %#v", transition)
	}
	expected, _, err := canonicalTrustBytesForTransition(nextTrust)
	if err != nil {
		t.Fatal(err)
	}
	if string(nextBytes) != string(expected) {
		t.Fatal("verified next trust bytes drifted")
	}
}

func TestReleaseAgentRejectsTrustTransitionRollback(t *testing.T) {
	currentTrust, currentPub, currentPriv, currentBytes := trustAnchorForTest(t, "prototype-1")
	nextTrust, _, _, _ := trustAnchorForTest(t, "prototype-2")
	envelope := signedTrustTransitionForTest(
		t,
		currentTrust,
		currentBytes,
		currentPriv,
		nextTrust,
		2,
	)

	if _, _, err := verifyTrustTransitionBytes(
		envelope,
		currentBytes,
		currentTrust,
		currentPub,
		defaultRepo,
		1,
	); err == nil || !strings.Contains(err.Error(), "sequence mismatch") {
		t.Fatalf("rollback error = %v", err)
	}
}

func TestReleaseAgentRejectsTrustTransitionWrongCurrentAnchor(t *testing.T) {
	currentTrust, _, currentPriv, currentBytes := trustAnchorForTest(t, "prototype-1")
	nextTrust, _, _, _ := trustAnchorForTest(t, "prototype-2")
	otherTrust, otherPub, _, otherBytes := trustAnchorForTest(t, "prototype-other")
	envelope := signedTrustTransitionForTest(
		t,
		currentTrust,
		currentBytes,
		currentPriv,
		nextTrust,
		1,
	)

	if _, _, err := verifyTrustTransitionBytes(
		envelope,
		otherBytes,
		otherTrust,
		otherPub,
		defaultRepo,
		1,
	); err == nil {
		t.Fatal("transition verified against unrelated current anchor")
	}
}

func TestReleaseAgentRejectsSameKeyMaterialRenamed(t *testing.T) {
	currentTrust, currentPub, currentPriv, currentBytes := trustAnchorForTest(t, "prototype-1")
	nextTrust := TrustAnchor{
		Schema:       trustSchema,
		KeyID:        "prototype-2",
		PublicKeyB64: currentTrust.PublicKeyB64,
	}
	envelope := signedTrustTransitionForTest(
		t,
		currentTrust,
		currentBytes,
		currentPriv,
		nextTrust,
		1,
	)

	if _, _, err := verifyTrustTransitionBytes(
		envelope,
		currentBytes,
		currentTrust,
		currentPub,
		defaultRepo,
		1,
	); err == nil || !strings.Contains(err.Error(), "different Ed25519 key material") {
		t.Fatalf("same-key error = %v", err)
	}
}

func TestReleaseAgentWritesVerifiedNextTrustOnlyToNewFile(t *testing.T) {
	root := t.TempDir()
	currentTrust, _, currentPriv, currentBytes := trustAnchorForTest(t, "prototype-1")
	nextTrust, _, _, _ := trustAnchorForTest(t, "prototype-2")
	envelope := signedTrustTransitionForTest(
		t,
		currentTrust,
		currentBytes,
		currentPriv,
		nextTrust,
		1,
	)

	currentPath := filepath.Join(root, "current-trust.json")
	envelopePath := filepath.Join(root, "transition.json")
	nextPath := filepath.Join(root, "next-trust.json")
	if err := os.WriteFile(currentPath, currentBytes, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(envelopePath, envelope, 0o644); err != nil {
		t.Fatal(err)
	}

	receipt, err := verifyTrustTransitionFile(
		envelopePath,
		currentPath,
		defaultRepo,
		1,
		nextPath,
	)
	if err != nil {
		t.Fatalf("verifyTrustTransitionFile: %v", err)
	}
	if receipt.Status != "trust-transition-verified" ||
		receipt.NextKeyID != "prototype-2" {
		t.Fatalf("unexpected receipt: %#v", receipt)
	}
	if _, err := os.Stat(nextPath); err != nil {
		t.Fatal(err)
	}
	if _, err := verifyTrustTransitionFile(
		envelopePath,
		currentPath,
		defaultRepo,
		1,
		nextPath,
	); err == nil {
		t.Fatal("existing next-trust output was silently overwritten")
	}
}
