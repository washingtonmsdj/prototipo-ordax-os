package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
)

const (
	trustTransitionSchema         = "prototype-ordax.release-trust-transition/1"
	trustTransitionEnvelopeSchema = "prototype-ordax.release-trust-transition-envelope/1"
	maxTrustTransition            = 64 << 10
)

type TrustTransition struct {
	Schema              string      `json:"$schema"`
	SourceRepository    string      `json:"source_repository"`
	Sequence            uint64      `json:"sequence"`
	PreviousKeyID       string      `json:"previous_key_id"`
	PreviousTrustSHA256 string      `json:"previous_trust_sha256"`
	NextTrust           TrustAnchor `json:"next_trust"`
	NextTrustSHA256     string      `json:"next_trust_sha256"`
}

type TrustTransitionEnvelope struct {
	Schema    string `json:"$schema"`
	Payload   []byte `json:"payload"`
	Signature []byte `json:"signature"`
	KeyID     string `json:"key_id"`
}

type TrustTransitionReceipt struct {
	Status          string `json:"status"`
	Sequence        uint64 `json:"sequence"`
	PreviousKeyID   string `json:"previous_key_id"`
	NextKeyID       string `json:"next_key_id"`
	NextTrustSHA256 string `json:"next_trust_sha256"`
}

func loadTrustWithBytes(path string) ([]byte, TrustAnchor, ed25519.PublicKey, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, TrustAnchor{}, nil, fmt.Errorf("trust anchor: %w", err)
	}
	if !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 || info.Size() <= 0 || info.Size() > 16<<10 {
		return nil, TrustAnchor{}, nil, errors.New("trust anchor must be a small regular file")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, TrustAnchor{}, nil, err
	}
	var trust TrustAnchor
	if err := strictDecode(data, 16<<10, &trust); err != nil {
		return nil, TrustAnchor{}, nil, fmt.Errorf("invalid trust anchor: %w", err)
	}
	if trust.Schema != trustSchema || !rolePattern.MatchString(trust.KeyID) {
		return nil, TrustAnchor{}, nil, errors.New("unsupported trust anchor schema or key id")
	}
	key, err := base64.StdEncoding.Strict().DecodeString(trust.PublicKeyB64)
	if err != nil || len(key) != ed25519.PublicKeySize {
		return nil, TrustAnchor{}, nil, errors.New("invalid Ed25519 public key")
	}
	return data, trust, ed25519.PublicKey(key), nil
}

func canonicalTrustBytesForTransition(trust TrustAnchor) ([]byte, ed25519.PublicKey, error) {
	if trust.Schema != trustSchema || !rolePattern.MatchString(trust.KeyID) {
		return nil, nil, errors.New("unsupported next trust anchor schema or key id")
	}
	key, err := base64.StdEncoding.Strict().DecodeString(trust.PublicKeyB64)
	if err != nil || len(key) != ed25519.PublicKeySize {
		return nil, nil, errors.New("invalid next Ed25519 public key")
	}
	data, err := json.MarshalIndent(trust, "", "  ")
	if err != nil {
		return nil, nil, err
	}
	data = append(data, '\n')
	return data, ed25519.PublicKey(key), nil
}

func verifyTrustTransitionBytes(
	envelopeBytes []byte,
	currentTrustBytes []byte,
	currentTrust TrustAnchor,
	currentPublic ed25519.PublicKey,
	expectedRepo string,
	expectedSequence uint64,
) (TrustTransition, []byte, error) {
	if expectedSequence == 0 {
		return TrustTransition{}, nil, errors.New("expected trust transition sequence must be positive")
	}
	var envelope TrustTransitionEnvelope
	if err := strictDecode(envelopeBytes, maxTrustTransition, &envelope); err != nil {
		return TrustTransition{}, nil, fmt.Errorf("invalid trust transition envelope: %w", err)
	}
	if envelope.Schema != trustTransitionEnvelopeSchema {
		return TrustTransition{}, nil, errors.New("unsupported trust transition envelope schema")
	}
	if envelope.KeyID != currentTrust.KeyID {
		return TrustTransition{}, nil, errors.New("trust transition envelope key id does not match current trust")
	}
	if len(envelope.Payload) == 0 || len(envelope.Payload) > maxTrustTransition {
		return TrustTransition{}, nil, errors.New("trust transition payload is outside allowed size")
	}
	if len(envelope.Signature) != ed25519.SignatureSize ||
		!ed25519.Verify(currentPublic, envelope.Payload, envelope.Signature) {
		return TrustTransition{}, nil, errors.New("trust transition signature verification failed")
	}

	var transition TrustTransition
	if err := strictDecode(envelope.Payload, maxTrustTransition, &transition); err != nil {
		return TrustTransition{}, nil, fmt.Errorf("invalid signed trust transition: %w", err)
	}
	if transition.Schema != trustTransitionSchema {
		return TrustTransition{}, nil, errors.New("unsupported trust transition schema")
	}
	if transition.SourceRepository != expectedRepo {
		return TrustTransition{}, nil, fmt.Errorf("unexpected source repository: %q", transition.SourceRepository)
	}
	if transition.Sequence != expectedSequence {
		return TrustTransition{}, nil, fmt.Errorf(
			"trust transition sequence mismatch: got=%d expected=%d",
			transition.Sequence,
			expectedSequence,
		)
	}
	if transition.PreviousKeyID != currentTrust.KeyID {
		return TrustTransition{}, nil, errors.New("trust transition previous_key_id does not match current trust")
	}
	currentDigest := sha256.Sum256(currentTrustBytes)
	if transition.PreviousTrustSHA256 != hex.EncodeToString(currentDigest[:]) {
		return TrustTransition{}, nil, errors.New("trust transition previous_trust_sha256 does not match current trust bytes")
	}
	if !shaPattern.MatchString(transition.PreviousTrustSHA256) ||
		!shaPattern.MatchString(transition.NextTrustSHA256) {
		return TrustTransition{}, nil, errors.New("trust transition SHA-256 field is invalid")
	}
	nextBytes, nextPublic, err := canonicalTrustBytesForTransition(transition.NextTrust)
	if err != nil {
		return TrustTransition{}, nil, err
	}
	if transition.NextTrust.KeyID == currentTrust.KeyID {
		return TrustTransition{}, nil, errors.New("next trust key id must differ from current trust key id")
	}
	if bytes.Equal(nextPublic, currentPublic) {
		return TrustTransition{}, nil, errors.New("next trust must use different Ed25519 key material")
	}
	nextDigest := sha256.Sum256(nextBytes)
	if transition.NextTrustSHA256 != hex.EncodeToString(nextDigest[:]) {
		return TrustTransition{}, nil, errors.New("trust transition next_trust_sha256 does not match canonical next trust")
	}
	return transition, nextBytes, nil
}

