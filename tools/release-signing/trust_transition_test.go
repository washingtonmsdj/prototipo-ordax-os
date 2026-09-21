package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestTrustTransitionRoundTrip(t *testing.T) {
	root := t.TempDir()
	currentPrivate := filepath.Join(root, "current-private.pem")
	currentTrust := filepath.Join(root, "current-trust.json")
	nextPrivate := filepath.Join(root, "next-private.pem")
	nextTrust := filepath.Join(root, "next-trust.json")
	envelope := filepath.Join(root, "transition-envelope.json")
	verifiedNext := filepath.Join(root, "verified-next-trust.json")

	if _, err := generateKeyFiles(currentPrivate, currentTrust, "prototype-1"); err != nil {
		t.Fatal(err)
	}
	if _, err := generateKeyFiles(nextPrivate, nextTrust, "prototype-2"); err != nil {
		t.Fatal(err)
	}

	signed, err := signTrustTransition(
		currentPrivate,
		currentTrust,
		nextTrust,
		envelope,
		1,
		defaultRepo,
	)
	if err != nil {
		t.Fatalf("signTrustTransition: %v", err)
	}
	if signed.Sequence != 1 ||
		signed.PreviousKeyID != "prototype-1" ||
		signed.NextTrust.KeyID != "prototype-2" {
		t.Fatalf("unexpected signed transition: %#v", signed)
	}

	verified, err := verifyTrustTransition(
		envelope,
		currentTrust,
		verifiedNext,
		1,
		defaultRepo,
	)
	if err != nil {
		t.Fatalf("verifyTrustTransition: %v", err)
	}
	if verified.Sequence != 1 || verified.NextTrust.KeyID != "prototype-2" {
		t.Fatalf("unexpected verified transition: %#v", verified)
	}

	expected, err := os.ReadFile(nextTrust)
	if err != nil {
		t.Fatal(err)
	}
	var expectedTrust TrustAnchor
	if err := json.Unmarshal(expected, &expectedTrust); err != nil {
		t.Fatal(err)
	}
	expectedCanonical, err := marshalJSON(expectedTrust)
	if err != nil {
		t.Fatal(err)
	}
	actual, err := os.ReadFile(verifiedNext)
	if err != nil {
		t.Fatal(err)
	}
	if string(actual) != string(expectedCanonical) {
		t.Fatal("verified next trust differs from canonical next trust")
	}
}

func TestTrustTransitionRejectsRollbackSequence(t *testing.T) {
	root := t.TempDir()
	currentPrivate := filepath.Join(root, "current-private.pem")
	currentTrust := filepath.Join(root, "current-trust.json")
	nextPrivate := filepath.Join(root, "next-private.pem")
	nextTrust := filepath.Join(root, "next-trust.json")
	envelope := filepath.Join(root, "transition-envelope.json")

	if _, err := generateKeyFiles(currentPrivate, currentTrust, "prototype-1"); err != nil {
		t.Fatal(err)
	}
	if _, err := generateKeyFiles(nextPrivate, nextTrust, "prototype-2"); err != nil {
		t.Fatal(err)
	}
	if _, err := signTrustTransition(
		currentPrivate,
		currentTrust,
		nextTrust,
		envelope,
		2,
		defaultRepo,
	); err != nil {
		t.Fatal(err)
	}

	if _, err := verifyTrustTransition(
		envelope,
		currentTrust,
		"",
		1,
		defaultRepo,
	); err == nil || !strings.Contains(err.Error(), "sequence mismatch") {
		t.Fatalf("rollback sequence error = %v", err)
	}
}

