import { AnimationMixer } from '../animation/AnimationMixer.js';
import { AppUtils } from '../extras/AppUtils.js';
import { BloomPass } from '../postprocessing/BloomPass.js';
import { BrightnessContrastPass } from '../postprocessing/BrightnessContrastPass.js';
import { BokehPass } from '../postprocessing/BokehPass.js';
import { BufferGeometry } from '../core/BufferGeometry.js';
import { Cache } from '../loaders/Cache.js';
import { Camera } from '../cameras/Camera.js';
import { Clock } from '../core/Clock.js';
import { Compat } from './Compat.js';
import { CubeCopy } from '../converters/CubeCopy.js';
import { CubeReflectionProbe } from '../lights/CubeReflectionProbe.js';
import { EffectComposer } from '../postprocessing/EffectComposer.js';
import { EventDispatcher } from '../core/EventDispatcher.js';
import { Detector } from '../core/Detector.js';
import { DirectionalLightShadow } from '../lights/DirectionalLightShadow.js';
import { FirstPersonControls } from '../controls/FirstPersonControls.js';
import { FlyingControls } from '../controls/FlyingControls.js';
import { FXAAPass } from '../postprocessing/FXAAPass.js';
import { GLTFLoader } from '../loaders/GLTFLoader.js';
import { GrayscalePass } from '../postprocessing/GrayscalePass.js';
import { GTAOPass } from '../postprocessing/GTAOPass.js';
import { Keys } from '../controls/Keys.js';
import { LightProbeGenerator } from '../lights/LightProbeGenerator.js';
import { Line } from '../objects/Line.js';
import { MaterialUtils } from '../materials/MaterialUtils.js';
import { Mesh } from '../objects/Mesh.js';
import * as MathUtils from '../math/MathUtils.js';
import { OrbitControls } from '../controls/OrbitControls.js';
import { OutlinePass } from '../postprocessing/OutlinePass.js';
import { Pass, FullScreenQuad } from '../postprocessing/Pass.js';
import { PMREMGenerator } from './PMREMGenerator.js';
import { RenderPass } from '../postprocessing/RenderPass.js';
import { RenderUtils } from '../renderers/RenderUtils.js';
import { RepeatedKeyListener } from '../controls/RepeatedKeyListener.js';
import { Scene } from '../scenes/Scene.js';
import { SceneBackground } from '../scenes/SceneBackground.js';
import { SceneUtils } from './SceneUtils.js';
import { ShaderLib } from '../renderers/shaders/ShaderLib.js';
import { ShaderPass } from '../postprocessing/ShaderPass.js';
import { Sprite } from '../objects/Sprite.js';
import { SpriteMaterial } from '../materials/SpriteMaterial.js';
import { Stats } from './Stats.js';
import { SSRPass } from '../postprocessing/SSRPass.js';
import { SSAARenderPass } from '../postprocessing/SSAARenderPass.js';
import { TextureLoader } from '../loaders/TextureLoader.js';
import { ToneMapPass } from '../postprocessing/ToneMapPass.js';
import { Vector2 } from '../math/Vector2.js';
import { Vector3 } from '../math/Vector3.js';
import { WebGLRenderer } from '../renderers/WebGLRenderer.js';
import { WebGLRenderTarget } from '../renderers/WebGLRenderTarget.js';
import { WebGLMultisampleRenderTarget } from '../renderers/WebGLMultisampleRenderTarget.js';

import { VRReticleImage } from '../media.js';
import { isDef } from '../utils.js';

import {
    acceleratedRaycast,
    computeBoundsTree,
    disposeBoundsTree
} from './core/mesh_bvh/index.js';

import {
    LinearMipmapLinearFilter,
    ESMShadowMap,
    PCFSoftShadowMap,
    ViewportFitNone,
    ViewportFitVertical,
    ViewportFitHorizontal,
    ViewportFitAuto,
    ViewportFitOverscan,
    ViewportFitFill,
    RGBAFormat,
    RGBEEncoding,
    LinearEncoding,
    sRGBEncoding,
    HalfFloatType,
    UnsignedByteType,
    IBLEnvironmentPMREM,
    IBLEnvironmentProbeCubemap,
    IBLEnvironmentProbe,
    ReflectionProbeTypeInfinite,
    NoBlending
} from '../constants.js';

const TONE_MAP_PARS = [
    'toneMapping',
    'toneMappingMidTones',
    'toneMappingPhysicalScale',
    // logarithmic max
    'toneMappingBrightness',
    'toneMappingContrast',
    'toneMappingChromaticAdaptation',
    'toneMappingWhiteColor',
    'toneMappingColorDifferentiation',
    'toneMappingExteriorDaylight',
    // physical max
    'toneMappingWhiteBalance',
    'toneMappingHighlights',
    'toneMappingShadows',
    'toneMappingSaturation',
    'toneMappingAperture',
    'toneMappingShutter',
    'toneMappingISO',
    'toneMappingVignetting'
];

const GLTF_PROGRESS_WEIGHT = 0.6;
const COMPILE_PROGRESS_WEIGHT = 0.4;
const ONLOAD_100_TIMEOUT = 16; // ms

const TEX_IMAGE_UNITS_WARN_LIMIT = 8; // maximum for iOS devices

const USE_BVH_RAYCAST = true;

const REG_PPP_PROFILING = true;
const REG_FFF_COUNTER = true;
const REG_HHH_TRIGGER = true;

const HIDPI_LAYER = 7;

function recalcVerticalFov(oldFov, oldAspect, newAspect) {
    return MathUtils.RAD2DEG * 2 * Math.atan(
            Math.tan(MathUtils.DEG2RAD * oldFov / 2) * oldAspect / newAspect);
}


class App extends EventDispatcher {

    constructor(container, ctxSettings, preloader) {

        super();

        this.container = container instanceof HTMLElement ? container
                : document.getElementById(container);

        if (!Detector.checkWebGL()) {
            Detector.showWebGLErrorMessage(this.container);
            return;
        }

        this.scene = null;
        this.camera = null;

        this.clock = new Clock();
        this.mixer = null;

        this.renderCallbacks = [];
        this.compileCallbacks = [];

        this.elapsed = 0;
        // for proper render calls calculation
        this.frame = 0;

        this.preloader = preloader;

        this.worldCubemapRes = 1024;

        // updated from the loaded gltf file
        this._pmremMaxTileSize = 256;

        // Generation time is O(n^2) for light probes (see LightProbeGenerator.js),
        // hence keep the resolution smaller to make the loading process smoother
        // (less freezing). Also, light probe cubemaps larger than a certain size
        // don't add much difference for indirect diffuse lighting, which they are
        // used for.
        this._lightProbeCubemapRes = 64;

        this.xrSession = null;
        this.xrControllers = [];

        // renderer

        ctxSettings = ctxSettings || {};
        if (ctxSettings.alpha === undefined) ctxSettings.alpha = false;
        if (ctxSettings.depth === undefined) ctxSettings.depth = true;
        if (ctxSettings.stencil === undefined) ctxSettings.stencil = true;
        if (ctxSettings.antialias === undefined) ctxSettings.antialias = true;
        if (ctxSettings.premultipliedAlpha === undefined) ctxSettings.premultipliedAlpha = true;
        if (ctxSettings.preserveDrawingBuffer === undefined) ctxSettings.preserveDrawingBuffer = false;

        this.renderer = new WebGLRenderer(ctxSettings);

        Compat.prepareRenderer(this.renderer);

        this.clearBkgOnLoad = false;

        this.frameRateDivider = 1;
        this.enableRender = true;
        this.disableRenderTrigger = 0;
        this.ssaaOnPause = false;

        this.renderer.setSize(this.container.offsetWidth, this.container.offsetHeight);
        this.renderer.outputEncoding = sRGBEncoding;

        this.container.appendChild(this.renderer.domElement);

        this.container.classList.add('v3d-container');
        this.renderer.domElement.classList.add('v3d-canvas');

        // HACK: workaround for Chrome bug with automatic translator removing canvas element
        this.container.setAttribute('translate', 'no');

        this.loader = new GLTFLoader();

        if (USE_BVH_RAYCAST) {
            BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
            BufferGeometry.prototype.disposeBoundsTree = disposeBoundsTree;
            Mesh.prototype.raycast = acceleratedRaycast;
        }

        this.actions = [];

        /**
         * Deprecated, Backward compatibility for old visual_logic.js scripts, that
         * have the assignMaterial puzzle, the old version of which has used
         * the materials property and the updateMaterials() method.
         */
        this.materials = { push: function() {} };
        this.updateMaterials = function() {},

        // updated from the loaded gltf file
        this._envIBLMode = IBLEnvironmentPMREM;
        this._envLightProbe = null;

        this._resizeCb = null;
        this._loadingTime = 0;

        this._backgroundSave = null;
        this._postprocessingSave = null;

        this.stats = null;

        AppUtils.drawWatermark(this);
        AppUtils.addToAppList(this);

        if (Detector.checkIOS() && ('polyfill' in window && 'WebXRPolyfill' in window && polyfill instanceof WebXRPolyfill))
            AppUtils.requestDeviceMotionPermissions();

        /**
         * Deprecated. Backward compatibility for old visual logic scripts using
         * App.prototype.worldMaterial.
         */
        this.worldMaterial = null;
    }

