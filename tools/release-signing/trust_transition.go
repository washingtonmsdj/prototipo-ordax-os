package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"flag"
	"fmt"
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

func validateEmbeddedTrust(trust TrustAnchor) (ed25519.PublicKey, error) {
	if trust.Schema != trustSchema {
		return nil, errors.New("unsupported trust anchor schema")
	}
	if err := validateKeyID(trust.KeyID); err != nil {
		return nil, fmt.Errorf("trust anchor: %w", err)
	}
	publicKey, err := base64.StdEncoding.Strict().DecodeString(trust.PublicKeyB64)
	if err != nil || len(publicKey) != ed25519.PublicKeySize {
		return nil, errors.New("trust anchor contains invalid Ed25519 public key")
	}
	return ed25519.PublicKey(publicKey), nil
}

func trustBytesAndAnchor(path string) ([]byte, TrustAnchor, ed25519.PublicKey, error) {
	data, err := readRegular(path, maxTrust, false)
	if err != nil {
		return nil, TrustAnchor{}, nil, fmt.Errorf("trust anchor: %w", err)
	}
	var trust TrustAnchor
	if err := decodeStrict(data, maxTrust, &trust); err != nil {
		return nil, TrustAnchor{}, nil, fmt.Errorf("trust anchor: %w", err)
	}
	publicKey, err := validateEmbeddedTrust(trust)
	if err != nil {
		return nil, TrustAnchor{}, nil, err
	}
	return data, trust, publicKey, nil
}

func canonicalTrustBytes(trust TrustAnchor) ([]byte, ed25519.PublicKey, error) {
	publicKey, err := validateEmbeddedTrust(trust)
	if err != nil {
		return nil, nil, err
	}
	data, err := marshalJSON(trust)
	if err != nil {
		return nil, nil, err
	}
	return data, publicKey, nil
}

func validateTrustTransition(
	transition TrustTransition,
	currentTrustBytes []byte,
	currentTrust TrustAnchor,
	currentPublic ed25519.PublicKey,
	expectedRepository string,
	expectedSequence uint64,
) ([]byte, error) {
	if transition.Schema != trustTransitionSchema {
		return nil, errors.New("unsupported trust transition schema")
	}
	if transition.SourceRepository != expectedRepository {
		return nil, fmt.Errorf("unexpected source repository: %q", transition.SourceRepository)
	}
	if transition.Sequence == 0 {
		return nil, errors.New("trust transition sequence must be positive")
	}
	if expectedSequence == 0 || transition.Sequence != expectedSequence {
		return nil, fmt.Errorf(
			"trust transition sequence mismatch: got=%d expected=%d",
			transition.Sequence,
			expectedSequence,
		)
	}
	if transition.PreviousKeyID != currentTrust.KeyID {
		return nil, errors.New("trust transition previous_key_id does not match current trust")
	}
	currentDigest := sha256.Sum256(currentTrustBytes)
	if transition.PreviousTrustSHA256 != hex.EncodeToString(currentDigest[:]) {
		return nil, errors.New("trust transition previous_trust_sha256 does not match current trust bytes")
	}
	if !shaPattern.MatchString(transition.PreviousTrustSHA256) ||
		!shaPattern.MatchString(transition.NextTrustSHA256) {
		return nil, errors.New("trust transition SHA-256 field is invalid")
	}
	nextBytes, nextPublic, err := canonicalTrustBytes(transition.NextTrust)
	if err != nil {
		return nil, fmt.Errorf("next trust: %w", err)
	}
	if transition.NextTrust.KeyID == currentTrust.KeyID {
		return nil, errors.New("next trust key id must differ from current trust key id")
	}
	if bytes.Equal(nextPublic, currentPublic) {
		return nil, errors.New("next trust must use different Ed25519 key material")
	}
	nextDigest := sha256.Sum256(nextBytes)
	if transition.NextTrustSHA256 != hex.EncodeToString(nextDigest[:]) {
		return nil, errors.New("trust transition next_trust_sha256 does not match canonical next trust")
	}
	return nextBytes, nil
}

