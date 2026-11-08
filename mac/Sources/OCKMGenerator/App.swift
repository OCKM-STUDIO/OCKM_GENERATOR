import SwiftUI
import AppKit

@MainActor final class AppDelegate: NSObject, NSApplicationDelegate {
    weak var engine: Engine?
    func applicationWillTerminate(_ notification: Notification) { engine?.stop() }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

@main struct OCKMGeneratorApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @StateObject private var engine = Engine()
    var body: some Scene {
        Window("OCKM GENERATOR", id: "instrument") {
            VStack(spacing: 0) {
                InstrumentView(engine: engine)
                    .frame(minWidth: 960, minHeight: 600)
                HStack {
                    Text(engine.project == "default" ? "New project" : engine.project)
                    if engine.unsaved { Text("• Unsaved changes").foregroundStyle(.secondary) }
                    Spacer()
                    Text(engine.audioStatus).foregroundStyle(.secondary)
                }
                .font(.system(size: 11)).padding(.horizontal, 14).frame(height: 28)
            }
            .background(Color(white: 0.16))
            .preferredColorScheme(.dark)
            .sheet(isPresented: $engine.showingShortcuts) { ShortcutReference() }
            .onAppear { delegate.engine = engine; engine.start(); NSApp.activate(ignoringOtherApps: true) }
            .alert("OCKM GENERATOR", isPresented: Binding(get: { engine.error != nil }, set: { if !$0 { engine.error = nil } })) {
                Button("OK") { engine.error = nil }
            } message: { Text(engine.error ?? "") }
        }
        .defaultSize(width: 1152, height: 748)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("Save Scene") { engine.command("save") }.keyboardShortcut("s")
                Button("Projects") { engine.command("screen", symbol: "project") }.keyboardShortcut("o")
                Button("Export…") { engine.command("export-sheet") }.keyboardShortcut("e")
                Divider()
                Button("Show Project Files") { engine.revealWorkspace() }
                Button("Show Exports") { engine.revealExports() }
            }
            CommandGroup(replacing: .undoRedo) {
                Button("Undo Instrument Change") { engine.command("undo") }.keyboardShortcut("z")
            }
            CommandGroup(replacing: .appSettings) {
                Button("Instrument Settings…") { engine.command("screen", symbol: "setup") }.keyboardShortcut(",")
            }
            CommandMenu("Instrument") {
                Button(engine.playing ? "Stop" : "Play") { engine.command("play") }
                Button("Builder") { engine.command("screen", symbol: "compose") }.keyboardShortcut("1")
                Button("Perform") { engine.command("screen", symbol: "live") }.keyboardShortcut("2")
                Button("Mixer") { engine.command("screen", symbol: "mixer") }.keyboardShortcut("3")
                Button("Drums") { engine.command("screen", symbol: "drums") }.keyboardShortcut("4")
                Button("Bass") { engine.command("screen", symbol: "bass") }.keyboardShortcut("5")
                Button("Lead") { engine.command("screen", symbol: "lead") }.keyboardShortcut("6")
                Button("Chords") { engine.command("screen", symbol: "chord") }.keyboardShortcut("7")
                Button("Samples") { engine.command("screen", symbol: "vox") }.keyboardShortcut("8")
                Button("FX") { engine.command("screen", symbol: "fx") }.keyboardShortcut("9")
                Button("Arrange") { engine.command("screen", symbol: "arrange") }.keyboardShortcut("0")
            }
            CommandMenu("MIDI") {
                Picker("Input", selection: $engine.inputIndex) {
                    Text("None").tag(-1)
                    ForEach(engine.midiInputs.indices, id: \.self) { Text(engine.midiInputs[$0]).tag($0) }
                }.onChange(of: engine.inputIndex) { _ in engine.selectMIDI() }
                Picker("Output", selection: $engine.outputIndex) {
                    Text("None").tag(-1)
                    ForEach(engine.midiOutputs.indices, id: \.self) { Text(engine.midiOutputs[$0]).tag($0) }
                }.onChange(of: engine.outputIndex) { _ in engine.selectMIDI() }
                Button("Refresh Devices") { engine.refreshMIDI() }
            }
            CommandGroup(replacing: .help) {
                Button("Keyboard Shortcuts") { engine.showingShortcuts = true }.keyboardShortcut("k")
                Button("Engine Diagnostics") { engine.showLog() }
            }
        }
    }
}
