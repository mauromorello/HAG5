class Hag5RendererCard extends HTMLElement {

    config;
    content;
    currentFilePath;
    currentProgress;

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
        const filePath = `/local/community/haghost5/gcodes/${fileName}`;

        // Check if the file path has changed
        if (this.currentFilePath !== filePath || !this.content) {
            this.currentFilePath = filePath;

            // Initialize or reinitialize the renderer with the new file
            this.innerHTML = `
                <ha-card header="3D Print Renderer">
                    <div class="card-content">
                        <div id="status-container" style="margin-bottom: 10px; font-size: 16px; color: var(--primary-text-color);">
                            In stampa: <b>${fileName}</b> - Completato <b>${printProgressState}%</b>
                        </div>
                        <div id="renderer-container" style="height: 400px; background-color: black;"></div>
                    </div>
                </ha-card>
            `;
            this.content = this.querySelector('#renderer-container');
            this.statusContainer = this.querySelector('#status-container');

            this.initializeRenderer(filePath);
        }

        // Check if the progress has changed
        if (this.currentProgress !== printProgressState) {
            this.currentProgress = printProgressState;

            // Update progress dynamically
            if (this.statusContainer) {
                this.statusContainer.innerHTML = `In stampa: <b>${fileName}</b> - Completato <b>${printProgressState}%</b>`;
            }
        }
    }

    initializeRenderer(filePath) {
        // Clear the previous content
        this.content.innerHTML = '';
        
        const threeScript = document.createElement('script');
        threeScript.src = "https://cdn.jsdelivr.net/npm/three@0.171.0/build/three.module.js";
        threeScript.type = "module";
        threeScript.onload = () => {
            console.log("Three.js loaded successfully.");
        };
        threeScript.onerror = () => {
            console.error("Failed to load Three.js.");
        };
        document.head.appendChild(threeScript);



        const scriptModule = document.createElement('script');
        scriptModule.type = 'module';
        scriptModule.innerHTML = `
            import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.171.0/build/three.module.js';
            import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.171.0/examples/jsm/controls/OrbitControls.js';
            import { GCodeLoader } from 'https://cdn.jsdelivr.net/npm/three@0.171.0/examples/jsm/loaders/GCodeLoader.js';


            let camera, scene, renderer;

            init();
            render();

            function init() {
                const container = document.getElementById('renderer-container');

                camera = new THREE.PerspectiveCamera( 60, container.clientWidth / container.clientHeight, 1, 1000 );
                camera.position.set( 0, 0, 70 );

                scene = new THREE.Scene();

                console.log('Initializing renderer with file:', filePath);
                
                try {
                    const loader = new GCodeLoader();
                    loader.load(filePath, function (object) {
                        console.log('GCode file loaded successfully:', filePath);
                        object.position.set(-100, -20, 100);
                        scene.add(object);
                        render();
                    }, undefined, function (error) {
                        console.error('Error loading GCode file:', error);
                    });
                } catch (e) {
                    console.error('Error during renderer initialization:', e);
                }

                renderer = new THREE.WebGLRenderer( { antialias: true } );
                renderer.setPixelRatio(window.devicePixelRatio);
                renderer.setSize(container.clientWidth, container.clientHeight);
                container.appendChild(renderer.domElement);

                const controls = new OrbitControls(camera, renderer.domElement);
                controls.addEventListener('change', render); // use if there is no animation loop
                controls.minDistance = 10;
                controls.maxDistance = 100;

                window.addEventListener('resize', resize);

                function resize() {
                    camera.aspect = container.clientWidth / container.clientHeight;
                    camera.updateProjectionMatrix();

                    renderer.setSize(container.clientWidth, container.clientHeight);

                    render();
                }
            }

            function render() {
                renderer.render(scene, camera);
            }
        `;

        this.content.appendChild(scriptModule);
    }
}

customElements.define('hag5-renderer-card', Hag5RendererCard);
