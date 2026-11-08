import SwiftUI
import AppKit

struct InstrumentView: NSViewRepresentable {
    @ObservedObject var engine: Engine
    func makeNSView(context: Context) -> InstrumentCanvas {
        let view = InstrumentCanvas()
        view.engine = engine
        return view
    }
    func updateNSView(_ view: InstrumentCanvas, context: Context) {
        view.commands = engine.drawing
        view.backdropColor = engine.backgroundColor
        view.isLightTheme = engine.isLightTheme
        view.applyWindowTheme()
        view.needsDisplay = true
    }
}

final class InstrumentCanvas: NSView {
    weak var engine: Engine?
    var commands: [DrawCommand] = []
    var backdropColor = NSColor(calibratedRed: 42/255, green: 42/255, blue: 40/255, alpha: 1)
    var isLightTheme = false
    private var pressed = false
    override var isFlipped: Bool { true }
    override var acceptsFirstResponder: Bool { true }
    private var zoom: CGFloat { min(bounds.width / 960, bounds.height / 600) }
    private var origin: CGPoint { CGPoint(x: (bounds.width - 960 * zoom) / 2, y: (bounds.height - 600 * zoom) / 2) }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        applyWindowTheme()
    }

    func applyWindowTheme() {
        guard let window else { return }
        let name: NSAppearance.Name = isLightTheme ? .aqua : .darkAqua
        if window.appearance?.name != name { window.appearance = NSAppearance(named: name) }
        window.backgroundColor = backdropColor
        window.titlebarAppearsTransparent = true
    }

    override func draw(_ dirtyRect: NSRect) {
        backdropColor.setFill(); bounds.fill()
        guard let context = NSGraphicsContext.current?.cgContext else { return }
        context.saveGState()
        context.translateBy(x: origin.x, y: origin.y)
        context.scaleBy(x: zoom, y: zoom)
        context.clip(to: CGRect(x: 0, y: 0, width: 960, height: 600))
        var color = NSColor.white
        for command in commands {
            let n = command.number
            let rect = CGRect(x: n(0), y: n(1), width: max(0, n(2)), height: max(0, n(3)))
            switch command.kind {
            case "color":
                color = NSColor(calibratedRed: n(0)/255, green: n(1)/255, blue: n(2)/255, alpha: 1)
                context.setFillColor(color.cgColor); context.setStrokeColor(color.cgColor)
            case "background": context.fill(CGRect(x: 0, y: 0, width: 960, height: 600))
            case "rect": context.fill(rect)
            case "round", "outline":
                let path = CGPath(roundedRect: rect, cornerWidth: n(4), cornerHeight: n(4), transform: nil)
                context.addPath(path)
                if command.kind == "outline" { context.setLineWidth(n(5)); context.strokePath() }
                else { context.fillPath() }
            case "ellipse": context.fillEllipse(in: rect)
            case "path":
                if command.values.count >= 4 {
                    context.beginPath(); context.move(to: CGPoint(x: n(0), y: n(1)))
                    for i in stride(from: 2, to: command.values.count - 1, by: 2) { context.addLine(to: CGPoint(x: n(i), y: n(i+1))) }
                    context.closePath(); context.fillPath()
                }
            case "text":
                let size = n(3)
                let width: CGFloat = size >= 36 ? 22 : size >= 24 ? 14 : size >= 16 ? 10 : size >= 12 ? 7 : size >= 10 ? 6 : 5
                let font = NSFont.monospacedSystemFont(ofSize: width / 0.602, weight: .regular)
                let paragraph = NSMutableParagraphStyle(); paragraph.lineBreakMode = .byWordWrapping
                let attributes: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: color, .paragraphStyle: paragraph]
                (command.text(4) as NSString).draw(in: CGRect(x: n(0), y: n(1), width: max(n(2), 1), height: 600-n(1)), withAttributes: attributes)
            default: break
            }
        }
        context.restoreGState()
    }

    private func point(_ event: NSEvent) -> CGPoint {
        let p = convert(event.locationInWindow, from: nil)
        return CGPoint(x: (p.x - origin.x)/zoom, y: (p.y-origin.y)/zoom)
    }
    override func mouseDown(with event: NSEvent) {
        window?.makeFirstResponder(self)
        let p = point(event)
        guard CGRect(x: 0, y: 0, width: 960, height: 600).contains(p) else { return }
        pressed = true; engine?.command("press", x: p.x, y: p.y)
    }
    override func mouseDragged(with event: NSEvent) {
        guard pressed else { return }; let p = point(event); engine?.command("move", x: p.x, y: p.y)
    }
    override func mouseUp(with event: NSEvent) {
        guard pressed else { return }; pressed = false; let p = point(event); engine?.command("release", x: p.x, y: p.y)
    }
    override func keyDown(with event: NSEvent) {
        if event.keyCode == 49 { engine?.command("play") } else { super.keyDown(with: event) }
    }
}
