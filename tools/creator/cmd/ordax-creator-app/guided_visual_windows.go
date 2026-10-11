//go:build windows

package main

import (
    "fmt"
    "strings"
    "syscall"
    "unsafe"
)

const (
    wmPaint = 0x000F
    colorWindow = 5
    colorWindowText = 8
    colorHighlight = 13
    colorHighlightText = 14
    colorBtnFace = 15
    colorGrayText = 17
    transparent = 1
    dtCenter = 0x00000001
    dtVCenter = 0x00000004
    dtSingleLine = 0x00000020
    dtWordBreak = 0x00000010
)

type rect struct { Left, Top, Right, Bottom int32 }
type paintStruct struct {
    Hdc uintptr
    Erase int32
    Paint rect
    Restore int32
    IncUpdate int32
    Reserved [32]byte
}

var (
    procBeginPaint = user32.NewProc("BeginPaint")
    procEndPaint = user32.NewProc("EndPaint")
    procInvalidateRect = user32.NewProc("InvalidateRect")
    procGetClientRect = user32.NewProc("GetClientRect")
    procFillRect = user32.NewProc("FillRect")
    procGetSysColor = user32.NewProc("GetSysColor")
    procDrawTextW = user32.NewProc("DrawTextW")
    procCreateSolidBrush = gdi32.NewProc("CreateSolidBrush")
    procCreatePen = gdi32.NewProc("CreatePen")
    procDeleteObject = gdi32.NewProc("DeleteObject")
    procSelectObject = gdi32.NewProc("SelectObject")
    procEllipse = gdi32.NewProc("Ellipse")
    procRoundRect = gdi32.NewProc("RoundRect")
    procMoveToEx = gdi32.NewProc("MoveToEx")
    procLineTo = gdi32.NewProc("LineTo")
    procSetBkMode = gdi32.NewProc("SetBkMode")
    procSetTextColor = gdi32.NewProc("SetTextColor")
)

func sysColor(index uintptr) uintptr {
    c, _, _ := procGetSysColor.Call(index)
    return c
}

func creatorClientRect() rect {
    var r rect
    if mainWindow != 0 { procGetClientRect.Call(mainWindow, uintptr(unsafe.Pointer(&r))) }
    return r
}

func invalidateGuidedVisual() {
    if mainWindow != 0 { procInvalidateRect.Call(mainWindow, 0, 1) }
}

func currentGuidedExperience() creatorExperienceView {
    stateMu.Lock()
    state := refreshState
    stateMu.Unlock()
    input := creatorExperienceInput{
        TargetCount: len(state.Targets),
        TargetSelected: selectedTargetIndex() >= 0,
        PhysicalReady: state.PhysicalReady,
    }
    if state.Error != "" { input.ErrorMessageID = msgRefreshFailedDetail }
    writeMu.Lock()
    write := writeState
    writeMu.Unlock()
    input.WriteActive = write.Active
    input.WriteComplete = !write.Active && write.Success
    if write.Error != "" { input.ErrorMessageID = msgPhysicalWriteFailedDetail }
    return creatorExperience(input)
}

func drawTextInRect(hdc uintptr, text string, bounds rect, flags uintptr, color uintptr) {
    chars, err := syscall.UTF16FromString(text)
    if err != nil || len(chars) == 0 { return }
    procSetBkMode.Call(hdc, transparent)
    procSetTextColor.Call(hdc, color)
    procDrawTextW.Call(hdc,
        uintptr(unsafe.Pointer(&chars[0])),
        uintptr(len(chars)-1),
        uintptr(unsafe.Pointer(&bounds)),
        flags,
    )
}

func drawCreatorPanel(hdc uintptr, bounds rect, fill, border string, radius int32) {
    brush, _, _ := procCreateSolidBrush.Call(creatorColorFor(fill, colorBtnFace))
    pen, _, _ := procCreatePen.Call(0, 1, creatorColorFor(border, colorGrayText))
    oldBrush, _, _ := procSelectObject.Call(hdc, brush)
    oldPen, _, _ := procSelectObject.Call(hdc, pen)
    procRoundRect.Call(hdc, uintptr(bounds.Left), uintptr(bounds.Top), uintptr(bounds.Right), uintptr(bounds.Bottom), uintptr(radius), uintptr(radius))
    procSelectObject.Call(hdc, oldPen)
    procSelectObject.Call(hdc, oldBrush)
    procDeleteObject.Call(pen)
    procDeleteObject.Call(brush)
}

func drawCreatorCircle(hdc uintptr, bounds rect, fill, text string, textColor uintptr) {
    brush, _, _ := procCreateSolidBrush.Call(creatorColorFor(fill, colorHighlight))
    oldBrush, _, _ := procSelectObject.Call(hdc, brush)
    pen, _, _ := procCreatePen.Call(0, 1, creatorColorFor("border", colorGrayText))
    oldPen, _, _ := procSelectObject.Call(hdc, pen)
    procEllipse.Call(hdc, uintptr(bounds.Left), uintptr(bounds.Top), uintptr(bounds.Right), uintptr(bounds.Bottom))
    procSelectObject.Call(hdc, oldBrush)
    procSelectObject.Call(hdc, oldPen)
    procDeleteObject.Call(brush)
    procDeleteObject.Call(pen)
    drawTextInRect(hdc, text, bounds, dtCenter|dtVCenter|dtSingleLine, textColor)
}

