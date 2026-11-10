class PcscReader {
    constructor() {
        this.endpoint = 'http://127.0.0.1:8765/uid';
        this.timer = null;
        this.lastUid = null;
    }

    start(onUid, onError = () => {}) {
        this.stop();
        this.timer = setInterval(async () => {
            try {
                const response = await fetch(this.endpoint, { cache: 'no-store' });
                if (!response.ok) return;
                const { uid } = await response.json();
                if (uid && uid !== this.lastUid) {
                    this.lastUid = uid;
                    onUid(uid);
                }
                if (!uid) this.lastUid = null;
            } catch (error) {
                onError(error);
            }
        }, 300);
    }

    stop() {
        if (this.timer !== null) {
            clearInterval(this.timer);
            this.timer = null;
        }
        this.lastUid = null;
    }
}
