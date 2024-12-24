class Hag5GCodeCard extends HTMLElement {
    setConfig(config) {
        this.config = config;

        const card = document.createElement('ha-card');
        card.header = config.title || 'GCode Viewer';
        
        const container = document.createElement('div');
        container.style.height = '300px'; // Imposta l'altezza personalizzata
        container.style.overflow = 'hidden';

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
        return 3; // Righe occupate nella dashboard
    }

    static getConfigElement() {
        const element = document.createElement('hui-generic-entity-row');
        element.innerHTML = `
            <div>
                <ha-textfield
                    label="File Name"
                    type="text"
                    configElement="filename"
                ></ha-textfield>
            </div>
        `;
    }
}

customElements.define('hag5-gcode-card', Hag5GCodeCard);