func drawCreatorRail(hdc uintptr, left int32, view creatorExperienceView) {
    titles := [4]string{
        creatorT(msgConnectTitle),
        creatorT(msgSelectTitle),
        creatorT(msgReviewTitle),
        creatorT(msgCompleteTitle),
    }
    active := view.StepNumber
    if active < 1 { active = 1 }
    for i := 1; i <= 4; i++ {
        y := int32(217 + (i-1)*70)
        if i != 4 {
            pen, _, _ := procCreatePen.Call(0, 2, creatorColorFor("border", colorGrayText))
            old, _, _ := procSelectObject.Call(hdc, pen)
            procMoveToEx.Call(hdc, uintptr(left+36), uintptr(y+33), 0)
            procLineTo.Call(hdc, uintptr(left+36), uintptr(y+70))
            procSelectObject.Call(hdc, old)
            procDeleteObject.Call(pen)
        }
        done := i < active || view.Step == creatorStepComplete
        fill := "surface"
        if done || i == active { fill = "brand_blue" }
        text := fmt.Sprintf("%d", i)
        if done { text = "✓" }
        labelColor := creatorColorFor("muted", colorWindowText)
        if done || i == active { labelColor = creatorColorFor("text", colorWindowText) }
        drawCreatorCircle(hdc, rect{left+19, y, left+53, y+34}, fill, text, creatorColorFor("text", colorHighlightText))
        drawTextInRect(hdc, titles[i-1], rect{left+69, y+2, left+288, y+28}, dtSingleLine, labelColor)
    }
}

func drawCreatorUSBStatus(hdc uintptr, left int32, view creatorExperienceView) {
    box := rect{left+16, 503, left+286, 584}
    drawCreatorPanel(hdc, box, "panel", "border", 12)
    stateMu.Lock()
    targets := refreshState.Targets
    stateMu.Unlock()
    selection := selectedTargetIndex()
    selected := selection >= 0 && selection < len(targets)
    if !selected {
        drawTextInRect(hdc, creatorT(msgConnectTitle), rect{left+35, 524, left+270, 548}, dtSingleLine, creatorColorFor("muted", colorGrayText))
        return
    }
    target := targets[selection]
    drawTextInRect(hdc, "USB detectado", rect{left+34, 513, left+260, 536}, dtSingleLine, creatorColorFor("text", colorWindowText))
    display := strings.TrimSpace(target.DriveLetter + " · " + target.VolumeLabel)
    if len([]rune(display)) > 28 { display = string([]rune(display)[:26]) + "…" }
    drawTextInRect(hdc, display, rect{left+34, 540, left+268, 560}, dtSingleLine, creatorColorFor("muted", colorGrayText))
    drawTextInRect(hdc, formatBytes(target.PhysicalDiskBytes), rect{left+34, 560, left+268, 580}, dtSingleLine, creatorColorFor("accent", colorHighlight))
}

func paintGuidedVisual(hwnd uintptr) uintptr {
    var ps paintStruct
    hdc, _, _ := procBeginPaint.Call(hwnd, uintptr(unsafe.Pointer(&ps)))
    if hdc == 0 { return 0 }
    defer procEndPaint.Call(hwnd, uintptr(unsafe.Pointer(&ps)))
    client := creatorClientRect()
    right := client.Right
    if right < 1090 { right = 1090 }
    sidebar := right - 306
    mainRight := sidebar - 18

    bg, _, _ := procCreateSolidBrush.Call(creatorColorFor("background", colorWindow))
    procFillRect.Call(hdc, uintptr(unsafe.Pointer(&client)), bg)
    procDeleteObject.Call(bg)

    drawCreatorPanel(hdc, rect{22, 19, right-21, 159}, "surface", "border", 18)
    drawCreatorPanel(hdc, rect{22, 174, 329, 285}, "panel", "border", 13)
    drawCreatorPanel(hdc, rect{344, 174, mainRight, 285}, "panel", "border", 13)
    view := currentGuidedExperience()
    cardBorder := "border"
    if view.Step == creatorStepBlocked { cardBorder = "warning" }
    if view.Step == creatorStepReview || view.Step == creatorStepComplete { cardBorder = "success" }
    drawCreatorPanel(hdc, rect{22, 301, mainRight, 500}, "panel", cardBorder, 15)
    iconFill := "accent"
    if view.Step == creatorStepBlocked { iconFill = "warning" }
    if view.Step == creatorStepReview || view.Step == creatorStepComplete { iconFill = "success" }
    symbol := "i"
    if view.Step == creatorStepBlocked { symbol = "!" }
    if view.Step == creatorStepReview || view.Step == creatorStepComplete { symbol = "✓" }
    drawCreatorCircle(hdc, rect{49, 348, 92, 391}, iconFill, symbol, creatorColorFor("background", colorWindow))
    drawCreatorPanel(hdc, rect{22, 514, mainRight, client.Bottom-77}, "panel", "border", 12)
    drawTextInRect(hdc, "Status", rect{43, 525, 190, 551}, dtSingleLine, creatorColorFor("accent", colorHighlight))

    drawCreatorPanel(hdc, rect{sidebar, 174, right-21, client.Bottom-20}, "panel", "border", 16)
    creatorDrawOfficialLogo(hdc, 44, 55, 75, 75)
    drawTextInRect(hdc, "Seu OrdaX USB", rect{sidebar+32, 187, right-38, 213}, dtSingleLine, creatorColorFor("text", colorWindowText))
    drawCreatorRail(hdc, sidebar, view)
    drawCreatorUSBStatus(hdc, sidebar, view)
    return 0
}
