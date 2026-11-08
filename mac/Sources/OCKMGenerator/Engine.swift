import AppKit
import AVFoundation
import Combine
import EngineBridge

struct DrawCommand {
    let kind: String
    let values: [Any]
    func number(_ index: Int) -> CGFloat { (values.indices.contains(index) ? values[index] as? NSNumber : nil)?.doubleValue ?? 0 }
    func text(_ index: Int) -> String { values.indices.contains(index) ? values[index] as? String ?? "" : "" }
}

@MainActor final class Engine: ObservableObject {
    @Published var drawing: [DrawCommand] = []
    @Published var backgroundColor = NSColor(calibratedRed: 42/255, green: 42/255, blue: 40/255, alpha: 1)
    @Published var isLightTheme = false
    @Published var error: String?
    @Published var playing = false
    @Published var unsaved = false
    @Published var project = "default"
    @Published var audioStatus = "Starting audio…"
    @Published var inputIndex = -1
    @Published var outputIndex = -1
    @Published var midiInputs: [String] = []
    @Published var midiOutputs: [String] = []
    @Published var showingShortcuts = false
    private var keyboard: KeyboardController?
    private var audio = AVAudioEngine()
    private var source: AVAudioSourceNode?
    private var timer: Timer?
    private var observer: NSObjectProtocol?
    private var opened = false
    private var restarting = false
    private(set) var workspace: URL?

    func start() {
        guard !opened else { return }
        do {
            let folder = try prepareWorkspace()
            workspace = folder
            let result = ockm_open(folder.path, 48000)
            guard result == 0 else { throw failure("The sound engine could not start (\(result)).") }
            opened = true
            try startAudio()
            refreshMIDI()
            keyboard = KeyboardController(engine: self)
            timer = Timer.scheduledTimer(withTimeInterval: 0.04, repeats: true) { [weak self] _ in
                Task { @MainActor in self?.refreshFrame() }
            }
            observer = NotificationCenter.default.addObserver(forName: .AVAudioEngineConfigurationChange, object: audio, queue: .main) { [weak self] _ in
                Task { @MainActor in self?.restartAudio() }
            }
        } catch { self.error = error.localizedDescription; audioStatus = "Audio unavailable" }
    }

    private func prepareWorkspace() throws -> URL {
        let files = FileManager.default
        let env = ProcessInfo.processInfo.environment
        let source = env["OCKM_RUNTIME"].map { URL(fileURLWithPath: $0) }
            ?? Bundle.main.resourceURL!.appendingPathComponent("Engine")
        guard files.fileExists(atPath: source.appendingPathComponent("OCKM_GENERATOR.pd").path) else {
            throw failure("The app’s engine files are missing. Build the app with mac/scripts/build.py.")
        }
        let destination: URL
        if let path = env["OCKM_WORKSPACE"] { destination = URL(fileURLWithPath: path) }
        else {
            destination = try files.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
                .appendingPathComponent("OCKM GENERATOR/Workspace", isDirectory: true)
        }
        guard destination.standardizedFileURL != source.standardizedFileURL else { throw failure("Choose a separate workspace for your projects.") }
        try files.createDirectory(at: destination, withIntermediateDirectories: true)
        // Replace only managed code. User projects, samples and settings survive updates.
        for name in ["voices", "seq", "ui", "lab", "pdlua", "Licenses", "OCKM_GENERATOR.pd"] {
            let target = destination.appendingPathComponent(name)
            let incoming = destination.appendingPathComponent(".incoming-" + name)
            if files.fileExists(atPath: incoming.path) { try files.removeItem(at: incoming) }
            try files.copyItem(at: source.appendingPathComponent(name), to: incoming)
            if files.fileExists(atPath: target.path) { try files.removeItem(at: target) }
            try files.moveItem(at: incoming, to: target)
        }
        for name in ["projects", "samples"] where !files.fileExists(atPath: destination.appendingPathComponent(name).path) {
            try files.copyItem(at: source.appendingPathComponent(name), to: destination.appendingPathComponent(name))
        }
        return destination
    }

