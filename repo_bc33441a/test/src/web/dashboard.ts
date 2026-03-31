interface AppSettings {
    version: string;
    debug: boolean;
}

class Dashboard {
    private settings: AppSettings;

    constructor(version: string) {
        this.settings = { version, debug: true };
    }

    public init() {
        console.log(`Aegis Web UI v${this.settings.version} initialized.`);
        this.triggerEncryption("test_payload");
    }

    private triggerEncryption(payload: string) {
        // Calls the Python backend API
        fetch('/api/encrypt', {
            method: 'POST',
            body: JSON.stringify({ data: payload })
        });
    }
}