func TestTrustTransitionRejectsDifferentCurrentTrust(t *testing.T) {
	root := t.TempDir()
	currentPrivate := filepath.Join(root, "current-private.pem")
	currentTrust := filepath.Join(root, "current-trust.json")
	otherPrivate := filepath.Join(root, "other-private.pem")
	otherTrust := filepath.Join(root, "other-trust.json")
	nextPrivate := filepath.Join(root, "next-private.pem")
	nextTrust := filepath.Join(root, "next-trust.json")
	envelope := filepath.Join(root, "transition-envelope.json")

	if _, err := generateKeyFiles(currentPrivate, currentTrust, "prototype-1"); err != nil {
		t.Fatal(err)
	}
	if _, err := generateKeyFiles(otherPrivate, otherTrust, "prototype-other"); err != nil {
		t.Fatal(err)
	}
	if _, err := generateKeyFiles(nextPrivate, nextTrust, "prototype-2"); err != nil {
		t.Fatal(err)
	}
	if _, err := signTrustTransition(
		currentPrivate,
		currentTrust,
		nextTrust,
		envelope,
		1,
		defaultRepo,
	); err != nil {
		t.Fatal(err)
	}

	if _, err := verifyTrustTransition(
		envelope,
		otherTrust,
		"",
		1,
		defaultRepo,
	); err == nil {
		t.Fatal("transition verified against unrelated current trust")
	}
}

func TestTrustTransitionRejectsSameKeyMaterialUnderNewID(t *testing.T) {
	root := t.TempDir()
	currentPrivate := filepath.Join(root, "current-private.pem")
	currentTrust := filepath.Join(root, "current-trust.json")
	sameKeyNextTrust := filepath.Join(root, "same-key-next-trust.json")
	envelope := filepath.Join(root, "transition-envelope.json")

	if _, err := generateKeyFiles(currentPrivate, currentTrust, "prototype-1"); err != nil {
		t.Fatal(err)
	}
	if _, err := deriveTrust(currentPrivate, sameKeyNextTrust, "prototype-2"); err != nil {
		t.Fatal(err)
	}

	if _, err := signTrustTransition(
		currentPrivate,
		currentTrust,
		sameKeyNextTrust,
		envelope,
		1,
		defaultRepo,
	); err == nil || !strings.Contains(err.Error(), "different Ed25519 key material") {
		t.Fatalf("same-key transition error = %v", err)
	}
	if _, err := os.Stat(envelope); !os.IsNotExist(err) {
		t.Fatalf("transition envelope appeared after rejected same-key rotation: %v", err)
	}
}

func TestTrustTransitionRejectsTamperedPayload(t *testing.T) {
	root := t.TempDir()
	currentPrivate := filepath.Join(root, "current-private.pem")
	currentTrust := filepath.Join(root, "current-trust.json")
	nextPrivate := filepath.Join(root, "next-private.pem")
	nextTrust := filepath.Join(root, "next-trust.json")
	envelope := filepath.Join(root, "transition-envelope.json")

	if _, err := generateKeyFiles(currentPrivate, currentTrust, "prototype-1"); err != nil {
		t.Fatal(err)
	}
	if _, err := generateKeyFiles(nextPrivate, nextTrust, "prototype-2"); err != nil {
		t.Fatal(err)
	}
	if _, err := signTrustTransition(
		currentPrivate,
		currentTrust,
		nextTrust,
		envelope,
		1,
		defaultRepo,
	); err != nil {
		t.Fatal(err)
	}

	raw, err := os.ReadFile(envelope)
	if err != nil {
		t.Fatal(err)
	}
	var wrapper TrustTransitionEnvelope
	if err := json.Unmarshal(raw, &wrapper); err != nil {
		t.Fatal(err)
	}
	wrapper.Payload[len(wrapper.Payload)-2] ^= 1
	tampered, err := marshalJSON(wrapper)
	if err != nil {
		t.Fatal(err)
	}
	tamperedPath := filepath.Join(root, "tampered-transition.json")
	if err := os.WriteFile(tamperedPath, tampered, 0o644); err != nil {
		t.Fatal(err)
	}

	if _, err := verifyTrustTransition(
		tamperedPath,
		currentTrust,
		"",
		1,
		defaultRepo,
	); err == nil || !strings.Contains(err.Error(), "signature verification failed") {
		t.Fatalf("tampered transition error = %v", err)
	}
}