    private func startAudio() throws {
        let format = AVAudioFormat(standardFormatWithSampleRate: 48000, channels: 2)!
        if source == nil {
            let node = AVAudioSourceNode(format: format) { _, _, frames, data in
                let buffers = UnsafeMutableAudioBufferListPointer(data)
                guard buffers.count == 2, let l = buffers[0].mData, let r = buffers[1].mData else { return -50 }
                ockm_render(l.assumingMemoryBound(to: Float.self), r.assumingMemoryBound(to: Float.self), frames)
                return noErr
            }
            source = node; audio.attach(node)
        }
        audio.connect(source!, to: audio.mainMixerNode, format: format)
        audio.prepare()
        try audio.start()
        audioStatus = "Audio ready"
    }

    private func restartAudio() {
        guard opened, !restarting else { return }
        restarting = true
        audio.stop()
        do { try startAudio(); error = nil }
        catch { self.error = "The audio output changed. \(error.localizedDescription)"; audioStatus = "Audio unavailable" }
        restarting = false
    }

    private func refreshFrame() {
        guard let pointer = ockm_copy_frame() else { return }
        defer { ockm_free(pointer) }
        guard let data = String(cString: pointer).data(using: .utf8),
              let items = try? JSONSerialization.jsonObject(with: data) as? [[Any]] else { return }
        let commands: [DrawCommand] = items.compactMap { row in
            guard let kind = row.first as? String else { return nil }
            let command = DrawCommand(kind: kind, values: Array(row.dropFirst()))
            if kind == "state" {
                playing = command.number(0) != 0; unsaved = command.number(2) != 0; project = command.text(3)
                return nil
            }
            return command
        }
        // Use the actual instrument background, including its current theme,
        // for all native chrome and unused space around the scaled canvas.
        var color: NSColor?
        for command in commands {
            if command.kind == "color" {
                color = NSColor(calibratedRed: command.number(0)/255, green: command.number(1)/255,
                                blue: command.number(2)/255, alpha: 1)
            } else if command.kind == "background", let color {
                if !backgroundColor.isEqual(color) { backgroundColor = color }
                let light = 0.2126 * color.redComponent + 0.7152 * color.greenComponent + 0.0722 * color.blueComponent > 0.5
                if isLightTheme != light { isLightTheme = light }
                break
            }
        }
        drawing = commands
    }

    func command(_ selector: String, x: CGFloat? = nil, y: CGFloat? = nil, symbol: String? = nil) {
        guard opened else { return }
        ockm_command(selector, symbol, Float(x ?? 0), Float(y ?? 0), symbol != nil ? 1 : x == nil ? 0 : y == nil ? 1 : 2)
    }

    func refreshMIDI() {
        func names(_ output: Bool) -> [String] {
            let count = output ? ockm_midi_output_count() : ockm_midi_input_count()
            return (0..<count).map { index in
                guard let p = ockm_midi_name(output ? 1 : 0, index) else { return "Unavailable" }
                defer { ockm_free(p) }; return String(cString: p)
            }
        }
        midiInputs = names(false); midiOutputs = names(true)
        inputIndex = -1; outputIndex = -1; selectMIDI()
    }
    func selectMIDI() { ockm_midi_select(Int32(inputIndex), Int32(outputIndex)) }
    func revealWorkspace() { if let workspace { NSWorkspace.shared.open(workspace) } }
    func revealExports() { if let workspace { let url = workspace.appendingPathComponent("exports"); try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true); NSWorkspace.shared.open(url) } }
    func showLog() {
        guard let p = ockm_copy_log() else { return }; defer { ockm_free(p) }
        let alert = NSAlert(); alert.messageText = "Engine diagnostics"
        alert.informativeText = "Audio buffer underruns: \(ockm_underruns()).\n\n" + String(cString: p).suffix(5000)
        alert.runModal()
    }
    func stop() {
        keyboard?.stop(); keyboard = nil
        timer?.invalidate(); timer = nil
        if let observer { NotificationCenter.default.removeObserver(observer) }
        audio.stop()
        if opened { ockm_close(); opened = false }
    }
    private func failure(_ text: String) -> NSError { NSError(domain: "OCKM", code: 1, userInfo: [NSLocalizedDescriptionKey: text]) }
}
