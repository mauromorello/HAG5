class Hag5OperationsCard extends HTMLElement {
    config;
    iframe;

    // required
    setConfig(config) {
        this.config = config;
    }

    set hass(hass) {
        // Crea il contenuto della card solo se non esiste
        if (!this.iframe) {
            const uploader = this.config.uploader || false;
            const filelist = this.config.filelist || false;
            const debug = this.config.debug || false;

            // Genera la query string con le opzioni
            const queryParams = new URLSearchParams({
                uploader: uploader,
                filelist: filelist,
                debug: debug
            }).toString();

            this.innerHTML = `
                <ha-card header="HAG5 Operations">
                    <div class="card-content">
                        <iframe id="operations-iframe" src="/local/community/haghost5/hag5-operations.html?${queryParams}" style="width: 100%; height: 400px; border: none;"></iframe>
                    </div>
                </ha-card>
            `;
            this.iframe = this.querySelector('#operations-iframe');
        }
    }
}

customElements.define('hag5-operations-card', Hag5OperationsCard);
