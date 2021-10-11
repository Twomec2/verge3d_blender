'use strict';

/* __V3D_TEMPLATE__ - template-based file; delete this line to prevent this file from being updated */

window.addEventListener('load', function() {

var CONTAINER_ID = 'v3d-container';

(function() {

    var params = v3d.AppUtils.getPageParams();

    var PUZZLES_DIR = '/puzzles/';
    var logicURL = params.logic ? params.logic : '__LOGIC__visual_logic.js'.replace('__LOGIC__', '');
    var sceneURL = params.load ? params.load : '__URL__global_illumination.gltf'.replace('__URL__', '');
    if (!sceneURL) {
        console.log('No scene URL specified');
        return;
    }

    // some puzzles can benefit from cache
    v3d.Cache.enabled = true;

    if (v3d.AppUtils.isXML(logicURL)) {
        var logicURLJS = logicURL.match(/(.*)\.xml$/)[1] + '.js';
        new v3d.PuzzlesLoader().loadEditorWithLogic(PUZZLES_DIR, logicURLJS,
            function() {
                var initOptions = v3d.PL ? v3d.PL.execInitPuzzles({
                        container: CONTAINER_ID }).initOptions
                        : { useFullscreen: true };
                var appInstance = loadScene(sceneURL, initOptions);
                v3d.PE.viewportUseAppInstance(appInstance);
            }
        );
    } else if (v3d.AppUtils.isJS(logicURL)) {
        new v3d.PuzzlesLoader().loadLogic(logicURL, function() {
            var initOptions = v3d.PL ? v3d.PL.execInitPuzzles({
                    container: CONTAINER_ID }).initOptions
                    : { useFullscreen: true };
            loadScene(sceneURL, initOptions);
        });
    } else {
        loadScene(sceneURL, { useFullscreen: true });
    }
})();

function loadScene(sceneURL, initOptions) {

    initOptions = initOptions || {};

    var ctxSettings = {};
    if (initOptions.useBkgTransp) ctxSettings.alpha = true;
    if (initOptions.preserveDrawBuf) ctxSettings.preserveDrawingBuffer = true;

    var preloader = initOptions.useCustomPreloader
            ? createCustomPreloader(initOptions.preloaderProgressCb,
            initOptions.preloaderEndCb)
            : new v3d.SimplePreloader({ container: CONTAINER_ID });

    if (v3d.PE) {
        puzzlesEditorPreparePreloader(preloader);
    }

    var app = new v3d.App(CONTAINER_ID, ctxSettings, preloader);
    if (initOptions.useBkgTransp) {
        app.clearBkgOnLoad = true;
        app.renderer.setClearColor(0x000000, 0);
    }

    // namespace for communicating with code generated by Puzzles
    app.ExternalInterface = {};
    prepareExternalInterface(app);

    if (initOptions.preloaderStartCb) initOptions.preloaderStartCb();
    if (initOptions.useFullscreen) {
        initFullScreen();
    } else {
        var fsButton = document.getElementById('fullscreen_button');
        if (fsButton) fsButton.style.display = 'none';
    }

    sceneURL = initOptions.useCompAssets ? sceneURL + '.xz' : sceneURL;
    app.loadScene(sceneURL, function() {
        app.enableControls();
        app.run();

        if (v3d.PE) v3d.PE.updateAppInstance(app);
        if (v3d.PL) v3d.PL.init(app, initOptions);

        runCode(app);
    }, null, function() {
        console.log('Can\'t load the scene ' + sceneURL);
    });

    return app;
}

function createCustomPreloader(updateCb, finishCb) {
    function CustomPreloader() {
        v3d.Preloader.call(this);
    }

    CustomPreloader.prototype = Object.assign(Object.create(v3d.Preloader.prototype), {
        onUpdate: function(percentage) {
            v3d.Preloader.prototype.onUpdate.call(this, percentage);
            if (updateCb) updateCb(percentage);
        },
        onFinish: function() {
            v3d.Preloader.prototype.onFinish.call(this);
            if (finishCb) finishCb();
        }
    });

    return new CustomPreloader();
}

/**
 * Modify the app's preloader to track the loading process in the Puzzles Editor.
 */
function puzzlesEditorPreparePreloader(preloader) {
    // backward compatibility for loading new projects within the old Puzzles Editor
    if (v3d.PE.loadingUpdateCb !== undefined && v3d.PE.loadingFinishCb !== undefined) {
        var _onUpdate = preloader.onUpdate.bind(preloader);
        preloader.onUpdate = function(percentage) {
            _onUpdate(percentage);
            v3d.PE.loadingUpdateCb(percentage);
        }

        var _onFinish = preloader.onFinish.bind(preloader);
        preloader.onFinish = function() {
            _onFinish();
            v3d.PE.loadingFinishCb();
        }
    }
}

function initFullScreen() {

    var fsButton = document.getElementById('fullscreen_button');
    if (!fsButton) return;

    var container = document.getElementById(CONTAINER_ID);

    if (document.fullscreenEnabled ||
            document.webkitFullscreenEnabled ||
            document.mozFullScreenEnabled ||
            document.msFullscreenEnabled)
        fsButton.style.display = 'inline';

    fsButton.addEventListener('click', function(event) {
        event.stopPropagation();
        if (document.fullscreenElement ||
                document.webkitFullscreenElement ||
                document.mozFullScreenElement ||
                document.msFullscreenElement) {
            exitFullscreen();
        } else
            requestFullscreen(container);
    });

    function changeFullscreen() {
        if (document.fullscreenElement ||
                document.webkitFullscreenElement ||
                document.mozFullScreenElement ||
                document.msFullscreenElement) {
            fsButton.classList.remove('fullscreen-open');
            fsButton.classList.add('fullscreen-close');
        } else {
            fsButton.classList.remove('fullscreen-close');
            fsButton.classList.add('fullscreen-open');
        }
    }

    document.addEventListener('webkitfullscreenchange', changeFullscreen);
    document.addEventListener('mozfullscreenchange', changeFullscreen);
    document.addEventListener('msfullscreenchange', changeFullscreen);
    document.addEventListener('fullscreenchange', changeFullscreen);

    function requestFullscreen(elem) {
        if (elem.requestFullscreen)
            elem.requestFullscreen();
        else if (elem.mozRequestFullScreen)
            elem.mozRequestFullScreen();
        else if (elem.webkitRequestFullscreen)
            elem.webkitRequestFullscreen();
        else if (elem.msRequestFullscreen)
            elem.msRequestFullscreen();
    }

    function exitFullscreen() {
        if (document.exitFullscreen)
            document.exitFullscreen();
        else if (document.mozCancelFullScreen)
            document.mozCancelFullScreen();
        else if (document.webkitExitFullscreen)
            document.webkitExitFullscreen();
        else if (document.msExitFullscreen)
            document.msExitFullscreen();
    }
}

function prepareExternalInterface(app) {
    // register functions in the app.ExternalInterface to call them from Puzzles, e.g:
    // app.ExternalInterface.myJSFunction = function() {
    //     console.log('Hello, World!');
    // }

}

function runCode(app) {
    // add your code here, e.g. console.log('Hello, World!');

}

});
