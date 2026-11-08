// swift-tools-version: 5.9
import PackageDescription
import Foundation

let deps = ProcessInfo.processInfo.environment["OCKM_DEPS"] ?? ".build/deps"
let package = Package(
    name: "OCKMGenerator", platforms: [.macOS(.v13)],
    products: [.executable(name: "OCKMGenerator", targets: ["OCKMGenerator"])],
    targets: [
        .target(name: "EngineBridge", publicHeadersPath: "include",
                cxxSettings: [.unsafeFlags(["-I\(deps)/libpd/libpd_wrapper", "-I\(deps)/libpd/pure-data/src"])],
                linkerSettings: [.unsafeFlags(["\(deps)/libpdlua.a", "\(deps)/libpd/libs/libpd.a"]),
                                 .linkedFramework("CoreMIDI"), .linkedFramework("CoreFoundation")]),
        .executableTarget(name: "OCKMGenerator", dependencies: ["EngineBridge"])
    ], cxxLanguageStandard: .cxx17
)
