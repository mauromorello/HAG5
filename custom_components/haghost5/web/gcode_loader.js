class GCodeLoader extends Loader {

    constructor(manager) {
        super(manager);
        this.splitLayer = false;
    }

    load(url, onLoad, onProgress, onError) {
        const scope = this;
        const loader = new FileLoader(scope.manager);
        loader.setPath(scope.path);
        loader.setRequestHeader(scope.requestHeader);
        loader.setWithCredentials(scope.withCredentials);
        loader.load(
            url,
            function (text) {
                try {
                    onLoad(scope.parse(text));
                } catch (e) {
                    if (onError) {
                        onError(e);
                    } else {
                        console.error(e);
                    }
                    scope.manager.itemError(url);
                }
            },
            onProgress,
            onError
        );
    }

    parse(data, progressPercentage = 0) {
        let totalSegments = 0;
        let state = { x: 0, y: 0, z: 0, e: 0, f: 0, extruding: false, relative: false };
        const layers = [];
        let currentLayer = undefined;

        const pathMaterial = new LineBasicMaterial({ color: 0xFF0000 }); // Red for not printed
        const extrudingMaterial = new LineBasicMaterial({ color: 0x00FF00 }); // Green for printed

        function newLayer(line) {
            currentLayer = { vertex: [], pathVertex: [], z: line.z };
            layers.push(currentLayer);
        }

        function addSegment(p1, p2) {
            if (currentLayer === undefined) {
                newLayer(p1);
            }
            totalSegments++;

            if (state.extruding) {
                currentLayer.vertex.push(p1.x, p1.y, p1.z);
                currentLayer.vertex.push(p2.x, p2.y, p2.z);
            } else {
                currentLayer.pathVertex.push(p1.x, p1.y, p1.z);
                currentLayer.pathVertex.push(p2.x, p2.y, p2.z);
            }
        }

        function delta(v1, v2) {
            return state.relative ? v2 : v2 - v1;
        }

        function absolute(v1, v2) {
            return state.relative ? v1 + v2 : v2;
        }

        const lines = data.replace(/;.+/g, '').split('\n');

        for (let i = 0; i < lines.length; i++) {
            const tokens = lines[i].split(' ');
            const cmd = tokens[0].toUpperCase();

            const args = {};
            tokens.splice(1).forEach(function (token) {
                if (token[0] !== undefined) {
                    const key = token[0].toLowerCase();
                    const value = parseFloat(token.substring(1));
                    args[key] = value;
                }
            });

            if (cmd === 'G0' || cmd === 'G1') {
                const line = {
                    x: args.x !== undefined ? absolute(state.x, args.x) : state.x,
                    y: args.y !== undefined ? absolute(state.y, args.y) : state.y,
                    z: args.z !== undefined ? absolute(state.z, args.z) : state.z,
                    e: args.e !== undefined ? absolute(state.e, args.e) : state.e,
                    f: args.f !== undefined ? absolute(state.f, args.f) : state.f,
                };

                if (delta(state.e, line.e) > 0) {
                    state.extruding = delta(state.e, line.e) > 0;

                    if (currentLayer == undefined || line.z != currentLayer.z) {
                        newLayer(line);
                    }
                }

                addSegment(state, line);
                state = line;
            } else if (cmd === 'G90') {
                state.relative = false;
            } else if (cmd === 'G91') {
                state.relative = true;
            } else if (cmd === 'G92') {
                const line = state;
                line.x = args.x !== undefined ? args.x : line.x;
                line.y = args.y !== undefined ? args.y : line.y;
                line.z = args.z !== undefined ? args.z : line.z;
                line.e = args.e !== undefined ? args.e : line.e;
            }
        }

        function addObject(vertex, extruding, progressPercentage) {
            const geometry = new BufferGeometry();
            geometry.setAttribute('position', new Float32BufferAttribute(vertex, 3));

            const completedSegments = Math.floor(vertex.length * (progressPercentage / 100));
            const remainingSegments = vertex.length - completedSegments;

            const completedMaterial = new LineBasicMaterial({ color: 0x00FF00 }); // Green for completed
            const remainingMaterial = new LineBasicMaterial({ color: 0xFF0000 }); // Red for remaining

            // Completed segments
            const completedGeometry = new BufferGeometry();
            completedGeometry.setAttribute(
                'position',
                new Float32BufferAttribute(vertex.slice(0, completedSegments * 3), 3)
            );
            const completedSegmentsObject = new LineSegments(completedGeometry, completedMaterial);
            object.add(completedSegmentsObject);

            // Remaining segments
            const remainingGeometry = new BufferGeometry();
            remainingGeometry.setAttribute(
                'position',
                new Float32BufferAttribute(vertex.slice(completedSegments * 3), 3)
            );
            const remainingSegmentsObject = new LineSegments(remainingGeometry, remainingMaterial);
            object.add(remainingSegmentsObject);
        }

        const object = new Group();
        object.name = 'gcode';

        if (this.splitLayer) {
            for (let i = 0; i < layers.length; i++) {
                const layer = layers[i];
                addObject(layer.vertex, true, progressPercentage);
                addObject(layer.pathVertex, false, progressPercentage);
            }
        } else {
            const vertex = [],
                pathVertex = [];

            for (let i = 0; i < layers.length; i++) {
                const layer = layers[i];
                const layerVertex = layer.vertex;
                const layerPathVertex = layer.pathVertex;

                for (let j = 0; j < layerVertex.length; j++) {
                    vertex.push(layerVertex[j]);
                }

                for (let j = 0; j < layerPathVertex.length; j++) {
                    pathVertex.push(layerPathVertex[j]);
                }
            }

            addObject(vertex, true, progressPercentage);
            addObject(pathVertex, false, progressPercentage);
        }

        object.rotation.set(-Math.PI / 2, 0, 0);

        return object;
    }
}

// Rendi GCodeLoader disponibile globalmente
window.GCodeLoader = GCodeLoader;
