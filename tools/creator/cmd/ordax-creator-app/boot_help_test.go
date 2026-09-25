package main

import (
	"strings"
	"testing"
)

func TestCreatorBootHelpExplainsUSBAndInternalDiskBoundary(t *testing.T) {
	text := creatorBootHelpText()
	for _, required := range []string{"menu de boot/UEFI", "USB/UEFI", "SSD ou HD interno", "não instala"} {
		if !strings.Contains(text, required) {
			t.Fatalf("boot help missing %q: %q", required, text)
		}
	}
}
