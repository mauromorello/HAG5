class Hag5RendererCard extends HTMLElement {

    config;
    content;
    websocketServer;

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

            // Start WebSocket server
            this.startWebSocketServer();
        }

        // Send updated data to the WebSocket clients
        this.broadcastWebSocketMessage({ fileName, progress: printProgressState });
    }

    startWebSocketServer() {
        this.websocketServer = new WebSocketServer({ port: 12345 }); // Port for WebSocket server

        this.websocketServer.on('connection', (socket) => {
            console.log('WebSocket client connected.');

            socket.on('message', (message) => {
                console.log('Received message from client:', message);
            });

            socket.on('close', () => {
                console.log('WebSocket client disconnected.');
            });
        });
    }

    broadcastWebSocketMessage(data) {
        if (this.websocketServer) {
            this.websocketServer.clients.forEach((client) => {
                if (client.readyState === WebSocket.OPEN) {
                    client.send(JSON.stringify(data));
                }
            });
        }
    }
}

customElements.define('hag5-renderer-card', Hag5RendererCard);
