class Hag5RendererCard extends HTMLElement {

    config;
    content;
    websocket;

    // required
    setConfig(config) {
        this.config = config;
    }

    set hass(hass) {
        const printingFileNameEntity = 'sensor.printing_file_name';
        const printProgressEntity = 'sensor.print_progress';

        const printingFileNameState = hass.states[printingFileNameEntity]?.state || 'unavailable';
        const printProgressState = hass.states[printProgressEntity]?.state || 'unavailable';

        const fileName = printingFileNameState !== 'unavailable' && printingFileNameState.trim() !== '' ? printingFileNameState : 'placeholder.gcode';

        // Initialize the card content if not already initialized
        if (!this.content) {
            this.innerHTML = `
                <ha-card header="3D Print Renderer">
                    <div class="card-content">
                        <iframe id="renderer-iframe" src="/local/community/haghost5/hag5_visualizer.html" style="width: 100%; height: 400px; border: none;"></iframe>
                    </div>
                </ha-card>
            `;
            this.content = this.querySelector('#renderer-iframe');

            // Start WebSocket connection
            this.initializeWebSocket(fileName, printProgressState);
        }
    }

    initializeWebSocket(fileName, progress) {
        const wsUrl = `ws://${window.location.hostname}:8123/api/websocket`;

        this.websocket = new WebSocket(wsUrl);
        this.websocket.onopen = () => {
            console.log('WebSocket connection established.');
        };

        this.websocket.onmessage = (event) => {
            console.log('WebSocket message received:', event.data);
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.websocket.onclose = () => {
            console.warn('WebSocket connection closed.');
        };

        // Send initial file name and progress
        this.sendWebSocketMessage({ fileName, progress });
    }

    sendWebSocketMessage(data) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket is not open. Message not sent:', data);
        }
    }
}

customElements.define('hag5-renderer-card', Hag5RendererCard);