func writeExclusiveTrust(path string, data []byte) error {
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if err != nil {
		return err
	}
	remove := true
	defer func() {
		if remove {
			_ = os.Remove(path)
		}
	}()
	if _, err := file.Write(data); err != nil {
		_ = file.Close()
		return err
	}
	if err := file.Sync(); err != nil {
		_ = file.Close()
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	remove = false
	return nil
}

func verifyTrustTransitionFile(
	envelopePath string,
	currentTrustPath string,
	expectedRepo string,
	expectedSequence uint64,
	outNextTrust string,
) (TrustTransitionReceipt, error) {
	currentTrustBytes, currentTrust, currentPublic, err := loadTrustWithBytes(currentTrustPath)
	if err != nil {
		return TrustTransitionReceipt{}, err
	}
	envelopeInfo, err := os.Lstat(envelopePath)
	if err != nil {
		return TrustTransitionReceipt{}, err
	}
	if !envelopeInfo.Mode().IsRegular() || envelopeInfo.Mode()&os.ModeSymlink != 0 ||
		envelopeInfo.Size() <= 0 || envelopeInfo.Size() > maxTrustTransition {
		return TrustTransitionReceipt{}, errors.New("trust transition envelope must be a small regular file")
	}
	envelopeBytes, err := os.ReadFile(envelopePath)
	if err != nil {
		return TrustTransitionReceipt{}, err
	}
	transition, nextBytes, err := verifyTrustTransitionBytes(
		envelopeBytes,
		currentTrustBytes,
		currentTrust,
		currentPublic,
		expectedRepo,
		expectedSequence,
	)
	if err != nil {
		return TrustTransitionReceipt{}, err
	}
	if outNextTrust != "" {
		if err := writeExclusiveTrust(outNextTrust, nextBytes); err != nil {
			return TrustTransitionReceipt{}, err
		}
	}
	return TrustTransitionReceipt{
		Status:          "trust-transition-verified",
		Sequence:        transition.Sequence,
		PreviousKeyID:   transition.PreviousKeyID,
		NextKeyID:       transition.NextTrust.KeyID,
		NextTrustSHA256: transition.NextTrustSHA256,
	}, nil
}

func verifyTrustTransitionCommand(args []string) error {
	fs := flag.NewFlagSet("verify-trust-transition", flag.ContinueOnError)
	envelopePath := fs.String("envelope", "", "signed trust transition envelope file")
	currentTrustPath := fs.String("current-trust", "", "currently trusted release anchor file")
	expectedSequence := fs.Uint64("expected-sequence", 0, "required exact next trust sequence")
	outNextTrust := fs.String("out-next-trust", "", "optional new file for verified canonical next trust")
	repository := fs.String("repository", defaultRepo, "expected source repository")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if *envelopePath == "" || *currentTrustPath == "" ||
		*expectedSequence == 0 || fs.NArg() != 0 {
		return errors.New("verify-trust-transition requires --envelope, --current-trust and positive --expected-sequence")
	}
	receipt, err := verifyTrustTransitionFile(
		*envelopePath,
		*currentTrustPath,
		*repository,
		*expectedSequence,
		*outNextTrust,
	)
	if err != nil {
		return err
	}
	return printJSON(receipt)
}