    _updateRendererFromGLTF(gltf) {

        const scope = this;

        const halfFloat = Detector.checkHalfFloatTex(this.renderer, true);

        if (gltf.renderer.shadowMap) {
            this.renderer.shadowMap.enabled = gltf.renderer.shadowMap.enabled;
            this.renderer.shadowMap.type = gltf.renderer.shadowMap.type;

            if (!halfFloat && this.renderer.shadowMap.type === ESMShadowMap) {
                this.renderer.shadowMap.type = PCFSoftShadowMap;

                gltf.scene.traverse(function(obj) {
                    if (obj.isLight && obj.castShadow && obj.shadow) {
                        // scale bias to make shadows look decent when forcing
                        // them to be PCF instead of ESM
                        obj.shadow.bias /= 100;

                        if (obj.shadow.isDirectionalLightShadowCSM) {
                            // scale radius and initialize non-csm directional shadow
                            obj.shadow.radius *= 100 / obj.shadow.mapSize.x / 2;
                            obj.shadow = new DirectionalLightShadow().copy(obj.shadow);
                            obj.shadow.camera.updateProjectionMatrix();
                        }
                    }


                });
            }

        } else {
            // COMPAT: < 2.3
            this.renderer.shadowMap.enabled = true;
            this.renderer.shadowMap.type = PCFSoftShadowMap;
        }

        // NOTE: does not work good for IBL
        if (gltf.renderer.physicallyCorrectLights)
            this.renderer.physicallyCorrectLights = true;

        this.aaMethod = gltf.renderer.aaMethod || 'AUTO';
        this.useHDR = Boolean(gltf.renderer.useHDR && halfFloat);
        this.renderer.unitsScaleFactor = gltf.renderer.unitsScaleFactor;

        if (gltf.renderer.toneMapping) {
            for (let i = 0; i < TONE_MAP_PARS.length; i++) {
                const par = TONE_MAP_PARS[i];
                if (isDef(gltf.renderer[par]))
                    this.renderer[par] = gltf.renderer[par];
            }
        }

        if (gltf.renderer.pmremMaxTileSize !== undefined) {
            this._pmremMaxTileSize = gltf.renderer.pmremMaxTileSize;
        }

        if (gltf.renderer.iblEnvironmentMode !== undefined) {
            this._envIBLMode = gltf.renderer.iblEnvironmentMode;
        }

        if (gltf.renderer.esmDistanceScale !== undefined) {
            this.renderer.shadowMap.esmDistanceScale = gltf.renderer.esmDistanceScale;
        }

        gltf.scene.traverse(function(obj) {
            if (obj.hidpiCompositing) {
                obj.traverse(obj2 => {
                    if (obj.isMesh)
                        obj2.layers.set(HIDPI_LAYER);
                });
                scope.useHiDPIRenderPass = true;
                scope.renderer.setPixelRatio(window.devicePixelRatio);
                // not setting composer.setPixelRatio() here
            }
        });

        // add lights to HiDPI layer
        if (scope.useHiDPIRenderPass) {
            gltf.scene.traverse(function(obj) {
                if (obj.isLight)
                    obj.layers.enable(HIDPI_LAYER);
            });
        }
    }

    _updateMeshesRaycastFromGLTF(gltf) {
        if (gltf.scene) {
            gltf.scene.traverse(function(obj) {
                const geom = obj.geometry;

                if (obj.isMesh) {
                    // enable optimized raycasting for non-morphed objects only
                    if (geom.computeBoundsTree
                        && Object.keys(geom.morphAttributes).length === 0
                        && !geom.attributes.position.isInterleavedBufferAttribute
                        && (!geom.index || !geom.index.isInterleavedBufferAttribute)) {
                        geom.computeBoundsTree({
                            verbose: false
                        });
                    }
                }
            });
        }
    }

    _prepareReflProbesFromGLTF(gltf) {
        if (gltf.scene) {
            gltf.scene.traverse(obj => {
                if (obj.isCubeReflectionProbe) {
                    this._prepareEnvMapProbe(obj);
                } else if (obj.isPlaneReflectionProbe) {
                    let samples = this._checkMSAA(this.renderer, 4);
                    if (samples > 0)
                        obj.makeMultisampleRenderTarget(samples);
                }
            });
        }
    }

    /**
     * This method prepares scene's CubeReflectionProbe objects.
     * - those objects don't affect the diffuse lighting component, only the
     * world envMap probe object can do that (Blender behavior), because of that
     * here we don't generate any light probe objects
     * - it needs App._pmremMaxTileSize and App._envIBLMode properties which
     * are set in the App._updateRendererFromGLTF() method.
     */
    _prepareEnvMapProbe(obj) {
        obj.setSize(this._pmremMaxTileSize);
        switch (this._envIBLMode) {
            case IBLEnvironmentPMREM:
                obj.onUpdate = cubeRT => this.generateRTargetPMREM(cubeRT);
                break;
            case IBLEnvironmentProbeCubemap:
                break;
            case IBLEnvironmentProbe:
                obj.onUpdate = () => null;
                break;
        }
    }

    /**
     * Set encoding for all probe objects on a scene. Usually
     * needed after the postprocessing setup is done.
     */
    _prepareReflProbesEncoding(scene, encoding) {
        scene.traverse(obj => {
            if (obj.isCubeReflectionProbe || obj.isPlaneReflectionProbe) {
                obj.setEncoding(encoding);
            }
        });
    }

    /**
     * This prepares the world envMap probe for the scene.
     * - it needs App._pmremMaxTileSize and App._envIBLMode properties which
     * are set in the App._updateRendererFromGLTF() method.
     */
    _prepareEnvMapProbeWorld() {
        const wMatScene = new Scene();
        wMatScene.worldMaterial = this.scene.worldMaterial;

        if (this.scene.worldEnvMapProbe === null) {
            this.scene.worldEnvMapProbe = new CubeReflectionProbe(
                    this._pmremMaxTileSize);
            this.scene.worldEnvMapProbe.influenceType = ReflectionProbeTypeInfinite;
            this.scene.worldEnvMapProbe.parallaxType = ReflectionProbeTypeInfinite;
        }
        const wProbe = this.scene.worldEnvMapProbe;

        switch (this._envIBLMode) {
            case IBLEnvironmentPMREM:
                wProbe.onUpdate = cubeRT => this.generateRTargetPMREM(cubeRT);
                break;

            case IBLEnvironmentProbeCubemap:
            case IBLEnvironmentProbe:
                wProbe.onUpdate = cubeRT => {

                    const probeRenderTarget = cubeRT.clone();
                    probeRenderTarget.setSize(this._lightProbeCubemapRes, this._lightProbeCubemapRes);
                    probeRenderTarget.texture.type = UnsignedByteType;
                    probeRenderTarget.texture.format = RGBAFormat;
                    probeRenderTarget.texture.encoding = RGBEEncoding;

                    const cc = new CubeCopy(cubeRT.texture);
                    cc.render(this.renderer, probeRenderTarget);
                    cc.dispose();

                    this._disposeEnvLightProbe();
                    this._envLightProbe = LightProbeGenerator.fromCubeRenderTarget(
                            this.renderer, probeRenderTarget);
                    this.scene.add(this._envLightProbe);
                    probeRenderTarget.dispose();

                    if (this._envIBLMode === IBLEnvironmentProbeCubemap) {
                        return cubeRT;
                    } else {
                        return null;
                    }
                }
                break;
        }

        wProbe.update(wMatScene, this.renderer);

        /**
         * IBL modes other than PMREM offer less quality and more performance.
         * Also they are already quite different from Blender's behavior,
         * therefore there's no reason to use the costly specular approximation.
         */
        this.renderer.compatSettings.useSpecEnvBlenderApprox
                = this._envIBLMode === IBLEnvironmentPMREM;
    }

