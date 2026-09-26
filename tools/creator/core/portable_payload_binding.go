package creatorcore

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"sort"
	"strconv"
)

const PortablePayloadBindingsDigestSchema = "ordax-portable-payload-bindings/1"

// PortableMediaBindingsSHA256 returns one target-independent identity for the
// exact 17 artifact bytes that may be materialized by the Portable writer.
// Target geometry is deliberately excluded so the same owner-authorized
// payload identity can be used with different eligible removable USB sizes.
func PortableMediaBindingsSHA256(bindings PortableMediaBindings) (string, error) {
	if bindings.Schema != PortableMediaBindingsSchema {
		return "", errors.New("portable payload bindings schema is not canonical")
	}
	if len(bindings.Artifacts) != len(portableMediaTargets) {
		return "", fmt.Errorf("portable payload requires exactly %d artifact bindings", len(portableMediaTargets))
	}

	byID := make(map[string]PortableMediaArtifactBinding, len(bindings.Artifacts))
	for _, binding := range bindings.Artifacts {
		if _, ok := portableMediaTargets[binding.ID]; !ok {
			return "", fmt.Errorf("portable payload contains unknown artifact id %q", binding.ID)
		}
		if _, duplicate := byID[binding.ID]; duplicate {
			return "", fmt.Errorf("portable payload contains duplicate artifact id %q", binding.ID)
		}
		if !validPortableMediaSHA256(binding.SHA256) {
			return "", fmt.Errorf("portable payload artifact %q has invalid SHA-256", binding.ID)
		}
		if binding.SizeBytes == 0 || binding.SizeBytes > portableMediaMaxArtifact {
			return "", fmt.Errorf("portable payload artifact %q size is outside allowed range", binding.ID)
		}
		byID[binding.ID] = binding
	}
	if len(byID) != len(portableMediaTargets) {
		return "", errors.New("portable payload artifact set is incomplete")
	}

	ids := make([]string, 0, len(byID))
	for id := range byID {
		ids = append(ids, id)
	}
	sort.Strings(ids)

	h := sha256.New()
	_, _ = h.Write([]byte(PortablePayloadBindingsDigestSchema))
	_, _ = h.Write([]byte{0})
	for _, id := range ids {
		binding := byID[id]
		_, _ = h.Write([]byte(id))
		_, _ = h.Write([]byte{0})
		_, _ = h.Write([]byte(binding.SHA256))
		_, _ = h.Write([]byte{0})
		_, _ = h.Write([]byte(strconv.FormatUint(binding.SizeBytes, 10)))
		_, _ = h.Write([]byte{0})
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

// PortableApplicationBindingsSHA256 proves that a target-specific 39-operation
// application plan still refers to the exact target-independent artifact set
// authorized by the owner. It rejects plans whose materialization phase does
// not contain exactly one binding for each canonical Portable artifact id.
func PortableApplicationBindingsSHA256(plan PortableApplicationPlan) (string, error) {
	if plan.Schema != PortableApplicationPlanSchema {
		return "", errors.New("portable application plan schema is not canonical")
	}
	bindings := PortableMediaBindings{
		Schema:    PortableMediaBindingsSchema,
		Artifacts: make([]PortableMediaArtifactBinding, 0, len(portableMediaTargets)),
	}
	seen := make(map[string]bool, len(portableMediaTargets))
	for _, operation := range plan.Operations {
		if operation.Kind != "materialize-artifact" {
			continue
		}
		if operation.ArtifactID == "" || seen[operation.ArtifactID] {
			return "", fmt.Errorf("portable application plan has invalid or duplicate materialization id %q", operation.ArtifactID)
		}
		seen[operation.ArtifactID] = true
		bindings.Artifacts = append(bindings.Artifacts, PortableMediaArtifactBinding{
			ID:        operation.ArtifactID,
			SHA256:    operation.SHA256,
			SizeBytes: operation.SizeBytes,
		})
	}
	if len(bindings.Artifacts) != len(portableMediaTargets) {
		return "", fmt.Errorf("portable application plan requires exactly %d materialized artifacts", len(portableMediaTargets))
	}
	return PortableMediaBindingsSHA256(bindings)
}
