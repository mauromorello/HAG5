import { LitElement, html, css } from 'lit';

class Hag5GCodeCard extends LitElement {
    static get properties() {
        return {
            config: { type: Object },
        };
    }

    static get styles() {
        return css`
            .card {
                padding: 16px;
                background-color: var(--ha-card-background, white);
                color: var(--primary-text-color, black);
                overflow: hidden;
                height: 100%;
            }
            iframe {
                border: none;
                width: 100%;
                height: 300px; /* Altezza personalizzabile */
            }
        `;
    }

    setConfig(config) {
        if (!config || !config.filename) {
            throw new Error("Devi specificare 'filename' nella configurazione della card.");
        }
        this.config = config;
    }

    getCardSize() {
        return 3; // Numero di righe occupate
    }

    render() {
        if (!this.config) {
            return html`<div class="card">Configurazione non valida!</div>`;
        }

        const filename = this.config.filename || '';
        const title = this.config.title || 'GCode Viewer';

        return html`
            <ha-card header="${title}">
                <div class="card">
                    <iframe
                        src="/local/community/haghost5/hag5_viewer.html?filename=${filename}"
                    ></iframe>
                </div>
            </ha-card>
        `;
    }

    // Config editor per l'interfaccia Lovelace
    static async getConfigElement() {
        const { LitElement, html } = await import("https://unpkg.com/lit?module");
        class ConfigEditor extends LitElement {
            static get properties() {
                return {
                    hass: {},
                    config: {},
                };
            }

            setConfig(config) {
                this.config = config;
            }

            render() {
                return html`
                    <div>
                        <paper-input
                            label="Titolo"
                            .value=${this.config.title || ''}
                            @value-changed=${e =>
                                this._updateConfig({ title: e.target.value })}
                        ></paper-input>
                        <paper-input
                            label="Nome file"
                            .value=${this.config.filename || ''}
                            @value-changed=${e =>
                                this._updateConfig({ filename: e.target.value })}
                        ></paper-input>
                    </div>
                `;
            }

            _updateConfig(changedProps) {
                this.dispatchEvent(
                    new CustomEvent("config-changed", {
                        detail: { config: { ...this.config, ...changedProps } },
                    })
                );
            }
        }
        customElements.define("hag5-gcode-card-editor", ConfigEditor);
        return document.createElement("hag5-gcode-card-editor");
    }

    static getStubConfig() {
        return {
            title: "GCode Viewer",
            filename: "example.gcode",
        };
    }
}

customElements.define('hag5-gcode-card', Hag5GCodeCard);