    _updateMaterialsFromGLTF(gltf) {

        const scope = this;
        if (gltf.scene) {
            gltf.scene.traverse(function(obj) {
                const mat = obj.material;
                if (!mat)
                    return;

                if (scope.useHDR) {
                    mat.useHDR = true;
                    mat.useFloatTex = Detector.checkFloatTex(scope.renderer, true);
                    if (mat.isMeshNodeMaterial) {
                        // NOTE: doing it too much
                        mat.updateNodeGraph();
                    }
                }

            });
        }
    }

    _updateAnimationsFromGLTF(gltf, animRoot) {

        const scope = this;

        if (!scope.mixer && gltf.animations && gltf.animations.length) {
            scope.mixer = new AnimationMixer(scope.scene);
        }

        (gltf.animations || []).forEach(function(anim) {
            const animObj = animRoot.getObjectById(anim.nodeId);
            if (animObj) {

                let action;

                // NOTE: use localRoot for non-root nodes that can be
                // wrongly treated as a root according to the logic in
                // the PropertyBinding.findNode() method
                if (animObj.id != animRoot.id
                        && (animObj.name === "" || animObj.name === "root"
                        || animObj.name === "." || animObj.name === animRoot.name
                        || animObj.name === animRoot.uuid)) {
                    action = scope.mixer.clipAction(anim.clip, animObj);
                } else {
                    action = scope.mixer.clipAction(anim.clip, animRoot);
                }

                action.setLoop(anim.loop, anim.repetitions);
                action.startAt(anim.startAt + scope.mixer.time);
                action.clampWhenFinished = true;

                if (anim.auto) {
                    action.play();
                } else {
                    action.stop();
                    action.paused = true;
                }

                scope.actions.push(action);
            }
        });

    }

    _traverseSceneForTexUniforms(scene, cb) {
        scene.traverse(function(obj) {
            if (obj.material) {
                const objMats = Array.isArray(obj.material) ? obj.material : [obj.material];
                objMats.forEach(function(mat) {
                    if (mat.program !== undefined) {
                        cb(obj, mat, mat.program.getTexUniformCount());
                    }
                });
            }
        });
    }

    _checkMSAA(renderer, requestedSamples) {
        return Math.min(requestedSamples, renderer.capabilities.maxSamples);
    }

    _precompileSceneAsync(scene, camera, renderTarget, progressCb) {

        const scope = this;

        const ccs = scope.compileCallbacks;
        for (let i = 0; i < ccs.length; i++)
            ccs[i](scope);

        const currentRenderTarget = scope.renderer.getRenderTarget();
        scope.renderer.setRenderTarget(renderTarget);

        scope.renderer.compileAsync(scene, camera, function(percentage) {

            if (percentage >= 1) {
                scope.renderer.setRenderTarget(currentRenderTarget);
            }

            if (progressCb) progressCb(percentage * 100);

        });

    }

    /**
     * disable transparency or fallback to alpha blend mode in case of non-multisampled buffers
     */
    _handleAlphaToCoverage(aaSamples) {
        this.scene.traverse(function(obj) {
            const mat = obj.material;

            if (mat && mat.alphaToCoverage) {
                if (aaSamples > 0) {
                    mat.transparent = false;
                    mat.premultipliedAlpha = false;
                    mat.blending = NoBlending;
                } else {
                    mat.alphaToCoverage = false;
                }
            }
        });
    }

    assignClippingPlanes(scene) {
        const scope = this;

        let planeObjs = [];
        let planes = [];
        let renderOrders = [];
        let renderOrder = -1000;

        scene.traverse(function(planeObj) {
            if (planeObj.isClippingPlaneObject) {

                planeObjs.push(planeObj);
                planes.push(planeObj.plane);

                scene.traverse(function(objToClip) {
                    if (planeObj.needsClippingPlane(objToClip))
                        planeObj.assignToObject(objToClip, renderOrder++);
                });

                renderOrders.push(renderOrder++);
            }
        });

        for (let i = 0; i < planeObjs.length; i++) {
            const planeObj = planeObjs[i];
            if (planeObj.crossSection)
                planeObj.createCrossSectionPlane(planes, renderOrders[i]);
        }

        if (planeObjs.length) {
            scope.renderer.localClippingEnabled = true;

            if (scope.postprocessing)
                scope.postprocessing.composer.setStencil(true);
        }
    }

    updateConstraints(scene) {
        const scope = this;

        scene.traverse(function(obj) {
            for (let i = 0; i < obj.constraints.length; i++) {
                const cons = obj.constraints[i];

                if (cons.isCanvasBreakpointsConstraint) {
                    cons.appInstance = scope;
                }
            }
        });
    }

    load(url, loadOkCb, loadErrorCb, autoStart) {

        console.warn('v3d.App.load has been deprecated. Use v3d.App.loadScene instead.');

        const scope = this;

        scope.loadScene(url, function(loadedScene) {
            loadOkCb(loadedScene);
            if (autoStart) scope.run();
        }, null, loadErrorCb);

    }

    loadScene(url, loadCb, progressCb, errorCb) {

        const scope = this;

        if (!scope.renderer) {
            if (errorCb) errorCb('WebGL not found');
            return;
        }

        scope._loadingTime = performance.now();

        if (scope.preloader) scope.preloader.onUpdate(0);
        this.loader.load(url, function(gltf) {

            // setup scene/camera
            scope.scene = gltf.scene || new Scene();

            let sceneBox = null;

            if (gltf.cameras && gltf.cameras.length) {
                scope.camera = gltf.cameras[0];
            } else {
                sceneBox = SceneUtils.calcSceneBox(scope.scene);

                scope.camera = SceneUtils.createDefaultCamera(sceneBox,
                        scope.container.offsetWidth / scope.container.offsetHeight);
                scope.scene.add(scope.camera);
            }

            // not a Verge3D asset
            if (!scope.camera.controls) {
                // for optimization
                sceneBox = sceneBox || SceneUtils.calcSceneBox(scope.scene);

                SceneUtils.assignDefaultControls(scope.camera, SceneUtils.calcSceneBox(scope.scene));
                scope.camera.viewportFit.type = ViewportFitVertical;
            }

            scope._updateRendererFromGLTF(gltf);
            scope._prepareReflProbesFromGLTF(gltf);
            scope._updateMaterialsFromGLTF(gltf);
            scope._updateAnimationsFromGLTF(gltf, scope.scene);

            const wMat = gltf.world.material;
            if (wMat) {
                scope.scene.background = new SceneBackground();
                scope.scene.worldMaterial = wMat;
                scope.updateEnvironment(wMat);

                // Deprecated. Backward compatibility for old visual logic scripts.
                scope.worldMaterial = wMat;
            }

            scope.initPostprocessing();

            scope.assignClippingPlanes(scope.scene);
            scope.updateConstraints(scope.scene);

            if (scope.onResize) scope.onResize();

            // make matrices up to date for possible use in the load callback
            scope.scene.updateMatrixWorld();

            /**
             * Don't render the loaded scene immediately on the following frame
             * to preventflickering until everything is done for the loaded
             * scene. This is especially related to user actions in the loadCb
             * callback.
             */
            scope.scene.visible = false;
            scope.scene.disableChildRendering = true;

            const firstFrameRendered = function() {
                // handle possible unload() before firstFrameRendered
                if (scope.scene)
                    scope._traverseSceneForTexUniforms(scope.scene, function(obj, mat, count) {
                        if (count > TEX_IMAGE_UNITS_WARN_LIMIT) {
                            console.warn(`v3d.App: Material "${mat.name}" on object `
                                    + `"${obj.name}" exceeds iOS limit of `
                                    + `${TEX_IMAGE_UNITS_WARN_LIMIT} textures `
                                    + `(has ${count}).`);
                        }
                    });

                scope.removeEventListener('firstFrameRendered', firstFrameRendered);
            }

            const rt = scope.postprocessing ? scope.postprocessing.composer.renderTarget1 : null;
            scope._precompileSceneAsync(scope.scene, scope.camera, rt,
                function(percentage) {

                    const totalPercentage = (GLTF_PROGRESS_WEIGHT * 100 + COMPILE_PROGRESS_WEIGHT * percentage)
                            / (GLTF_PROGRESS_WEIGHT + COMPILE_PROGRESS_WEIGHT);
                    if (progressCb) progressCb(totalPercentage);
                    if (scope.preloader) scope.preloader.onUpdate(totalPercentage);

                    if (totalPercentage >= 100) {

                        if (USE_BVH_RAYCAST) {
                            scope._updateMeshesRaycastFromGLTF(gltf);
                        }

                        scope.addEventListener('firstFrameRendered', firstFrameRendered);

                        if (loadCb) {
                            setTimeout(function() {
                                /**
                                 * Restore the loaded scene's visibility. See
                                 * the comment above.
                                 */
                                scope.scene.visible = true;
                                scope.scene.disableChildRendering = false;

                                scope.updateReflectionProbes(scope.scene);

                                scope._loadingTime = performance.now() - scope._loadingTime;
                                scope.dispatchEvent({ type: 'loadSceneEnd' });
                                loadCb(scope.scene);
                            }, ONLOAD_100_TIMEOUT);
                        }
                    }

                }
            );

            if (scope.clearBkgOnLoad) scope.scene.background = null;

            if (REG_PPP_PROFILING) {
                scope._tripleP = new RepeatedKeyListener(window, Keys.P, function() {
                    AppUtils.printPerformanceInfo(scope, 1);
                }, 3, 1);
            }

            if (REG_FFF_COUNTER) {
                scope._tripleF = new RepeatedKeyListener(window, Keys.F, function() {
                    if (scope.stats)
                        scope.hideFPS();
                    else
                        scope.showFPS();
                }, 3, 1);
            }

            if (REG_HHH_TRIGGER) {
                scope._tripleH = new RepeatedKeyListener(window, Keys.H, function() {
                    if (scope.enableRender)
                        scope.disableRendering();
                    else
                        scope.enableRendering();
                }, 3, 1);
            }

        }, function(percentage) {

            const totalPercentage = GLTF_PROGRESS_WEIGHT * percentage
                    / (GLTF_PROGRESS_WEIGHT + COMPILE_PROGRESS_WEIGHT);
            if (progressCb) progressCb(totalPercentage);
            if (scope.preloader) scope.preloader.onUpdate(totalPercentage);

        }, function(error) {

            console.error(error);
            if (errorCb) errorCb(error);

        });

        // remove previous resize callback if exists
        window.removeEventListener('resize', this._resizeCb, false);
        this._resizeCb = function() { if (scope.onResize) scope.onResize(); }
        window.addEventListener('resize', this._resizeCb, false);
    }

