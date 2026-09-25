//go:build windows

package main

import "testing"

func TestResetWriteResultClearsTerminalState(t *testing.T) {
	writeMu.Lock()
	writeState = physicalWriteState{
		Success:     true,
		Error:       "old error",
		Status:      "old status",
		Hint:        "old hint",
		Determinate: true,
		Percent:     100,
	}
	writeMu.Unlock()

	resetWriteResult()

	writeMu.Lock()
	state := writeState
	writeMu.Unlock()
	if state.Active || state.Success || state.Error != "" || state.Status != "" || state.Hint != "" || state.Determinate || state.Percent != 0 {
		t.Fatalf("terminal write state was not reset: %+v", state)
	}
}

func TestResetWriteResultDoesNotTouchActiveWrite(t *testing.T) {
	writeMu.Lock()
	writeState = physicalWriteState{Active: true, Status: "writing", Percent: 42}
	writeMu.Unlock()

	resetWriteResult()

	writeMu.Lock()
	state := writeState
	writeState = physicalWriteState{}
	writeMu.Unlock()
	if !state.Active || state.Status != "writing" || state.Percent != 42 {
		t.Fatalf("active write state changed unexpectedly: %+v", state)
	}
}
