import AppKit
import SwiftUI

@MainActor final class KeyboardController {
    private weak var engine: Engine?
    private var monitor: Any?
    private var observer: NSObjectProtocol?
    private var menuObservers: [NSObjectProtocol] = []
    private var menuTracking = false
    private var held = Set<String>()
    private let keys: Set<String> = [" ", "r", "w", "d", "b", "z", "x", "c", "v", "n", "m", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "escape"]

    init(engine: Engine) {
        self.engine = engine
        monitor = NSEvent.addLocalMonitorForEvents(matching: [.keyDown, .keyUp]) { [weak self] event in
            guard let self else { return event }
            return self.handle(event)
        }
        observer = NotificationCenter.default.addObserver(forName: NSApplication.didResignActiveNotification, object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in self?.releaseAll() }
        }
        for name in [NSMenu.didBeginTrackingNotification, NSMenu.didEndTrackingNotification] {
            menuObservers.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] note in
                Task { @MainActor in
                    self?.menuTracking = note.name == NSMenu.didBeginTrackingNotification
                    if self?.menuTracking == true { self?.releaseAll() }
                }
            })
        }
    }
    private func handle(_ event: NSEvent) -> NSEvent? {
        let key = event.keyCode == 53 ? "escape" : (event.charactersIgnoringModifiers ?? "").lowercased()
        // A key-up must release its effect even if modifiers or focus changed.
        if event.type == .keyUp, held.remove(key) != nil { engine?.command("key-up", symbol: key); return nil }
        guard event.type == .keyDown, keys.contains(key), !menuTracking,
              event.modifierFlags.intersection([.command, .control, .option]).isEmpty,
              !(NSApp.keyWindow?.firstResponder is NSTextView), NSApp.modalWindow == nil,
              NSApp.keyWindow?.attachedSheet == nil, NSApp.keyWindow?.sheetParent == nil,
              engine?.showingShortcuts != true else { return event }
        if !event.isARepeat, held.insert(key).inserted { engine?.command("key-down", symbol: key) }
        return nil
    }
    func releaseAll() {
        for key in held { engine?.command("key-up", symbol: key) }
        held.removeAll(); engine?.command("cancel-touch")
    }
    func stop() {
        releaseAll()
        if let monitor { NSEvent.removeMonitor(monitor) }; monitor = nil
        if let observer { NotificationCenter.default.removeObserver(observer) }; observer = nil
        for observer in menuObservers { NotificationCenter.default.removeObserver(observer) }; menuObservers = []
    }
}

struct ShortcutReference: View {
    @Environment(\.dismiss) private var dismiss
    private let sections: [(String, [(String,String)])] = [
        ("Play", [("Space", "Play / stop"), ("1–8", "Mute / bring back drum tracks"), ("9 · 0 · − · =", "Mute bass · lead · chords · samples"),
                  ("R", "Rise on / off"), ("W", "Rewind"), ("Hold D", "Drop"), ("Hold B", "Beat repeat"),
                  ("Z · X · C · V · N · M", "Recipe pads A–F (tap or hold)"), ("Esc", "Close a pop-up or release performance moves")]),
        ("Navigate", [("⌘1 · ⌘2 · ⌘3", "Builder · perform · mixer"), ("⌘4 · ⌘5 · ⌘6", "Drums · bass · lead"),
                      ("⌘7 · ⌘8 · ⌘9 · ⌘0", "Chords · samples · FX · arrange"), ("⌘O", "Projects"), ("⌘,", "Instrument settings")]),
        ("Keep & export", [("⌘S", "Save a new scene"), ("⌘Z", "Undo the last supported instrument change"), ("⌘E", "Export options"), ("⌘K", "This shortcut reference")])
    ]
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Keyboard shortcuts").font(.title2.bold())
            Text("Play the instrument from your Mac keyboard. Mutes follow the timing selected on Perform.")
                .foregroundStyle(.secondary)
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    ForEach(sections, id: \.0) { title, rows in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(title).font(.headline)
                            ForEach(rows, id: \.0) { key, action in
                                HStack(alignment: .top) {
                                    Text(key).font(.system(.body, design: .monospaced)).frame(width: 170, alignment: .leading)
                                    Text(action).frame(maxWidth: .infinity, alignment: .leading)
                                }
                            }
                        }
                    }
                }
            }
            Text("Held effects release when you let go or switch to another app. Shortcuts pause while a text field or dialog is active.")
                .font(.footnote).foregroundStyle(.secondary)
            HStack { Spacer(); Button("Done") { dismiss() }.keyboardShortcut(.defaultAction) }
        }.padding(28).frame(width: 660, height: 680)
    }
}