    appendScene(url, loadCb, progressCb, errorCb, loadCameras, loadLights) {

        const scope = this;

        if (!scope.renderer) {
            if (errorCb) errorCb('WebGL not found');
            return;
        }

        if (loadCameras === undefined) loadCameras = true;
        if (loadLights === undefined) loadLights = true;

        if (scope.preloader) scope.preloader.onUpdate(0);
        this.loader.load(url, function(gltf) {

            const loadedScene = gltf.scene || new Scene();

            const objsToUnload = [];
            loadedScene.traverse(function(obj) {
                if (obj.isCamera && !loadCameras || obj.isLight && !loadLights) {
                    objsToUnload.push(obj);
                }
            });

            objsToUnload.forEach(function(obj) {
                scope.unload(obj);
            });

            if (scope.scene) {
                scope.scene.add(loadedScene);

                scope._prepareReflProbesFromGLTF(gltf);
                scope._updateMaterialsFromGLTF(gltf);
                scope._updateAnimationsFromGLTF(gltf, loadedScene);

                // make matrices up to date for possible use in the load callback
                scope.scene.updateMatrixWorld();
            }

            const rt = scope.postprocessing ? scope.postprocessing.composer.renderTarget1 : null;
            // use the whole scene because it can be affected by something from
            // the dynamically loaded scene, e.g. lights
            const compiledScene = scope.scene || loadedScene;

            scope.assignClippingPlanes(compiledScene);
            scope.updateConstraints(compiledScene);

            /**
             * Don't render the loaded scene immediately on the following frame
             * to preventflickering until everything is done for the loaded
             * scene. This is especially related to user actions in the loadCb
             * callback.
             */
            loadedScene.visible = false;
            loadedScene.disableChildRendering = true;

            scope._precompileSceneAsync(compiledScene, scope.camera || new Camera(),
                rt, function(percentage) {

                    const totalPercentage = (GLTF_PROGRESS_WEIGHT * 100 + COMPILE_PROGRESS_WEIGHT * percentage)
                            / (GLTF_PROGRESS_WEIGHT + COMPILE_PROGRESS_WEIGHT);
                    if (progressCb) progressCb(totalPercentage);
                    if (scope.preloader) scope.preloader.onUpdate(totalPercentage);

                    if (totalPercentage >= 100) {

                        if (USE_BVH_RAYCAST) {
                            scope._updateMeshesRaycastFromGLTF(gltf);
                        }

                        /**
                         * This is different from what happens in loadScene(),
                         * because the scene is already being rendered while
                         * appending is going on - no deferring.
                         */
                        scope._traverseSceneForTexUniforms(loadedScene, function(obj, mat, count) {
                            if (count > TEX_IMAGE_UNITS_WARN_LIMIT) {
                                console.warn(`v3d.App: Material "${mat.name}" on object `
                                        + `"${obj.name}" exceeds iOS limit of `
                                        + `${TEX_IMAGE_UNITS_WARN_LIMIT} textures `
                                        + `(has ${count}).`);
                            }
                        });

                        if (loadCb) {
                            setTimeout(function() {
                                /**
                                 * Restore the loaded scene's visibility. See
                                 * the comment above.
                                 */
                                loadedScene.visible = true;
                                loadedScene.disableChildRendering = false;

                                scope.updateReflectionProbes(scope.scene);

                                loadCb(loadedScene);
                            }, ONLOAD_100_TIMEOUT);
                        }

                    }

                }
            );

        }, function(percentage) {

            const totalPercentage = GLTF_PROGRESS_WEIGHT * percentage
                    / (GLTF_PROGRESS_WEIGHT + COMPILE_PROGRESS_WEIGHT);
            if (progressCb) progressCb(totalPercentage);
            if (scope.preloader) scope.preloader.onUpdate(totalPercentage);

        }, function(error) {

            console.error(error);
            if (errorCb) errorCb(error);

        });
    }

    unload(rootObj) {

        const scope = this;

        if (!rootObj) rootObj = scope.scene;

        function disposeObjResources(obj) {
            if (obj.isAnnotation) {
                obj.dispose();
            } else if (obj.isLight && obj.shadow && obj.shadow.isLightShadow) {
                obj.shadow.dispose();
            } else if (obj.isCamera && obj.controls && obj.controls.orbitTarget) {
                disposeObjResources(obj.controls.orbitTarget);
            } else if (obj.isScene) {
                // dispose Scene.overrideMaterial too?
                const wMat = obj.worldMaterial;
                if (wMat !== null) {
                    MaterialUtils.disposeTextures(wMat);
                    wMat.dispose();
                }
                if (obj.worldEnvMapProbe !== null) {
                    obj.worldEnvMapProbe.dispose();
                    obj.worldEnvMapProbe = null;
                }
            } else if (obj.isMesh) {
                obj.geometry.dispose();

                if (obj.geometry.disposeBoundsTree) {
                    obj.geometry.disposeBoundsTree();
                }

                const mat = obj.material;
                MaterialUtils.disposeTextures(mat);
                mat.dispose();
            }
        }

        if (rootObj === scope.scene) {
            // full scene cleanup

            if (scope.scene) {
                scope.scene.traverse(disposeObjResources);
                scope.disposeEnvironment();
            }
            scope.scene = null;

            if (scope.controls && scope.controls.dispose) {
                scope.controls.dispose();
            }
            scope.controls = null;
            scope.camera = null;

            if (scope.mixer) {
                scope.mixer.stopAllAction();
                scope.actions.forEach(function(action) {
                    scope.mixer.uncacheAction(action.getClip(), action.getRoot());
                });
            }
            scope.mixer = null;
            scope.actions = [];

            if (scope.postprocessing) {
                if (scope.postprocessing.composer) {
                    for (let name in scope.postprocessing) {
                        const ppEffect = scope.postprocessing[name];
                        if (ppEffect instanceof Pass || ppEffect instanceof EffectComposer) {
                            ppEffect.dispose();
                        }
                    }
                }
                scope.disablePostprocessing();
            }
            scope.postprocessing = null;
            FullScreenQuad.dispose();

            if (scope.renderer) scope.renderer.disposeInternalCaches();

            if (scope._tripleP) scope._tripleP.dispose();
            if (scope._tripleF) scope._tripleF.dispose();
            if (scope._tripleH) scope._tripleH.dispose();

        } else {

            if (scope.scene) {
                rootObj.traverse(disposeObjResources);
                if (rootObj.parent) rootObj.parent.remove(rootObj);
            }

            if (scope.mixer) {
                for (let i = scope.actions.length - 1; i >= 0; i--) {
                    const action = scope.actions[i];
                    if (!SceneUtils.checkActionIsUsed(scope.scene, action)) {
                        action.stop();
                        scope.mixer.uncacheAction(action.getClip(), action.getRoot());
                        scope.actions.splice(i, 1);
                    }
                }
            }

        }

    }