func signTrustTransition(
	currentPrivatePath string,
	currentTrustPath string,
	nextTrustPath string,
	outputPath string,
	sequence uint64,
	repository string,
) (TrustTransition, error) {
	if sequence == 0 {
		return TrustTransition{}, errors.New("trust transition sequence must be positive")
	}
	currentTrustBytes, currentTrust, currentPublic, err := trustBytesAndAnchor(currentTrustPath)
	if err != nil {
		return TrustTransition{}, err
	}
	nextRaw, nextTrust, _, err := trustBytesAndAnchor(nextTrustPath)
	if err != nil {
		return TrustTransition{}, fmt.Errorf("next trust: %w", err)
	}
	_ = nextRaw
	privateKey, err := loadPrivateKey(currentPrivatePath)
	if err != nil {
		return TrustTransition{}, err
	}
	if err := validateSigningIdentity(
		privateKey,
		currentTrust,
		currentPublic,
		currentTrust.KeyID,
	); err != nil {
		return TrustTransition{}, err
	}
	nextBytes, _, err := canonicalTrustBytes(nextTrust)
	if err != nil {
		return TrustTransition{}, err
	}
	previousDigest := sha256.Sum256(currentTrustBytes)
	nextDigest := sha256.Sum256(nextBytes)
	transition := TrustTransition{
		Schema:              trustTransitionSchema,
		SourceRepository:    repository,
		Sequence:            sequence,
		PreviousKeyID:       currentTrust.KeyID,
		PreviousTrustSHA256: hex.EncodeToString(previousDigest[:]),
		NextTrust:           nextTrust,
		NextTrustSHA256:     hex.EncodeToString(nextDigest[:]),
	}
	if _, err := validateTrustTransition(
		transition,
		currentTrustBytes,
		currentTrust,
		currentPublic,
		repository,
		sequence,
	); err != nil {
		return TrustTransition{}, err
	}
	payload, err := marshalJSON(transition)
	if err != nil {
		return TrustTransition{}, err
	}
	envelope := TrustTransitionEnvelope{
		Schema:    trustTransitionEnvelopeSchema,
		Payload:   payload,
		Signature: ed25519.Sign(privateKey, payload),
		KeyID:     currentTrust.KeyID,
	}
	envelopeBytes, err := marshalJSON(envelope)
	if err != nil {
		return TrustTransition{}, err
	}
	if err := writeExclusive(outputPath, envelopeBytes, 0o644); err != nil {
		return TrustTransition{}, err
	}
	return transition, nil
}

func verifyTrustTransition(
	envelopePath string,
	currentTrustPath string,
	nextTrustOutputPath string,
	expectedSequence uint64,
	repository string,
) (TrustTransition, error) {
	if expectedSequence == 0 {
		return TrustTransition{}, errors.New("expected trust transition sequence must be positive")
	}
	currentTrustBytes, currentTrust, currentPublic, err := trustBytesAndAnchor(currentTrustPath)
	if err != nil {
		return TrustTransition{}, err
	}
	envelopeBytes, err := readRegular(envelopePath, maxTrustTransition, false)
	if err != nil {
		return TrustTransition{}, fmt.Errorf("trust transition envelope: %w", err)
	}
	var envelope TrustTransitionEnvelope
	if err := decodeStrict(envelopeBytes, maxTrustTransition, &envelope); err != nil {
		return TrustTransition{}, fmt.Errorf("trust transition envelope: %w", err)
	}
	if envelope.Schema != trustTransitionEnvelopeSchema {
		return TrustTransition{}, errors.New("unsupported trust transition envelope schema")
	}
	if envelope.KeyID != currentTrust.KeyID {
		return TrustTransition{}, errors.New("trust transition envelope key id does not match current trust")
	}
	if len(envelope.Payload) == 0 || len(envelope.Payload) > maxTrustTransition {
		return TrustTransition{}, errors.New("trust transition payload is outside allowed size")
	}
	if len(envelope.Signature) != ed25519.SignatureSize ||
		!ed25519.Verify(currentPublic, envelope.Payload, envelope.Signature) {
		return TrustTransition{}, errors.New("trust transition signature verification failed")
	}
	var transition TrustTransition
	if err := decodeStrict(envelope.Payload, maxTrustTransition, &transition); err != nil {
		return TrustTransition{}, fmt.Errorf("trust transition payload: %w", err)
	}
	nextBytes, err := validateTrustTransition(
		transition,
		currentTrustBytes,
		currentTrust,
		currentPublic,
		repository,
		expectedSequence,
	)
	if err != nil {
		return TrustTransition{}, err
	}
	if nextTrustOutputPath != "" {
		if err := writeExclusive(nextTrustOutputPath, nextBytes, 0o644); err != nil {
			return TrustTransition{}, err
		}
	}
	return transition, nil
}

