class Hag5RendererCard extends HTMLElement {
    config;
    iframe;
    currentFileName;
    currentProgress;

    // required
    setConfig(config) {
        this.config = config;
    }

    set hass(hass) {
        const printingFileNameEntity = 'sensor.printing_file_name';
        const printProgressEntity = 'sensor.print_progress';

        const printingFileNameState = hass.states[printingFileNameEntity]?.state || 'unavailable';
        const printProgressState = hass.states[printProgressEntity]?.state || '0';

        // Aggiorna il file in stampa se è cambiato
        if (this.currentFileName !== printingFileNameState) {
            this.currentFileName = printingFileNameState;
            this.updateIframe({ fileName: this.currentFileName, progress: printProgressState });
        }

        // Aggiorna la percentuale se è cambiata
        if (this.currentProgress !== printProgressState) {
            this.currentProgress = printProgressState;
            this.updateIframe({ progress: this.currentProgress });
        }

        // Crea il contenuto della card solo se non esiste
        if (!this.iframe) {
            this.innerHTML = `
                <ha-card header="3D Print Renderer">
                    <div class="card-content">
                        <iframe id="renderer-iframe" src="/local/community/haghost5/hag5_visualizer.html" style="width: 100%; height: 400px; border: none;"></iframe>
                    </div>
                </ha-card>
            `;
            this.iframe = this.querySelector('#renderer-iframe');
        }
    }

    // Funzione per inviare messaggi all'iframe
    updateIframe(data) {
        if (this.iframe && this.iframe.contentWindow) {
            this.iframe.contentWindow.postMessage(data, '*');
            console.log('Sent message to iframe:', data);
        } else {
            console.warn('Iframe not ready to receive messages.');
        }
    }
}

customElements.define('hag5-renderer-card', Hag5RendererCard);