    dispose() {
        if (this.scene) this.unload();

        if (this.renderer) {
            this.renderer.forceContextLoss();
            this.renderer.dispose();
            if (this.renderer.domElement.parentElement === this.container) {
                this.container.removeChild(this.renderer.domElement);
            }
        }
        this.renderer = null;

        window.removeEventListener('resize', this._resizeCb, false);

        AppUtils.removeFromAppList(this);

        Cache.clear();

        this.dispatchEvent({ type: 'dispose' });
    }

    getWidth() {
        return this.container.offsetWidth;
    }

    getHeight() {
        return this.container.offsetHeight;
    }

    onResize() {

        // refresh disabled or partially rendered canvas
        if (!this.enableRender || this.ssaaOnPause) {
            this.enableRendering();
            this.disableRendering(1);
        }

        const width = this.getWidth();
        const height = this.getHeight();

        this.renderer.setSize(width, height);

        if (this.postprocessing) {
            this.postprocessing.composer.setSize(width, height);
        }

        if (this.scene) {

            this.scene.traverse(obj => {
                if (obj.isPlaneReflectionProbe)
                    obj.setSize(width, height);
            });

            const aspect = width / height;
            const cam = this.camera;

            if (cam.isPerspectiveCamera) {
                const oldAspectIsLess = cam.aspect < cam.viewportFit.initialAspect;
                const newAspectIsLess = aspect < cam.viewportFit.initialAspect;

                switch (cam.viewportFit.type) {
                case ViewportFitVertical:
                    cam.aspect = aspect;
                    break;
                case ViewportFitHorizontal:
                    cam.fov = recalcVerticalFov(cam.fov,
                            cam.aspect, aspect);
                    cam.aspect = aspect;
                    break;
                case ViewportFitAuto:
                    if (oldAspectIsLess && newAspectIsLess)
                        cam.fov = recalcVerticalFov(cam.fov, cam.aspect, aspect);
                    else if (oldAspectIsLess && !newAspectIsLess)
                        cam.fov = recalcVerticalFov(cam.fov, cam.aspect, cam.viewportFit.initialAspect);
                    else if (!oldAspectIsLess && newAspectIsLess)
                        cam.fov = recalcVerticalFov(cam.fov, cam.viewportFit.initialAspect, aspect);

                    cam.aspect = aspect;
                    break;
                case ViewportFitOverscan:

                    if (oldAspectIsLess && newAspectIsLess)
                        cam.fov = recalcVerticalFov(cam.fov, cam.aspect, aspect);
                    else if (oldAspectIsLess && !newAspectIsLess)
                        cam.fov = recalcVerticalFov(cam.fov, cam.viewportFit.initialAspect, aspect);
                    else if (!oldAspectIsLess && newAspectIsLess)
                        cam.fov = recalcVerticalFov(cam.fov, cam.aspect, aspect);

                    cam.aspect = aspect;
                    break;
                case ViewportFitFill:

                    if (!oldAspectIsLess && !newAspectIsLess)
                        cam.fov = recalcVerticalFov(cam.fov, cam.aspect, aspect);
                    else if (oldAspectIsLess && !newAspectIsLess)
                        cam.fov = recalcVerticalFov(cam.fov, cam.aspect, cam.viewportFit.initialAspect);
                    else if (!oldAspectIsLess && newAspectIsLess)
                        cam.fov = recalcVerticalFov(cam.fov, cam.aspect, cam.viewportFit.initialAspect);

                    cam.aspect = aspect;
                    break;
                case ViewportFitNone:
                default:
                    break;
                }

            } else if (cam.isOrthographicCamera) {

                let horizSize;
                let vertSize;

                switch (cam.viewportFit.type) {
                case ViewportFitVertical:
                    horizSize = cam.top * aspect;
                    cam.left = -horizSize;
                    cam.right = horizSize;
                    break;
                case ViewportFitHorizontal:
                    vertSize = cam.right / aspect;
                    cam.bottom = -vertSize;
                    cam.top = vertSize;
                    break;
                case ViewportFitAuto:
                    const oldAspectIsLess = (cam.right - cam.left) /
                            (cam.top - cam.bottom) < cam.viewportFit.initialAspect;
                    const newAspectIsLess = aspect < cam.viewportFit.initialAspect;

                    horizSize;

                    if (oldAspectIsLess && newAspectIsLess)
                        horizSize = cam.right;
                    else if (oldAspectIsLess && !newAspectIsLess)
                        horizSize = cam.right * aspect / cam.viewportFit.initialAspect;
                    else if (!oldAspectIsLess && newAspectIsLess)
                        horizSize = cam.top * cam.viewportFit.initialAspect;
                    else
                        horizSize = cam.top * aspect;

                    cam.left = -horizSize;
                    cam.right = horizSize;
                    cam.bottom = -horizSize / aspect;
                    cam.top = horizSize / aspect;

                    break;
                case ViewportFitFill:
                    vertSize = cam.right / aspect;
                    cam.bottom = -vertSize;
                    cam.top = vertSize;
                    break;
                case ViewportFitOverscan:
                    horizSize = cam.top * aspect;
                    cam.left = -horizSize;
                    cam.right = horizSize;
                    break;
                case ViewportFitNone:
                default:
                    break;
                }

            }

            cam.updateProjectionMatrix();

        }

    }

    run() {

        if (this.preloader) {
            this.preloader.onFinish();
            this.preloader = null;
        }
        this.animate();

    }

    animate() {
        const scope = this;

        const cb = function() {

            if (scope.stats)
                scope.stats.begin();

            const elapsed = scope.clock.getDelta();
            scope.elapsed = elapsed;

            if (scope.mixer)
                scope.mixer.update(elapsed);

            if (scope.controls && !scope.xrSession)
                scope.controls.update(elapsed);

            const rbs = scope.renderCallbacks;
            for (let i = 0; i < rbs.length; i++)
                rbs[i](elapsed, scope.clock.elapsedTime);

            if ((scope.frame % scope.frameRateDivider) == 0 && scope.enableRender) {
                scope.render();
                if (scope.frame === 0) {
                    scope.dispatchEvent({ type: 'firstFrameRendered' });
                }
            }

            scope.frame++;

            if (scope.disableRenderTrigger && --scope.disableRenderTrigger == 0)
                scope.enableRender = false;

            if (scope.stats)
                scope.stats.end();
        }

        scope.renderer.setAnimationLoop(cb);
    }

    enableRendering() {
        this.disableRenderTrigger = 0;
        this.enableRender = true;
        if (this.ssaaOnPause)
            this.enableSSAA(0, true);
    }

    disableRendering(after) {
        after = after || 0;

        if ((after || this.ssaaOnPause) && this.enableRender && this.disableRenderTrigger == 0) {
            this.disableRenderTrigger = this.ssaaOnPause ? 32 : after; // maximum 32
            if (this.ssaaOnPause)
                this.enableSSAA(4, true);
        } else if (after == 0) {
            this.enableRender = false;
        }
    }

    setFrameRateDivider(divider) {
        this.frameRateDivider = divider;
    }

    render() {
        this.dispatchEvent({ type: 'onBeforeRender' });

        const sceneCameraExist = (!!this.scene && !!this.camera);

        if (sceneCameraExist) {
            this.scene.traverse(obj => {
                if (obj.isPlaneReflectionProbe) {
                    obj.update(this.scene, this.camera, this.renderer);
                }
            });
        }

        if (this.postprocessing) {
            const composer = this.postprocessing.composer;
            composer.render(this.elapsed);
        } else if (sceneCameraExist) {
            this.renderer.render(this.scene, this.camera);
        }

        if (sceneCameraExist && this.useHiDPIRenderPass) {
            const prevCameraLayersMask = this.camera.layers.mask;
            const prevBackground = this.scene.background;
            this.scene.background = null;
            this.camera.layers.set(HIDPI_LAYER);

            this.renderer.autoClear = false;
            this.renderer.clearDepth();
            this.renderer.render(this.scene, this.camera);

            this.camera.layers.mask = prevCameraLayersMask;
            this.scene.background = prevBackground;
        }

        this.dispatchEvent({ type: 'onAfterRender' });
    }

