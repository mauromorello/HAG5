class Hag5RendererCard extends HTMLElement {

    config;
    content;

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
        }

        // Send data to iframe
        this.sendMessageToIframe({ fileName, progress: printProgressState });
    }

    sendMessageToIframe(data) {
        if (this.content) {
            this.content.contentWindow.postMessage(data, '*');
        } else {
            console.warn('Iframe is not ready. Message not sent:', data);
        }
    }
}

customElements.define('hag5-renderer-card', Hag5RendererCard);
