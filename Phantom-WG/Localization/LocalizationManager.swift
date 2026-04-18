import Foundation

@Observable
final class LocalizationManager {

    enum Language: String, CaseIterable, Identifiable {
        case tr, en
        var id: String { rawValue }

        var flag: String {
            switch self {
            case .tr: return "\u{1F1F9}\u{1F1F7}"
            case .en: return "\u{1F1FA}\u{1F1F8}"
            }
        }
    }

    @ObservationIgnored static let shared = LocalizationManager()

    var current: Language {
        didSet {
            guard current != oldValue else { return }
            UserDefaults.standard.set(current.rawValue, forKey: "app_language")
            loadStrings()
        }
    }

    /// Observed so that views calling `t(_:)` re-render when the dictionary
    /// is reloaded after a language switch. Without this, `@Observable` would
    /// only track `current`, and callers would see stale translations because
    /// `t(_:)` reads `strings` internally (not `current`).
    private var strings: [String: String] = [:]

    init() {
        // Resolve initial language: saved preference → device locale → English.
        if let saved = UserDefaults.standard.string(forKey: "app_language"),
           let lang = Language(rawValue: saved) {
            self.current = lang
        } else if Locale.current.language.languageCode?.identifier == "tr" {
            self.current = .tr
        } else {
            self.current = .en
        }
        loadStrings()
    }

    /// Simple key lookup.
    func t(_ key: String) -> String {
        strings[key] ?? key
    }

    /// Key lookup with format arguments (%d, %@, etc.).
    func t(_ key: String, _ args: CVarArg...) -> String {
        let template = strings[key] ?? key
        return String(format: template, arguments: args)
    }

    private func loadStrings() {
        guard let url = Bundle.main.url(forResource: current.rawValue, withExtension: "json", subdirectory: "translations"),
              let data = try? Data(contentsOf: url),
              let dict = try? JSONDecoder().decode([String: String].self, from: data)
        else { return }
        strings = dict
    }
}