    enableControls(element) {
        const camera = this.camera;

        if (!camera.controls)
            return;

        switch (camera.controls.type) {
        case 'ORBIT':
            this.controls = new OrbitControls(camera, element || this.renderer.domElement);
            this.controls.targetObj = camera.controls.orbitTarget;
            this.controls.minDistance = camera.controls.orbitMinDistance;
            this.controls.maxDistance = camera.controls.orbitMaxDistance;
            this.controls.minZoom = camera.controls.orbitMinZoom;
            this.controls.maxZoom = camera.controls.orbitMaxZoom;
            this.controls.minPolarAngle = camera.controls.orbitMinPolarAngle;
            this.controls.maxPolarAngle = camera.controls.orbitMaxPolarAngle;
            this.controls.minAzimuthAngle = camera.controls.orbitMinAzimuthAngle;
            this.controls.maxAzimuthAngle = camera.controls.orbitMaxAzimuthAngle;
            break;
        case 'FLYING':
            this.controls = new FlyingControls(camera, this.renderer.domElement);

            this.controls.panSpeedTouch *= camera.controls.moveSpeed;
            this.controls.zoomSpeedKey *= camera.controls.moveSpeed;
            break;
        case 'FIRST_PERSON':
            this.controls = new FirstPersonControls(camera, this.renderer.domElement);
            this.controls.collisionMeshes = [];

            const scope = this;

            this.scene.traverse(function(obj) {
                const mat = obj.material;
                if (mat && camera.controls.collisionMaterial && mat.name == camera.controls.collisionMaterial.name) {
                    scope.controls.collisionMeshes.push(obj);
                }
            });

            scope.controls.gazeLevel = camera.controls.gazeLevel;
            scope.controls.storyHeight = camera.controls.storyHeight;

            this.controls.zoomSpeedKey *= camera.controls.moveSpeed;

            break;
        default:
            this.controls = null;
            break;
        }

        if (this.controls) {
            this.controls.enablePan = camera.controls.enablePan;

            this.controls.rotateSpeed *= camera.controls.rotateSpeed;
            this.controls.rotateSpeedTouch *= camera.controls.rotateSpeed;

            this.controls.panSpeed *= camera.controls.moveSpeed;
            this.controls.panSpeedKey *= camera.controls.moveSpeed;

            this.controls.zoomSpeed *= camera.controls.moveSpeed;
            this.controls.zoomSpeedTouch *= camera.controls.moveSpeed;

            // apply all settings immediately, to ensure correct rendering on
            // the current frame
            this.controls.update();
        }
    }

    setCamera(camera) {
        this.camera = camera;

        if (this.postprocessing) {
            const passes = this.postprocessing.composer.passes;
            for (let i = 0; i < passes.length; i++)
                passes[i].setCamera(camera);

            // one of them won't be in passes when using ssaaOnPause
            if (this.postprocessing.renderPass)
                this.postprocessing.renderPass.setCamera(camera);
            if (this.postprocessing.ssaaRenderPass)
                this.postprocessing.ssaaRenderPass.setCamera(camera);
        }

        if (this.controls)
            this.controls.dispose();

        this.enableControls();
        this.onResize();
    }

    getCamera(tryXrIfAvail=false) {
        if (tryXrIfAvail && this.camera && this.renderer && this.renderer.xr.enabled && this.renderer.xr.isPresenting)
            return this.renderer.xr.getCamera(this.camera);
        else
            return this.camera;
    }

    cleanup() {

        console.warn('v3d.App.cleanup has been deprecated. Use v3d.App.unload or v3d.App.dispose instead.');

        if (this.container) {
            while (this.container.firstChild) {
                this.container.removeChild(this.container.firstChild);
            }
        }

        if (!this.loader || !this.mixer)
            return;

        this.mixer.stopAllAction();
    }

    initPostprocessing() {
        // also enable ToneMap/FXAA for HDR pipeline
        if (this.scene.postprocessing && this.scene.postprocessing.length || this.useHDR || this.useHiDPIRenderPass || this.aaMethod != 'AUTO')
            this.enablePostprocessing(this.scene.postprocessing || []);
        else
            this._handleAlphaToCoverage(this.renderer.getContextAttributes().antialias ? 4 : 0);
    }

