package creatorcore

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"sort"
	"strings"
)

const (
	PortableMediaBindingsSchema = "prototype-ordax.portable-media-bindings/1"
	PortableMediaPlanSchema = "prototype-ordax.portable-media-plan/1"
	portableMediaMaxArtifact = uint64(16 << 30)
)

type PortableMediaArtifactBinding struct {
	ID string `json:"id"`
	SHA256 string `json:"sha256"`
	SizeBytes uint64 `json:"size_bytes"`
}

type PortableMediaBindings struct {
	Schema string `json:"$schema"`
	Artifacts []PortableMediaArtifactBinding `json:"artifacts"`
}

type PortableMediaArtifactPlan struct {
	ID string `json:"id"`
	Partition string `json:"partition"`
	TargetPath string `json:"target_path"`
	SHA256 string `json:"sha256"`
	SizeBytes uint64 `json:"size_bytes"`
}

type PortableMediaPlan struct {
	Schema string `json:"$schema"`
	Profile string `json:"profile"`
	SourceCommit string `json:"source_commit"`
	TargetBytes uint64 `json:"target_bytes"`
	ESPStartLBA uint64 `json:"esp_start_lba"`
	ESPLastLBA uint64 `json:"esp_last_lba"`
	DataStartLBA uint64 `json:"data_start_lba"`
	DataLastLBA uint64 `json:"data_last_lba"`
	Artifacts []PortableMediaArtifactPlan `json:"artifacts"`
	PhysicalWriteAuthorized bool `json:"physical_write_authorized"`
}

type portableMediaTarget struct {
	partition string
	target func(string) string
}

var portableMediaTargets = map[string]portableMediaTarget{
	"systemd-boot": {"ORDAX-ESP", func(string) string { return "/EFI/BOOT/BOOTX64.EFI" }},
	"loader-config": {"ORDAX-ESP", func(string) string { return "/loader/loader.conf" }},
	"loader-normal": {"ORDAX-ESP", func(string) string { return "/loader/entries/ordax-portable.conf" }},
	"loader-recovery": {"ORDAX-ESP", func(string) string { return "/loader/entries/ordax-portable-recovery.conf" }},
	"kernel": {"ORDAX-ESP", func(string) string { return "/ordax/vmlinuz" }},
	"initramfs": {"ORDAX-ESP", func(string) string { return "/ordax/initrd.gz" }},
	"bootstrap-capsule": {"ORDAX-ESP", func(string) string { return "/ordax/bootstrap/bootstrap.erofs" }},
	"release-trust": {"ORDAX-ESP", func(string) string { return "/ordax/bootstrap/trust/release-ed25519.json" }},
	"stable-base": {"ORDAX-DATA", func(string) string { return "/.ordax/base/stable-base.erofs" }},
	"persistent-state": {"ORDAX-DATA", func(string) string { return "/.ordax/state/persistent-state.img" }},
	"system-image": {"ORDAX-DATA", func(commit string) string { return "/.ordax/releases/" + commit + "/system.erofs" }},
	"release-manifest": {"ORDAX-DATA", func(commit string) string { return "/.ordax/releases/" + commit + "/release-manifest.json" }},
	"release-envelope": {"ORDAX-DATA", func(commit string) string { return "/.ordax/releases/" + commit + "/release-envelope.json" }},
}

func ParsePortableMediaBindings(data []byte) (PortableMediaBindings, error) {
	var value PortableMediaBindings
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&value); err != nil {
		return PortableMediaBindings{}, fmt.Errorf("decode portable media bindings: %w", err)
	}
	var extra any
	if err := decoder.Decode(&extra); !errors.Is(err, io.EOF) {
		if err == nil {
			return PortableMediaBindings{}, errors.New("decode portable media bindings: trailing JSON value")
		}
		return PortableMediaBindings{}, fmt.Errorf("decode portable media bindings trailing content: %w", err)
	}
	if value.Schema != PortableMediaBindingsSchema {
		return PortableMediaBindings{}, fmt.Errorf("unsupported portable media bindings schema %q", value.Schema)
	}
	return value, nil
}

func validPortableMediaSHA256(value string) bool {
	if len(value) != 64 || value != strings.ToLower(value) { return false }
	decoded, err := hex.DecodeString(value)
	return err == nil && len(decoded) == 32
}

func validPortableSourceCommit(value string) bool {
	if len(value) != 40 || value != strings.ToLower(value) { return false }
	decoded, err := hex.DecodeString(value)
	return err == nil && len(decoded) == 20
}

func PlanPortableMedia(targetBytes uint64, sourceCommit string, bindings PortableMediaBindings) (PortableMediaPlan, error) {
	if !validPortableSourceCommit(sourceCommit) {
		return PortableMediaPlan{}, errors.New("portable source commit must be lowercase 40-hex")
	}
	if bindings.Schema != PortableMediaBindingsSchema {
		return PortableMediaPlan{}, errors.New("portable media bindings schema is not canonical")
	}
	layout, err := PlanPortableTargetStorage(targetBytes)
	if err != nil { return PortableMediaPlan{}, err }
	if len(bindings.Artifacts) != len(portableMediaTargets) {
		return PortableMediaPlan{}, fmt.Errorf("portable media requires exactly %d artifact bindings; got=%d", len(portableMediaTargets), len(bindings.Artifacts))
	}
	seen := map[string]bool{}
	artifacts := make([]PortableMediaArtifactPlan, 0, len(bindings.Artifacts))
	for _, binding := range bindings.Artifacts {
		target, ok := portableMediaTargets[binding.ID]
		if !ok { return PortableMediaPlan{}, fmt.Errorf("unknown portable media artifact id %q", binding.ID) }
		if seen[binding.ID] { return PortableMediaPlan{}, fmt.Errorf("duplicate portable media artifact id %q", binding.ID) }
		seen[binding.ID] = true
		if !validPortableMediaSHA256(binding.SHA256) { return PortableMediaPlan{}, fmt.Errorf("portable media artifact %q has invalid SHA-256", binding.ID) }
		if binding.SizeBytes == 0 || binding.SizeBytes > portableMediaMaxArtifact { return PortableMediaPlan{}, fmt.Errorf("portable media artifact %q size is outside allowed range", binding.ID) }
		artifacts = append(artifacts, PortableMediaArtifactPlan{ID: binding.ID, Partition: target.partition, TargetPath: target.target(sourceCommit), SHA256: binding.SHA256, SizeBytes: binding.SizeBytes})
	}
	for id := range portableMediaTargets { if !seen[id] { return PortableMediaPlan{}, fmt.Errorf("missing portable media artifact id %q", id) } }
	sort.Slice(artifacts, func(i, j int) bool {
		if artifacts[i].Partition == artifacts[j].Partition {
			if artifacts[i].TargetPath == artifacts[j].TargetPath { return artifacts[i].ID < artifacts[j].ID }
			return artifacts[i].TargetPath < artifacts[j].TargetPath
		}
		return artifacts[i].Partition < artifacts[j].Partition
	})
	return PortableMediaPlan{
		Schema: PortableMediaPlanSchema, Profile: layout.Profile, SourceCommit: sourceCommit, TargetBytes: targetBytes,
		ESPStartLBA: layout.ESPStartLBA, ESPLastLBA: layout.ESPLastLBA, DataStartLBA: layout.PayloadStartLBA, DataLastLBA: layout.PayloadLastLBA,
		Artifacts: artifacts, PhysicalWriteAuthorized: false,
	}, nil
}
