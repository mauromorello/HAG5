class Hag5RendererCard extends HTMLElement {

    config;
    content;

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

        // done once
        if (!this.content) {
            this.innerHTML = `
                <ha-card header="3D Print Renderer">
                    <div class="card-content">
                        <div id="renderer-container" style="height: 400px; background-color: black;"></div>
                    </div>
                </ha-card>
            `;
            this.content = this.querySelector('#renderer-container');

            this.initializeRenderer(filePath);
        }
    }

    initializeRenderer(filePath) {
        const container = this.content;

        // Create and append the canvas
        const scriptImportMap = document.createElement('script');
        scriptImportMap.type = 'importmap';
        scriptImportMap.innerHTML = JSON.stringify({
            imports: {
                "three": "https://cdn.jsdelivr.net/npm/three@0.171.0/build/three.module.js",
                "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.171.0/examples/jsm/"
            }
        });
        container.appendChild(scriptImportMap);

        const scriptModule = document.createElement('script');
        scriptModule.type = 'module';
        scriptModule.innerHTML = `
            import * as THREE from 'three';
            import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
            import { GCodeLoader } from 'three/addons/loaders/GCodeLoader.js';

            let camera, scene, renderer;

            init();
            render();

            function init() {
                camera = new THREE.PerspectiveCamera( 60, container.clientWidth / container.clientHeight, 1, 1000 );
                camera.position.set( 0, 0, 70 );

                scene = new THREE.Scene();

                const loader = new GCodeLoader();
                loader.load('${filePath}', function (object) {
                    object.position.set(-100, -20, 100);
                    scene.add(object);

                    render();
                }, undefined, function (error) {
                    console.error('Errore durante il caricamento del file GCode:', error);
                });

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

        container.appendChild(scriptModule);
    }
}

customElements.define('hag5-renderer-card', Hag5RendererCard);