    enablePostprocessing(effects) {

        const renderTargetParams = {
            format: RGBAFormat,
            stencilBuffer: false
        }

        if (this.useHDR) {
            renderTargetParams.type = HalfFloatType;
            renderTargetParams.encoding = LinearEncoding;
        } else {
            renderTargetParams.type = UnsignedByteType;
            renderTargetParams.encoding = sRGBEncoding;
        }

        /**
         * NOTE: need to use the same encoding for probe objects as for RenderPass
         * in order to avoid recompiling of all objects' shaders back and forth
         * when updating a probe.
         */
        this._prepareReflProbesEncoding(this.scene, renderTargetParams.encoding);

        let composer;

        if (!this.postprocessing) {
            this.postprocessing = {};
            const renderPass = new RenderPass(this.scene, this.camera);
            this.postprocessing.renderPass = renderPass;

            let aaSamples = 0;
            switch (this.aaMethod) {
            case 'AUTO':
            case 'MSAA4':
                aaSamples = this._checkMSAA(this.renderer, 4);
                break;
            case 'MSAA8':
                aaSamples = this._checkMSAA(this.renderer, 8);
                break;
            case 'MSAA16':
                aaSamples = this._checkMSAA(this.renderer, 16);
                break;
            }

            if (Detector.checkSwiftShader(this.renderer)) {
                aaSamples = 0;
                console.warn('v3d.App: disabling buggy multisampling on SwiftShader renderer');
            }

            let renderTarget;

            if (aaSamples) {
                renderTarget = new WebGLMultisampleRenderTarget(this.getWidth(), this.getHeight(),
                        renderTargetParams);
                renderTarget.samples = aaSamples;
            } else {
                renderTarget = new WebGLRenderTarget(this.getWidth(), this.getHeight(),
                        renderTargetParams);
            }

            renderTarget.texture.name = 'EffectComposer.rt1';

            composer = new EffectComposer(this.renderer, renderTarget);
            composer.addPass(renderPass);

            this.postprocessing.composer = composer;

            const alpha = this.renderer.getContextAttributes().alpha;
            const useFXAA = (aaSamples == 0 && this.aaMethod != 'NONE');

            if (this.useHDR) {
                const toneMapPass = new ToneMapPass();
                if (useFXAA && !alpha)
                    toneMapPass.material.defines['ALPHA_AS_LUMA'] = 1;
                composer.addPass(toneMapPass);
                this.postprocessing.toneMapPass = toneMapPass;
            }

            if (useFXAA) {
                const fxaaPass = new FXAAPass(this.scene, this.camera);
                if (this.useHDR && !alpha)
                    fxaaPass.material.defines['FXAA_GREEN_AS_LUMA'] = 0;
                composer.addPass(fxaaPass);
                this.postprocessing.fxaaPass = fxaaPass;
            }

            this._handleAlphaToCoverage(aaSamples);

        } else {
            composer = this.postprocessing.composer;
        }

        // cleanup unnecessary copy pass
        if (effects.length && this.postprocessing.copyPass) {
            composer.passes.splice(composer.passes.indexOf(this.postprocessing.copyPass), 1);
            this.postprocessing.copyPass = null;
        }

        for (let i = 0; i < effects.length; i++) {
            const effect = effects[i];

            let insertIndex = composer.passes.length - 1;

            // no FXAA
            if (!(composer.passes[insertIndex] instanceof FXAAPass))
                insertIndex++

            // before Tonemap pass
            if (this.useHDR)
                insertIndex--;

            switch (effect.type) {
            case 'ao':
                if (!Detector.checkDepthTex(this.renderer)) {
                    console.warn('v3d.App: disabling GTAO since your hardware does not support depth textures');
                    break;
                }

                if (!this.postprocessing.aoPass) {
                    this.postprocessing.aoPass = new GTAOPass(this.scene,
                            this.camera, this.getWidth(), this.getHeight(),
                            this.renderer.capabilities.isWebGL2);
                    composer.insertPass(this.postprocessing.aoPass, insertIndex);
                }

                const aoPass = this.postprocessing.aoPass;
                aoPass.distance = effect.distance;
                aoPass.factor = effect.factor;
                aoPass.precision = effect.precision;
                aoPass.bounceApprox = effect.bounceApprox;
                break;

            case 'bloom':
                const bloomStrength = effect.strength;
                const bloomRadius = effect.radius;
                const bloomThreshold = effect.threshold;

                let bloomPass;

                if (!this.postprocessing.bloomPass) {
                    bloomPass = new BloomPass(new Vector2(this.getWidth(), this.getHeight()),
                            bloomStrength, bloomRadius, bloomThreshold, renderTargetParams);

                    composer.insertPass(bloomPass, insertIndex);
                    this.postprocessing.bloomPass = bloomPass;
                } else {
                    bloomPass = this.postprocessing.bloomPass;

                    bloomPass.strength = bloomStrength;
                    bloomPass.radius = bloomRadius;
                    bloomPass.threshold = bloomThreshold;
                }

                break;

            case 'brightnessContrast':
                let brightnessContrastPass;

                if (!this.postprocessing.brightnessContrastPass) {
                    brightnessContrastPass = new BrightnessContrastPass();

                    composer.insertPass(brightnessContrastPass, insertIndex);
                    this.postprocessing.brightnessContrastPass = brightnessContrastPass;
                } else
                    brightnessContrastPass = this.postprocessing.brightnessContrastPass;

                brightnessContrastPass.brightness = effect.brightness;
                brightnessContrastPass.contrast = effect.contrast;

                break;

            case 'dof':
                let bokehPass;

                if (!this.postprocessing.bokehPass) {
                    bokehPass = new BokehPass(this.scene, this.camera, {
                        width: this.getWidth(),
                        height: this.getHeight()
                    });
                    composer.insertPass(bokehPass, insertIndex);
                    this.postprocessing.bokehPass = bokehPass;
                } else {
                    bokehPass = this.postprocessing.bokehPass;
                }

                bokehPass.focus = effect.focus;
                bokehPass.aperture = effect.aperture;
                bokehPass.maxblur = effect.maxblur;
                bokehPass.depthLeakThreshold = effect.depthLeakThreshold;

                break;

            case 'grayscale':
                if (!this.postprocessing.grayscalePass) {
                    const grayscalePass = new GrayscalePass();

                    composer.insertPass(grayscalePass, insertIndex);
                    this.postprocessing.grayscalePass = grayscalePass;
                }

                break;

            case 'outline':
                let outlinePass;

                if (!this.postprocessing.outlinePass) {
                    outlinePass = new OutlinePass(
                            new Vector2(this.getWidth(), this.getHeight()),
                            this.scene, this.camera);
                    composer.insertPass(outlinePass, insertIndex);
                    this.postprocessing.outlinePass = outlinePass;
                } else
                    outlinePass = this.postprocessing.outlinePass;

                outlinePass.edgeStrength = effect.edgeStrength;
                outlinePass.edgeGlow = effect.edgeGlow;
                outlinePass.edgeThickness = effect.edgeThickness;
                outlinePass.pulsePeriod = effect.pulsePeriod;
                outlinePass.visibleEdgeColor.fromArray(effect.visibleEdgeColor)
                outlinePass.hiddenEdgeColor.fromArray(effect.hiddenEdgeColor);

                if (effect.renderHiddenEdge === undefined) {
                    // COMPAT: < 2.17
                    /**
                     * if black color is used, then it's probably to not render
                     * the hidden edge part at all, otherwise, it should be
                     * rendered by default
                     */
                    const blackColorUsed = effect.hiddenEdgeColor[0] === 0.0
                            && effect.hiddenEdgeColor[1] === 0.0
                            && effect.hiddenEdgeColor[2] === 0.0;
                    outlinePass.hiddenEdgeColor.setW(Number(!blackColorUsed));
                } else {
                    outlinePass.hiddenEdgeColor.setW(Number(effect.renderHiddenEdge));
                }
                break;

            case 'ssr':
                if (!Detector.checkHalfFloatTex(this.renderer, false)) {
                    console.warn('v3d.App: disabling SSR since your hardware does not support half float textures');
                    break;
                }

                let useRefract = false;

                if (isDef(effect.useRefract))
                    useRefract = effect.useRefract;

                let ssrPass;

                if (!(useRefract ? this.postprocessing.ssrPassRefract : this.postprocessing.ssrPassReflect)) {
                    ssrPass = new SSRPass(this.scene, this.camera);
                    composer.insertPassAfter(ssrPass, [
                            this.postprocessing.renderPass,
                            this.postprocessing.ssrPassRefract,
                            this.postprocessing.ssrPassReflect]);
                    if (useRefract)
                        this.postprocessing.ssrPassRefract = ssrPass;
                    else
                        this.postprocessing.ssrPassReflect = ssrPass;
                } else {
                    ssrPass = useRefract ? this.postprocessing.ssrPassRefract :
                            this.postprocessing.ssrPassReflect;
                }

                ssrPass.useRefract = useRefract;

                if (isDef(effect.objects))
                    ssrPass.objects = effect.objects;
                if (isDef(effect.intensity))
                    ssrPass.intensity = effect.intensity;
                if (isDef(effect.steps))
                    ssrPass.steps = effect.steps;
                if (isDef(effect.stride))
                    ssrPass.stride = effect.stride;
                if (isDef(effect.binarySearchSteps))
                    ssrPass.binarySearchSteps = effect.binarySearchSteps;
                if (isDef(effect.renderTargetScale))
                    ssrPass.renderTargetScale = effect.renderTargetScale;
                if (isDef(effect.thickness))
                    ssrPass.thickness = effect.thickness;
                if (isDef(effect.maxDistance))
                    ssrPass.maxDistance = effect.maxDistance;
                if (isDef(effect.jitter))
                    ssrPass.jitter = effect.jitter;
                if (isDef(effect.renderAfter))
                    ssrPass.renderAfter = effect.renderAfter;
                if (isDef(effect.simpleRefraction))
                    ssrPass.simpleRefraction = effect.simpleRefraction;

                // NOTE: temporary
                if (this.onResize) this.onResize();

                break;
            default:
                console.error(`v3d.App: wrong postprocessing effect "${effect.type}"`);
                break;
            }
        }

        if (composer.passes.length == 1) {
            const copyPass = new ShaderPass(ShaderLib.copy);
            composer.passes.push(copyPass);
            this.postprocessing.copyPass = copyPass;
        }

    }

    disablePostprocessing(keepOutline, keepAO) {

        if (!this.postprocessing)
            return;

        const passesToRemove = [
            'bloomPass',
            'brightnessContrastPass',
            'bokehPass',
            'grayscalePass',
            'ssrPassReflect',
            'ssrPassRefract'
        ];

        if (!keepOutline) {
            passesToRemove.push('outlinePass');
        }

        if (!keepAO) {
            passesToRemove.push('aoPass');
        }

        const composer = this.postprocessing.composer;

        for (let i = 0; i < passesToRemove.length; i++) {
            const passName = passesToRemove[i];

            if (this.postprocessing[passName]) {
                composer.passes.splice(composer.passes.indexOf(
                    this.postprocessing[passName]), 1);

                this.postprocessing[passName].dispose();
                this.postprocessing[passName] = null;
            }
        }

        // cleanup everything if only Render (and FXAA) remain
        if (!this.useHDR && this.aaMethod == 'AUTO' && composer.passes.length <= 2) {

            this.postprocessing.renderPass.dispose();

            if (this.postprocessing.fxaaPass)
                this.postprocessing.fxaaPass.dispose();

            this.postprocessing.composer.dispose();

            this.postprocessing = null;

        }

    }

    enableSSAA(sampleLevel, iterative) {

        if (!this.postprocessing)
            this.enablePostprocessing([]);

        // SSAA works bad with SSR since we have no depth info  and objects are rendered after main pass
        if (sampleLevel > 0 && (this.postprocessing.ssrPassRefract || this.postprocessing.ssrPassReflect))
            return;

        // prevents annotation jitter
        const scope = this;
        this.scene.traverse(function(obj) {
            if (obj.isAnnotationControl) {
                obj.update(scope.camera);
                obj.doUpdate = !Boolean(sampleLevel);
            }
        });

        const composer = this.postprocessing.composer;

        if (sampleLevel > 0 && composer.passes[0] instanceof RenderPass) {

            let ssaaRenderPass;

            if (!this.postprocessing.ssaaRenderPass) {
                ssaaRenderPass = new SSAARenderPass(this.scene, this.camera);
                this.postprocessing.ssaaRenderPass = ssaaRenderPass;

                if (iterative) {
                    ssaaRenderPass.addEventListener('iteration', function(event) {
                        if (event.frame == (sampleLevel * sampleLevel - 1)) {
                            composer.enableAllPasses();
                            composer.renderToScreen = true;
                            // force it, since it maybe the last iteration rendered directly to screen
                            // as such no assignment in composer.render() will happen
                            composer.passes[composer.passes.length-1].renderToScreen = true;
                            scope.disableRenderTrigger = 1;
                        }
                    });
                }

            } else {
                ssaaRenderPass = this.postprocessing.ssaaRenderPass;
            }

            // 16x
            ssaaRenderPass.sampleLevel = sampleLevel || 4;

            composer.passes[0] = ssaaRenderPass;

            // disable FXAA if any
            if (this.postprocessing.fxaaPass)
                composer.passes.splice(composer.passes.length-1, 1);

            if (iterative) {
                ssaaRenderPass.iterative = true;
                ssaaRenderPass.iterativeFrame = 0;

                composer.disableAllPasses();
                composer.renderToScreen = false;
                ssaaRenderPass.enabled = true;
            }

        } else if (sampleLevel > 0) {

            composer.passes[0].sampleLevel = sampleLevel || 4;

            if (iterative) {
                ssaaRenderPass.iterative = true;
                ssaaRenderPass.iterativeFrame = 0;

                composer.disableAllPasses();
                composer.renderToScreen = false;
                ssaaRenderPass.enabled = true;
            }

        } else if (sampleLevel == 0 && composer.passes[0] instanceof SSAARenderPass) {
            composer.passes[0] = this.postprocessing.renderPass;

            if (this.postprocessing.fxaaPass)
                composer.passes.push(this.postprocessing.fxaaPass);

            composer.enableAllPasses();
            composer.renderToScreen = true;
        }
    }