func signTrustTransitionCommand(args []string) error {
	flags := flag.NewFlagSet("sign-trust-transition", flag.ContinueOnError)
	privatePath := flags.String("current-private-key", "", "current external PKCS#8 Ed25519 private-key path")
	currentTrustPath := flags.String("current-trust", "", "current public trust-anchor JSON path")
	nextTrustPath := flags.String("next-trust", "", "next public trust-anchor JSON path")
	outputPath := flags.String("out", "", "new signed trust-transition envelope path")
	sequence := flags.Uint64("sequence", 0, "strictly increasing trust transition sequence")
	repository := flags.String("repository", defaultRepo, "expected source repository")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *privatePath == "" || *currentTrustPath == "" || *nextTrustPath == "" ||
		*outputPath == "" || *sequence == 0 || flags.NArg() != 0 {
		return errors.New("sign-trust-transition requires --current-private-key, --current-trust, --next-trust, --out and positive --sequence")
	}
	transition, err := signTrustTransition(
		*privatePath,
		*currentTrustPath,
		*nextTrustPath,
		*outputPath,
		*sequence,
		*repository,
	)
	if err != nil {
		return err
	}
	fmt.Printf(
		"TRUST_TRANSITION_SIGNED=YES\nSEQUENCE=%d\nPREVIOUS_KEY_ID=%s\nNEXT_KEY_ID=%s\nPRIVATE_KEY_PRINTED=NO\n",
		transition.Sequence,
		transition.PreviousKeyID,
		transition.NextTrust.KeyID,
	)
	return nil
}

func verifyTrustTransitionCommand(args []string) error {
	flags := flag.NewFlagSet("verify-trust-transition", flag.ContinueOnError)
	envelopePath := flags.String("envelope", "", "signed trust-transition envelope path")
	currentTrustPath := flags.String("current-trust", "", "current public trust-anchor JSON path")
	nextTrustOutput := flags.String("out-next-trust", "", "optional new file for canonical next public trust")
	expectedSequence := flags.Uint64("expected-sequence", 0, "required exact next trust transition sequence")
	repository := flags.String("repository", defaultRepo, "expected source repository")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *envelopePath == "" || *currentTrustPath == "" ||
		*expectedSequence == 0 || flags.NArg() != 0 {
		return errors.New("verify-trust-transition requires --envelope, --current-trust and positive --expected-sequence")
	}
	transition, err := verifyTrustTransition(
		*envelopePath,
		*currentTrustPath,
		*nextTrustOutput,
		*expectedSequence,
		*repository,
	)
	if err != nil {
		return err
	}
	fmt.Printf(
		"TRUST_TRANSITION_VERIFIED=YES\nSEQUENCE=%d\nPREVIOUS_KEY_ID=%s\nNEXT_KEY_ID=%s\nNEXT_TRUST_SHA256=%s\n",
		transition.Sequence,
		transition.PreviousKeyID,
		transition.NextTrust.KeyID,
		transition.NextTrustSHA256,
	)
	return nil
}
