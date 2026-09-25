//go:build windows

package main

func resetWriteResult() {
	writeMu.Lock()
	defer writeMu.Unlock()
	if writeState.Active {
		return
	}
	writeState.Success = false
	writeState.Error = ""
	writeState.Status = ""
	writeState.Hint = ""
	writeState.Determinate = false
	writeState.Percent = 0
}
