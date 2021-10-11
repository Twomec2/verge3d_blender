/**
 * Generated by Verge3D Puzzles v.3.8.1
 * Sun Oct 03 2021 10:33:28 GMT+0300 (Moscow Standard Time)
 * Prefer not editing this file as your changes may get overridden once Puzzles are saved.
 * Check out https://www.soft8soft.com/docs/manual/en/introduction/Using-JavaScript.html
 * for the information on how to add your own JavaScript to Verge3D apps.
 */

'use strict';

(function() {

// global variables/constants used by puzzles' functions

var LIST_NONE = '<none>';

var _pGlob = {};

_pGlob.objCache = {};
_pGlob.fadeAnnotations = true;
_pGlob.pickedObject = '';
_pGlob.hoveredObject = '';
_pGlob.mediaElements = {};
_pGlob.loadedFile = '';
_pGlob.states = [];
_pGlob.percentage = 0;
_pGlob.openedFile = '';
_pGlob.xrSessionAcquired = false;
_pGlob.xrSessionCallbacks = [];
_pGlob.screenCoords = new v3d.Vector2();
_pGlob.intervalTimers = {};

_pGlob.AXIS_X = new v3d.Vector3(1, 0, 0);
_pGlob.AXIS_Y = new v3d.Vector3(0, 1, 0);
_pGlob.AXIS_Z = new v3d.Vector3(0, 0, 1);
_pGlob.MIN_DRAG_SCALE = 10e-4;
_pGlob.SET_OBJ_ROT_EPS = 1e-8;

_pGlob.vec2Tmp = new v3d.Vector2();
_pGlob.vec2Tmp2 = new v3d.Vector2();
_pGlob.vec3Tmp = new v3d.Vector3();
_pGlob.vec3Tmp2 = new v3d.Vector3();
_pGlob.vec3Tmp3 = new v3d.Vector3();
_pGlob.vec3Tmp4 = new v3d.Vector3();
_pGlob.eulerTmp = new v3d.Euler();
_pGlob.eulerTmp2 = new v3d.Euler();
_pGlob.quatTmp = new v3d.Quaternion();
_pGlob.quatTmp2 = new v3d.Quaternion();
_pGlob.colorTmp = new v3d.Color();
_pGlob.mat4Tmp = new v3d.Matrix4();
_pGlob.planeTmp = new v3d.Plane();
_pGlob.raycasterTmp = new v3d.Raycaster();

var PL = v3d.PL = v3d.PL || {};

// a more readable alias for PL (stands for "Puzzle Logic")
v3d.puzzles = PL;

PL.procedures = PL.procedures || {};


_pGlob.wooProductInfo = {};


PL.execInitPuzzles = function(options) {
    // always null, should not be available in "init" puzzles
    var appInstance = null;
    // app is more conventional than appInstance (used in exec script and app templates)
    var app = null;

    var _initGlob = {};
    _initGlob.percentage = 0;
    _initGlob.output = {
        initOptions: {
            fadeAnnotations: true,
            useBkgTransp: false,
            preserveDrawBuf: false,
            useCompAssets: false,
            useFullscreen: true,
            useCustomPreloader: false,
            preloaderStartCb: function() {},
            preloaderProgressCb: function() {},
            preloaderEndCb: function() {},
        }
    }

    // provide the container's id to puzzles that need access to the container
    _initGlob.container = options !== undefined && 'container' in options
            ? options.container : "";

    

    var PROC = {
    
};

// initSettings puzzle
_initGlob.output.initOptions.fadeAnnotations = true;
_initGlob.output.initOptions.useBkgTransp = false;
_initGlob.output.initOptions.preserveDrawBuf = true;
_initGlob.output.initOptions.useCompAssets = false;
_initGlob.output.initOptions.useFullscreen = true;

    return _initGlob.output;
}

PL.init = function(appInstance, initOptions) {

// app is more conventional than appInstance (used in exec script and app templates)
var app = appInstance;

initOptions = initOptions || {};

if ('fadeAnnotations' in initOptions) {
    _pGlob.fadeAnnotations = initOptions.fadeAnnotations;
}

this.procedures["price_recount"] = price_recount;

var PROC = {
    "price_recount": price_recount,
};

var parts_cost, final_cost, checkout_list;



// utility function envoked by almost all V3D-specific puzzles
// filter off some non-mesh types
function notIgnoredObj(obj) {
    return obj.type !== 'AmbientLight' &&
           obj.name !== '' &&
           !(obj.isMesh && obj.isMaterialGeneratedMesh) &&
           !obj.isAuxClippingMesh;
}


// utility function envoked by almost all V3D-specific puzzles
// find first occurence of the object by its name
function getObjectByName(objName) {
    var objFound;
    var runTime = _pGlob !== undefined;
    objFound = runTime ? _pGlob.objCache[objName] : null;

    if (objFound && objFound.name === objName)
        return objFound;

    appInstance.scene.traverse(function(obj) {
        if (!objFound && notIgnoredObj(obj) && (obj.name == objName)) {
            objFound = obj;
            if (runTime) {
                _pGlob.objCache[objName] = objFound;
            }
        }
    });
    return objFound;
}


// utility function envoked by almost all V3D-specific puzzles
// retrieve all objects on the scene
function getAllObjectNames() {
    var objNameList = [];
    appInstance.scene.traverse(function(obj) {
        if (notIgnoredObj(obj))
            objNameList.push(obj.name)
    });
    return objNameList;
}


// utility function envoked by almost all V3D-specific puzzles
// retrieve all objects which belong to the group
function getObjectNamesByGroupName(targetGroupName) {
    var objNameList = [];
    appInstance.scene.traverse(function(obj){
        if (notIgnoredObj(obj)) {
            var groupNames = obj.groupNames;
            if (!groupNames)
                return;
            for (var i = 0; i < groupNames.length; i++) {
                var groupName = groupNames[i];
                if (groupName == targetGroupName) {
                    objNameList.push(obj.name);
                }
            }
        }
    });
    return objNameList;
}


// utility function envoked by almost all V3D-specific puzzles
// process object input, which can be either single obj or array of objects, or a group
function retrieveObjectNames(objNames) {
    var acc = [];
    retrieveObjectNamesAcc(objNames, acc);
    return acc.filter(function(name) {
        return name;
    });
}

function retrieveObjectNamesAcc(currObjNames, acc) {
    if (typeof currObjNames == "string") {
        acc.push(currObjNames);
    } else if (Array.isArray(currObjNames) && currObjNames[0] == "GROUP") {
        var newObj = getObjectNamesByGroupName(currObjNames[1]);
        for (var i = 0; i < newObj.length; i++)
            acc.push(newObj[i]);
    } else if (Array.isArray(currObjNames) && currObjNames[0] == "ALL_OBJECTS") {
        var newObj = getAllObjectNames();
        for (var i = 0; i < newObj.length; i++)
            acc.push(newObj[i]);
    } else if (Array.isArray(currObjNames)) {
        for (var i = 0; i < currObjNames.length; i++)
            retrieveObjectNamesAcc(currObjNames[i], acc);
    }
}




// refraction puzzle
function refraction(matName, distance, renderAfterSelector) {

    var matNames = Array.isArray(matName) ? matName : [matName];
    var mats = [];

    matNames.forEach(function(name) {
        mats = mats.concat(v3d.SceneUtils.getMaterialsByName(appInstance, name));
    });

    var objects = [];

    for (var i = 0; i < mats.length; i++) {
        var mat = mats[i];

        appInstance.scene.traverse(function(obj) {
            if (obj.material && obj.material == mat)
                objects.push(obj);
        });
    }

    // no need
    if (!objects.length)
        return;

    var renderAfter = [];

    var renderAfterNames = retrieveObjectNames(renderAfterSelector);

    for (var i = 0; i < renderAfterNames.length; i++) {
        var obj = getObjectByName(renderAfterNames[i]);
        if (obj)
            renderAfter.push(obj);
    }

    appInstance.enablePostprocessing([{
        type: 'ssr',
        useRefract: true,
        simpleRefraction: true,
        objects: objects,
        maxDistance: distance,
        renderAfter: renderAfter
    }]);
}



// bloom puzzle
function bloom(threshold, strength, radius) {
    appInstance.enablePostprocessing([{
        type: 'bloom',
        threshold: threshold,
        strength: strength,
        radius: radius
    }]);
}



// utility functions envoked by the HTML puzzles
function getElements(ids, isParent) {
    var elems = [];
    if (Array.isArray(ids) && ids[0] != 'CONTAINER' && ids[0] != 'WINDOW' &&
        ids[0] != 'DOCUMENT' && ids[0] != 'BODY' && ids[0] != 'QUERYSELECTOR') {
        for (var i = 0; i < ids.length; i++)
            elems.push(getElement(ids[i], isParent));
    } else {
        elems.push(getElement(ids, isParent));
    }
    return elems;
}

function getElement(id, isParent) {
    var elem;
    if (Array.isArray(id) && id[0] == 'CONTAINER') {
        if (appInstance !== null) {
            elem = appInstance.container;
        } else if (typeof _initGlob !== 'undefined') {
            // if we are on the initialization stage, we still can have access
            // to the container element
            var id = _initGlob.container;
            if (isParent) {
                elem = parent.document.getElementById(id);
            } else {
                elem = document.getElementById(id);
            }
        }
    } else if (Array.isArray(id) && id[0] == 'WINDOW') {
        if (isParent)
            elem = parent;
        else
            elem = window;
    } else if (Array.isArray(id) && id[0] == 'DOCUMENT') {
        if (isParent)
            elem = parent.document;
        else
            elem = document;
    } else if (Array.isArray(id) && id[0] == 'BODY') {
        if (isParent)
            elem = parent.document.body;
        else
            elem = document.body;
    } else if (Array.isArray(id) && id[0] == 'QUERYSELECTOR') {
        if (isParent)
            elem = parent.document.querySelector(id);
        else
            elem = document.querySelector(id);
    } else {
        if (isParent)
            elem = parent.document.getElementById(id);
        else
            elem = document.getElementById(id);
    }
    return elem;
}



// setHTMLElemStyle puzzle
function setHTMLElemStyle(prop, value, ids, isParent) {
    var elems = getElements(ids, isParent);
    for (var i = 0; i < elems.length; i++) {
        var elem = elems[i];
        if (!elem || !elem.style)
            continue;
        elem.style[prop] = value;
    }
}



// updateTextObject puzzle
function updateTextObj(objSelector, text) {
    var objNames = retrieveObjectNames(objSelector);

    for (var i = 0; i < objNames.length; i++) {
        var objName = objNames[i];
        if (!objName) continue;
        var obj = getObjectByName(objName);
        if (!obj || !obj.geometry || !obj.geometry.cloneWithText)
            continue;
        obj.geometry = obj.geometry.cloneWithText(String(text));
    }
}


// Describe this function...
function price_recount() {
  final_cost = parts_cost[0] + parts_cost[1];
  updateTextObj('final_cost', String(final_cost) + '$');
}


// show and hide puzzles
function changeVis(objSelector, bool) {
    var objNames = retrieveObjectNames(objSelector);

    for (var i = 0; i < objNames.length; i++) {
        var objName = objNames[i]
        if (!objName)
            continue;
        var obj = getObjectByName(objName);
        if (!obj)
            continue;
        obj.visible = bool;
    }
}



// utility function used by the whenClicked, whenHovered and whenDraggedOver puzzles
function initObjectPicking(callback, eventType, mouseDownUseTouchStart, mouseButtons) {

    var elem = appInstance.renderer.domElement;
    elem.addEventListener(eventType, pickListener);
    if (v3d.PL.editorEventListeners)
        v3d.PL.editorEventListeners.push([elem, eventType, pickListener]);

    if (eventType == 'mousedown') {

        var touchEventName = mouseDownUseTouchStart ? 'touchstart' : 'touchend';
        elem.addEventListener(touchEventName, pickListener);
        if (v3d.PL.editorEventListeners)
            v3d.PL.editorEventListeners.push([elem, touchEventName, pickListener]);

    } else if (eventType == 'dblclick') {

        var prevTapTime = 0;

        function doubleTapCallback(event) {

            var now = new Date().getTime();
            var timesince = now - prevTapTime;

            if (timesince < 600 && timesince > 0) {

                pickListener(event);
                prevTapTime = 0;
                return;

            }

            prevTapTime = new Date().getTime();
        }

        var touchEventName = mouseDownUseTouchStart ? 'touchstart' : 'touchend';
        elem.addEventListener(touchEventName, doubleTapCallback);
        if (v3d.PL.editorEventListeners)
            v3d.PL.editorEventListeners.push([elem, touchEventName, doubleTapCallback]);
    }

    var raycaster = new v3d.Raycaster();

    function pickListener(event) {

        // to handle unload in loadScene puzzle
        if (!appInstance.getCamera())
            return;

        event.preventDefault();

        var xNorm = 0, yNorm = 0;
        if (event instanceof MouseEvent) {
            if (mouseButtons && mouseButtons.indexOf(event.button) == -1)
                return;
            xNorm = event.offsetX / elem.clientWidth;
            yNorm = event.offsetY / elem.clientHeight;
        } else if (event instanceof TouchEvent) {
            var rect = elem.getBoundingClientRect();
            xNorm = (event.changedTouches[0].clientX - rect.left) / rect.width;
            yNorm = (event.changedTouches[0].clientY - rect.top) / rect.height;
        }

        _pGlob.screenCoords.x = xNorm * 2 - 1;
        _pGlob.screenCoords.y = -yNorm * 2 + 1;
        raycaster.setFromCamera(_pGlob.screenCoords, appInstance.getCamera(true));
        var objList = [];
        appInstance.scene.traverse(function(obj){objList.push(obj);});
        var intersects = raycaster.intersectObjects(objList);
        callback(intersects, event);
    }
}

function objectsIncludeObj(objNames, testedObjName) {
    if (!testedObjName) return false;

    for (var i = 0; i < objNames.length; i++) {
        if (testedObjName == objNames[i]) {
            return true;
        } else {
            // also check children which are auto-generated for multi-material objects
            var obj = getObjectByName(objNames[i]);
            if (obj && obj.type == "Group") {
                for (var j = 0; j < obj.children.length; j++) {
                    if (testedObjName == obj.children[j].name) {
                        return true;
                    }
                }
            }
        }
    }
    return false;
}

// utility function used by the whenClicked, whenHovered, whenDraggedOver, and raycast puzzles
function getPickedObjectName(obj) {
    // auto-generated from a multi-material object, use parent name instead
    if (obj.isMesh && obj.isMaterialGeneratedMesh && obj.parent) {
        return obj.parent.name;
    } else {
        return obj.name;
    }
}



// whenClicked puzzle
function registerOnClick(objSelector, xRay, doubleClick, mouseButtons, cbDo, cbIfMissedDo) {

    // for AR/VR
    _pGlob.objClickInfo = _pGlob.objClickInfo || [];

    _pGlob.objClickInfo.push({
        objSelector: objSelector,
        callbacks: [cbDo, cbIfMissedDo]
    });

    initObjectPicking(function(intersects, event) {

        var isPicked = false;

        var maxIntersects = xRay ? intersects.length : Math.min(1, intersects.length);

        for (var i = 0; i < maxIntersects; i++) {
            var obj = intersects[i].object;
            var objName = getPickedObjectName(obj);
            var objNames = retrieveObjectNames(objSelector);

            if (objectsIncludeObj(objNames, objName)) {
                // save the object for the pickedObject block
                _pGlob.pickedObject = objName;
                isPicked = true;
                cbDo(event);
            }
        }

        if (!isPicked) {
            _pGlob.pickedObject = '';
            cbIfMissedDo(event);
        }

    }, doubleClick ? 'dblclick' : 'mousedown', false, mouseButtons);
}



function placeOrder() {
    return (function(url, title, content, price, makeScreenshot) {
        // placeOrder puzzle
        function doPost(url, params) {
            const form = document.createElement('form');
            form.setAttribute('method', 'post');
            form.setAttribute('action', url);
            form.setAttribute('target', 'v3d_view');

            for (const key in params) {
                const hiddenField = document.createElement('input');
                hiddenField.setAttribute('type', 'hidden');
                hiddenField.setAttribute('name', key);
                hiddenField.setAttribute('value', params[key]);
                form.appendChild(hiddenField);
            }

            document.body.appendChild(form);
            window.open('', 'v3d_view');
            form.submit();
        }

        const orderParams = {
            'v3d_title': title,
            'v3d_content': content,
            'v3d_price': price
        }

        if (makeScreenshot)
            orderParams['v3d_screenshot'] = appInstance.renderer.domElement.toDataURL("image/png");

        doPost(url, orderParams);
    }).apply(null, arguments);
}



// whenHovered puzzle
initObjectPicking(function(intersects, event) {

    var prevHovered = _pGlob.hoveredObject;
    var currHovered = '';

    // the event might happen before hover registration
    _pGlob.objHoverInfo = _pGlob.objHoverInfo || [];

    // search for closest hovered object

    var lastIntersectIndex = Infinity;
    _pGlob.objHoverInfo.forEach(function(el) {
        var maxIntersects = el.xRay ? intersects.length : Math.min(1, intersects.length);

        for (var i = 0; i < maxIntersects; i++) {
            var obj = intersects[i].object;
            var objName = getPickedObjectName(obj);

            if (objectsIncludeObj(retrieveObjectNames(el.objSelector), objName) && i <= lastIntersectIndex) {
                currHovered = objName;
                lastIntersectIndex = i;
            }
        }
    });

    if (prevHovered == currHovered) return;

    // first - all "out" callbacks, then - all "over"
    _pGlob.objHoverInfo.forEach(function(el) {
        if (objectsIncludeObj(retrieveObjectNames(el.objSelector), prevHovered)) {
            // ensure the correct value of the hoveredObject block
            _pGlob.hoveredObject = prevHovered;
            el.callbacks[1](event);
        }
    });

    _pGlob.objHoverInfo.forEach(function(el) {
        if (objectsIncludeObj(retrieveObjectNames(el.objSelector), currHovered)) {
            // ensure the correct value of the hoveredObject block
            _pGlob.hoveredObject = currHovered;
            el.callbacks[0](event);
        }
    });

    _pGlob.hoveredObject = currHovered;
}, 'mousemove', false);



// whenHovered puzzle
function registerOnHover(objSelector, xRay, cbOver, cbOut) {

    _pGlob.objHoverInfo = _pGlob.objHoverInfo || [];

    _pGlob.objHoverInfo.push({
        objSelector: objSelector,
        callbacks: [cbOver, cbOut],
        xRay: xRay
    });
}



/**
 * Obtain a unique name from the given one. Names are tested with the given
 * callback function that should return a boolean "unique" flag. If the given
 * "name" is not considered unique, then "name2" is tested for uniqueness, then
 * "name3" and so on...
 */
function acquireUniqueName(name, isUniqueCb) {
    var uniqueName = name;

    if (isUniqueCb !== undefined) {
        while (!isUniqueCb(uniqueName)) {
            var r = uniqueName.match(/^(.*?)(\d+)$/);
            if (!r) {
                uniqueName += "2";
            } else {
                uniqueName = r[1] + (parseInt(r[2], 10) + 1);
            }
        }
    }

    return uniqueName;
}



/**
 * Check if the given material name is already used by materials on the scene.
 */
function matNameUsed(name) {
    return v3d.SceneUtils.getMaterialByName(appInstance, name) !== null;
}



// assignMaterial puzzle
function assignMat(objSelector, matName) {
    var objNames = retrieveObjectNames(objSelector);
    if (!matName)
        return;
    var mat = v3d.SceneUtils.getMaterialByName(appInstance, matName);
    if (!mat)
        return;
    for (var i = 0; i < objNames.length; i++) {
        var objName = objNames[i];
        if (!objName)
            continue;
        var obj = getObjectByName(objName);
        if (obj) {
            var firstSubmesh = obj.resolveMultiMaterial()[0];

            var influences = firstSubmesh.morphTargetInfluences;
            var hasMorphing = influences !== undefined && influences.length > 0;

            if (hasMorphing) {
                var newMat = mat.clone();
                newMat.name = acquireUniqueName(mat.name, function(name) {
                    return !matNameUsed(name);
                });

                if (hasMorphing) {
                    newMat.morphTargets = true;
                    if (firstSubmesh.geometry.morphAttributes.normal !== undefined) {
                        newMat.morphNormals = true;
                    }
                }

                firstSubmesh.material = newMat;
            } else {
                firstSubmesh.material = mat;
            }
        }
    }
}



// socialShareLink puzzle
function socialShareLink(media, title, text) {

    function fixedEncodeURIComponent(str) {
        return encodeURIComponent(str).replace(/[!'()*]/g, function(c) {
            return '%' + c.charCodeAt(0).toString(16);
        });
    }

    switch(media) {
    case 'TWITTER':
        return 'https://twitter.com/intent/tweet?url=' +
            fixedEncodeURIComponent(window.location.href) +
            '&text=' + fixedEncodeURIComponent(title);
    case 'FB':
        return 'http://www.facebook.com/sharer.php?u=' +
            fixedEncodeURIComponent(window.location.href);
    case 'REDDIT':
        return 'https://reddit.com/submit?url=' +
            fixedEncodeURIComponent(window.location.href) +
            '&title=' + fixedEncodeURIComponent(title);
    case 'LINKEDIN':
        return 'https://www.linkedin.com/shareArticle?mini=true&url=' +
            fixedEncodeURIComponent(window.location.href) +
             '&title=' + fixedEncodeURIComponent(title) +
             '&summary=' + fixedEncodeURIComponent(text);
    case 'VK':
        return 'http://vk.com/share.php?url=' +
            fixedEncodeURIComponent(window.location.href) +
            '&title=' + fixedEncodeURIComponent(title) +
            '&comment=' + fixedEncodeURIComponent(text);
    case 'WEIBO':
        return 'http://service.weibo.com/share/share.php?url=' +
            fixedEncodeURIComponent(window.location.href) +
            '&title=' + fixedEncodeURIComponent(title);
    }
}



// openWebPage puzzle
function openWebPage(url, mode) {

    if (appInstance && appInstance.controls) {
        appInstance.controls.forceMouseUp();
    }

    if (mode == "NEW") {
        window.open(url);
    } else if (mode == "NO_RELOAD") {
        history.pushState('verge3d state', 'verge3d page', url);
    } else {
        var target;
        switch (mode) {
            case "SAME":
                target = "_self";
                break;
            case "TOP":
                target = "_top";
                break;
            case "PARENT":
                target = "_parent";
                break;
        }
        if (typeof window.PE != "undefined") {
            if (window.confirm("Are you sure you want to leave Puzzles?"))
                window.open(url, target);
        } else {
            window.open(url, target);
        }
    }
}



// autoRotateCamera puzzle
function autoRotateCamera(enabled, speed) {

    if (appInstance.controls && appInstance.controls instanceof v3d.OrbitControls) {
        appInstance.controls.autoRotate = enabled;
        appInstance.controls.autoRotateSpeed = speed;
    } else {
        console.error('autorotate camera: Wrong controls type');
    }
}



// setTimer puzzle
function registerSetTimer(id, timeout, callback, repeat) {

    if (id in _pGlob.intervalTimers) {
        window.clearInterval(_pGlob.intervalTimers[id]);
    }

    _pGlob.intervalTimers[id] = window.setInterval(function() {
        if (repeat-- > 0) {
            callback(_pGlob.intervalTimers[id]);
        }
    }, 1000 * timeout);
}



// eventHTMLElem puzzle
function eventHTMLElem(eventType, ids, isParent, callback) {
    var elems = getElements(ids, isParent);
    for (var i = 0; i < elems.length; i++) {
        var elem = elems[i];
        if (!elem)
            continue;
        elem.addEventListener(eventType, callback);
        if (v3d.PL.editorEventListeners)
            v3d.PL.editorEventListeners.push([elem, eventType, callback]);
    }
}



refraction('gem_outside', 0.17, ['ring_01', 'ring_02', 'ring_03', 'ring_04']);

bloom(0.98, 0.6, 0.5);
parts_cost = [40, 100];
checkout_list = ['Silver ', 'ring with three small gems.'];
price_recount();
setHTMLElemStyle('display', 'none', 'fullscreen_button', false);

registerOnClick('button_2', false, false, [0,1,2], function() {
  changeVis(['GROUP', 'everything'], false);
  changeVis(['ring_02', 'gem_01_outside', 'gem_01_inside', 'gem_02_outside', 'gem_02_inside'], true);
  parts_cost[1] = 140;
  checkout_list[1] = 'ring with three small gems.';
  price_recount();
}, function() {});

registerOnClick('button_1', false, false, [0,1,2], function() {
  changeVis(['GROUP', 'everything'], false);
  changeVis(['ring_01', 'gem_01_outside', 'gem_01_inside'], true);
  parts_cost[1] = 100;
  checkout_list[1] = 'ring with one small gem.';
  price_recount();
}, function() {});

registerOnClick('order_button', false, false, [0,1,2], function() {
  final_cost = parts_cost[0] + parts_cost[1];
  placeOrder('https://sandbox.soft8soft.com/order-form/', 'Jewelry configurator', 'Your order is: ' + String(String(checkout_list[0]) + String(checkout_list[1])), String(final_cost) + '$', true);}, function() {});

registerOnClick('button_3', false, false, [0,1,2], function() {
  changeVis(['GROUP', 'everything'], false);
  changeVis(['ring_03', 'gem_03_outside', 'gem_03_inside'], true);
  parts_cost[1] = 180;
  checkout_list[1] = 'ring with one big gem.';
  price_recount();
}, function() {});

registerOnClick('button_4', false, false, [0,1,2], function() {
  changeVis(['GROUP', 'everything'], false);
  changeVis(['ring_04', 'gem_03_outside', 'gem_03_inside'], true);
  parts_cost[1] = 200;
  checkout_list[1] = 'ring with one fastened big gem.';
  price_recount();
}, function() {});

registerOnHover(['button_1', 'button_2', 'button_3', 'button_4', 'button_5', 'button_6', 'button_7', 'facebook_button', 'linkedin_button', 'order_button', 'twitter_button'], false, function() {
  setHTMLElemStyle('cursor', 'pointer', ['BODY'], false);
}, function() {
  setHTMLElemStyle('cursor', 'default', ['BODY'], false);
});

registerOnClick('button_5', false, false, [0,1,2], function() {
  assignMat(['GROUP', 'metal parts'], 'gold_material');
  parts_cost[0] = 80;
  checkout_list[0] = 'Gold ';
  price_recount();
}, function() {});

registerOnClick('button_6', false, false, [0,1,2], function() {
  assignMat(['GROUP', 'metal parts'], 'silver_material');
  parts_cost[0] = 40;
  checkout_list[0] = 'Silver ';
  price_recount();
}, function() {});

registerOnClick('button_7', false, false, [0,1,2], function() {
  assignMat(['GROUP', 'metal parts'], 'pink_gold_material');
  parts_cost[0] = 70;
  checkout_list[0] = 'Pink gold ';
  price_recount();
}, function() {});

registerOnClick('facebook_button', false, false, [0,1,2], function() {
  openWebPage(socialShareLink('FB', '3D Jewelry Configurator', 'Interactive jewelry configurator made with Verge3D. Design your own precious ring now!'), 'NEW');
}, function() {});

eventHTMLElem('click', ['WINDOW'], false, function(event) {
  autoRotateCamera(false, 2);
  registerSetTimer('autorotate_delay', 3, function() {
    autoRotateCamera(true, 2);
  }, Infinity);
});
registerSetTimer('autorotate_delay', 3, function() {
  autoRotateCamera(true, 2);
}, Infinity);

registerOnClick('linkedin_button', false, false, [0,1,2], function() {
  openWebPage(socialShareLink('LINKEDIN', '3D Jewelry Configurator', 'Interactive jewelry configurator made with Verge3D. Design your own precious ring now!'), 'NEW');
}, function() {});

registerOnClick('twitter_button', false, false, [0,1,2], function() {
  openWebPage(socialShareLink('TWITTER', '3D Jewelry Configurator', 'Interactive jewelry configurator made with Verge3D. Design your own precious ring now!'), 'NEW');
}, function() {});



} // end of PL.init function

})(); // end of closure

/* ================================ end of code ============================= */