    updateEnvironment(wMat) {
        const xrEnabledSave = this.renderer.xr.enabled;
        this.renderer.xr.enabled = false;

        this.disposeEnvironment();

        /**
         * NOTE: unconditionally.
         *
         * Setting useHDR to true also makes the world material not use
         * per-material tone mapping in favor of the tone mapping postprocessing
         * pass. But when rendering the world environment cubemap no
         * postprocessing is applied anyway, so the cubemap is always in the
         * original colors. Which makes sense, because in the end tone mapping
         * will still affect the cubemap data when rendering the background and
         * reflective objects. They either use tone mapping as a part of their
         * shaders or just undergo a postprocessing pass.
         */
        wMat.useHDR = true;

        if (this.scene.background !== null && this.scene.background.isSceneBackground) {
            this.scene.background.data = RenderUtils.renderWorldNodeMatToCubemap(
                    this.renderer, wMat, this.worldCubemapRes, {
                encoding: sRGBEncoding,
                format: RGBAFormat,
                generateMipmaps: true,
                minFilter: LinearMipmapLinearFilter,
                type: HalfFloatType,
            });
            this.scene.background.useHDR = this.useHDR;
        }

        if (this._envIBLMode === IBLEnvironmentPMREM) {
            /**
             * NOTE: compile PMREMGenerator shaders earlier to reduce loading
             * time. All internal resources are disposed after any of
             * PMREMGenerator instance is disposed, so no need to worry about
             * this one.
             */
            new PMREMGenerator(this.renderer, this._pmremMaxTileSize, true)
                    .compileCubemapShader();
        }

        this._prepareEnvMapProbeWorld();
        this.renderer.xr.enabled = xrEnabledSave;
    }

    disposeEnvironment() {
        this._disposeEnvLightProbe();
        let bkg = this.scene.background;
        if (bkg) {
            if (bkg.isSceneBackground) bkg = bkg.data;
            if (bkg && (bkg.isTexture || bkg.isWebGLRenderTarget)) {
                bkg.dispose();
            }
        }
    }

    _disposeEnvLightProbe() {
        if (this._envLightProbe !== null) {
            this.scene.remove(this._envLightProbe);
            this._envLightProbe = null;
        }
    }

    updateReflectionProbes(object3d) {
        object3d.traverse(obj => {
            if (obj.isCubeReflectionProbe) {
                obj.update(this.scene, this.renderer);
            }
        });
    }

    /**
     * deprecated, not needed anymore
     */
    updateObjectMaterialEnv(obj) {
        console.warn('v3d.App.updateObjectMaterialEnv has been deprecated: not needed anymore');
    }

    generateRTargetPMREM(cubeRT) {
        // process WebGLCubeRenderTarget only
        if (!cubeRT.isWebGLCubeRenderTarget) {
            return null;
        }

        // can use blurLinEncodingOptimization=true, because the output and the
        // internal blur render targets are supposed to be linear as per options
        // passed to .fromCubeRenderTarget()
        const pmremGenerator = new PMREMGenerator(this.renderer,
                this._pmremMaxTileSize, true);

        // don't flip WebGLCubeRenderTarget textures along the X coordinate
        pmremGenerator.flipCubemapX = false;

        const pmremRTarget = pmremGenerator.fromCubeRenderTarget(cubeRT, {
            encoding: LinearEncoding
        });
        pmremGenerator.dispose();

        return pmremRTarget;
    }

    initWebXR(mode, referenceSpaceType, successCb, failureCb, exitCb, options) {

        successCb = successCb || function() {};
        failureCb = failureCb || function() {};
        exitCb = exitCb || function() {};
        options = options || {};

        const scope = this;

        function onSessionEnded(event) {

            scope.xrSession.removeEventListener('end', onSessionEnded);
            scope.renderer.xr.setSession(null);

            // allow unregister controllers first
            exitCb();

            for (let i = 0; i < scope.xrControllers.length; i++) {
                const controller = scope.xrControllers[i];
                scope.scene.remove(controller);
            }

            scope.xrControllers = [];

            scope.xrSession = null;

            // return background back
            if (scope._backgroundSave) {
                scope.scene.background = scope._backgroundSave;
                scope._backgroundSave = null;
            }

            // return postprocessing back
            scope.postprocessing = scope._postprocessingSave;
            scope._postprocessingSave = null;

            scope.onResize();
        }

        function onControllerConnected(event) {

            const inputSource = event.data;
            const controller = event.target;

            if (inputSource.targetRayMode == 'tracked-pointer') {
                const geometry = new BufferGeometry().setFromPoints([new Vector3(0, 0, 0),
                        new Vector3(0, 0, -1)]);

                const line = new Line(geometry);
                line.name = controller.name + '_RAY';
                line.scale.z = 5;

                controller.add(line);

            } else if (inputSource.targetRayMode == 'gaze') {

                const spriteMap = new TextureLoader().load(VRReticleImage);
                const spriteMaterial = new SpriteMaterial({ map: spriteMap, sizeAttenuation: false });

                const sprite = new Sprite(spriteMaterial);
                sprite.name = controller.name + '_RETICLE';
                sprite.scale.multiplyScalar(0.1);
                sprite.position.z = -5;

                controller.add(sprite);

            }

            controller.userData.v3d.inputSource = inputSource;
        }

        function onControllerDisconnected(event) {

            const controller = event.target;

            for (let i = controller.children.length-1; i >= 0; i--) {
                const child = controller.children[i];

                // only ray/reticle, do not remove user-added objects
                if (child.name.indexOf(controller.name) > -1) {
                    child.geometry.dispose();
                    child.material.dispose();

                    controller.remove(child);
                }
            }

        }

        const opts = { optionalFeatures: [referenceSpaceType] };

        if (mode == 'immersive-ar') {
            opts.optionalFeatures.push('hit-test');

            if (options.domOverlay) {
                opts.optionalFeatures.push('dom-overlay');
                opts.domOverlay = { root: scope.container };
            }
        }

        navigator.xr.requestSession(mode, opts).then(function(session) {

            scope._postprocessingSave = scope.postprocessing;
            scope.postprocessing = null;

            scope.renderer.xr.setReferenceSpaceType(referenceSpaceType);

            scope.xrSession = session;
            session.addEventListener('end', onSessionEnded);

            const numControllers = (mode == 'immersive-vr') ? 2 : 1;

            for (let i = 0; i < numControllers; i++) {
                const controller = scope.renderer.xr.getController(i);
                scope.scene.add(controller);
                scope.xrControllers.push(controller);

                controller.addEventListener('connected', onControllerConnected);
                controller.addEventListener('disconnected', onControllerDisconnected);
            }

            if (mode == 'immersive-vr') {
                // NOTE: reduce pixel ratio for VR sessions on HIDPI screens
                if (window.devicePixelRatio >= 2)
                    scope.renderer.xr.setFramebufferScaleFactor(0.5);
            } else {
                scope._backgroundSave = scope.scene.background;
                scope.scene.background = null;
            }

            scope.renderer.xr.enabled = true;
            scope.renderer.xr.setSession(session);

            // HACK: sync canvas size with container, which is used as the overlay element
            if (options.domOverlay) {
                scope.renderer.xr.addEventListener('sessionstart', function() {
                    setTimeout(function() {
                        scope.renderer.domElement.style.width = scope.getWidth() + 'px'
                        scope.renderer.domElement.style.height = scope.getHeight() + 'px';
                    }, 300);
                });
            }

            successCb();

        }).catch(failureCb);

    }

    endWebXR() {
        if (this.xrSession)
            this.xrSession.end();
    }

    printPerformanceInfo(delta) {

        AppUtils.printPerformanceInfo(this, delta);

    }

    showFPS() {
        if (this.container) {
            this.hideFPS();
            const stats = new Stats();
            stats.showPanel(0);
            this.container.appendChild(stats.dom);
            this.stats = stats;
        }
    }

    hideFPS() {
        if (this.container && this.stats) {
            this.container.removeChild(this.stats.dom);
            this.stats = null;
        }
    }

}

export { App };
