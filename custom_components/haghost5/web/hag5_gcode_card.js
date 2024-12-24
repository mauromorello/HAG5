class Hag5GCodeCard extends HTMLElement {
    setConfig(config) {
        this.config = config;

        // Crea un contenitore per il visualizzatore
        const card = document.createElement('ha-card');
        card.header = config.title || 'GCode Viewer';

        const container = document.createElement('div');
        container.style.width = '100%';
        container.style.height = '300px'; // Altezza personalizzabile
        container.style.overflow = 'hidden';

        // Crea un iframe per visualizzare il GCode
        const iframe = document.createElement('iframe');
        iframe.src = `/local/community/haghost5/hag5_viewer.html?filename=${config.filename || ''}`;
        iframe.style.border = 'none';
        iframe.style.width = '100%';
        iframe.style.height = '100%';

        container.appendChild(iframe);
        card.appendChild(container);

        this.appendChild(card);
    }

    getCardSize() {
        return 3; // Numero di righe occupate nella dashboard
    }
}

customElements.define('hag5-gcode-card', Hag5GCodeCard);
