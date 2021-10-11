(function() {

var DIALOG_ICONS_MAP = {
    'diaNewApp': 'toolbar-icon-new-app',
    'diaAppTemplates': 'toolbar-icon-templates',
    'diaSettings': 'toolbar-icon-settings',
    'diaLicense': 'toolbar-icon-license',
    'diaLicenseKey': 'toolbar-icon-license',
    'diaHelp': 'toolbar-icon-help',
    'diaAbout': 'toolbar-icon-about',
}

var VERSION_URL = 'https://www.soft8soft.com/verge3d-' + appManager.package.toLowerCase() + '-latest.json?' + Date.now();

function parseVersion(text) {
    version = [0, 0, 0, 0];

    dotSplit = text.split('.');

    preSplit = dotSplit[2].split('pre');
    alphaSplit = preSplit[0].split('alpha');

    version[0] = +dotSplit[0];
    version[1] = +dotSplit[1];
    version[2] = +alphaSplit[0];

    if (preSplit.length > 1)
        version[3] = +preSplit[1];
    else if (alphaSplit.length > 1)
        // alpha release comes before pre release
        version[3] = +alphaSplit[1] - 1000;
    else
        // stable release is more recent than pre/alpha release
        version[3] = 1000;

    return version;
}

/**
 *  1 v1 > v2
 *  0 v1 = v2
 * -1 v1 < v2
 */
function compareVersions(v1, v2) {

    for (var i = 0; i < 4; i++) {
        var sign = Math.sign(v1[i] - v2[i]);
        if (sign)
            return sign;
    }

    return 0;
}

function checkForUpdates() {
    function reqListener() {
        if (this.status == 200) {
            var info = JSON.parse(this.responseText);

            var v1 = parseVersion(info.version);
            var v2 = parseVersion(appManager.version);

            if (compareVersions(v1, v2) > 0) {
                newVersionAvailDot.classList.remove('hidden');

                newVersionPostfix.classList.remove('hidden');
                newVersionPostfix.innerHTML = '(<a href="' + info.release_notes +
                        '" target="_blank" >update ' + info.version + ' available!)</a>'
            }
        }
    }

    var req = new XMLHttpRequest();
    req.addEventListener('load', reqListener);
    req.open('GET', VERSION_URL);
    req.send();
}

function updateFilter() {

    var regExp = new RegExp(filterInput.value, 'gi');

    var items = document.getElementsByClassName('filterable');

    for (var i = 0; i < items.length; i++) {
        var item = items[i];

        var filterResults = item.textContent.match(regExp);

        if (filterResults && filterResults.length > 0) {

            item.classList.remove('hidden');

        } else {

            item.classList.add('hidden');

        }

    }

}

function applyTableHeightHack() {
    var bannerHeight = document.querySelector('.main-panel div.banner').offsetHeight;
    var tableHeight = document.querySelector('.main-panel table').offsetHeight;

    document.querySelectorAll('.main-panel table tbody').forEach(function(tableBody) {

        var rowHeight = window.innerHeight - bannerHeight - tableHeight;

        if (rowHeight > 0) {
            tableBody.insertAdjacentHTML('beforeend', '<tr style="height:' + rowHeight + 'px"></tr>');
        }

    });
}

function init() {

    window.addEventListener('load', function() {
        if (appManager.checkForUpdates)
            checkForUpdates();

        filterInput.addEventListener('input', function() {
            updateFilter();
        });

        handleDialogEscape('diaAbout', false);
        handleDialogEscape('diaAppTemplates', true);
        handleDialogEscape('diaDeleteConfirm', true);
        handleDialogEscape('diaDelete', true);
        handleDialogEscape('diaError', true);
        handleDialogEscape('diaHelp', false);
        handleDialogEscape('diaLicense', false);
        handleDialogEscape('diaLicenseKey', false);
        handleDialogEscape('diaLicenseKeyDone', true);
        handleDialogEscape('diaNetworkDelete', true);
        handleDialogEscape('diaNetworkError', true);
        handleDialogEscape('diaNewApp', false);
        handleDialogEscape('diaNewAppCreated', true);
        handleDialogEscape('diaPublishing', false);
        handleDialogEscape('diaPublished', true);
        handleDialogEscape('diaQrCode', false);
        handleDialogEscape('diaSettings', true);
        handleDialogEscape('diaUpdate', true);
        handleDialogEscape('diaUpdateDone', true);

        applyTableHeightHack();
    });
}

window.capitalizeFirstLetters = function(str) {
    return str.toLowerCase().replace(/^\w|\s\w/g, function (letter) {
        return letter.toUpperCase();
    });
}

window.toggleCollapsible = function(elem) {
    switch (elem.className) {
    case 'app-collapsed':
        elem.className = 'app-expanded';
        elem.parentElement.parentElement.querySelectorAll('.app-icon-cut').forEach(function(cutElem) {
            cutElem.classList.remove('hidden');
        });
        break;
    case 'app-expanded':
        elem.className = 'app-collapsed';
        elem.parentElement.parentElement.querySelectorAll('.app-icon-cut').forEach(function(cutElem) {
            cutElem.classList.add('hidden');
        });
        break;
    default:
        break;
    }
}

window.focusElem = function(id) {
    setTimeout(function() {
        document.getElementById(id).focus();
    }, 0);
}

window.openDialog = function(id) {
    document.getElementById(id).style.display = 'flex';

    setActiveToolbar(DIALOG_ICONS_MAP[id]);
}

window.closeDialog = function(id) {
    document.getElementById(id).style.display = 'none';
    setActiveToolbar();
}

window.isDialogOpen = function(id) {
    var elem = document.getElementById(id);
    return (elem && elem.style.display !== 'none')
}

window.appendDialog = function(code) {
    document.body.insertAdjacentHTML('beforeend', code);
    var dia = document.body.lastElementChild;
    var scriptElem = dia.getElementsByTagName('script')[0];
    if (scriptElem)
        eval(scriptElem.innerHTML);
    else
        console.error('Missing dialog script, check your template for errors!');
    return dia.id;
}

window.destroyDialog = function(id) {
    document.getElementById(id).parentNode.removeChild(document.getElementById(id));
    setActiveToolbar();
}

window.makeRequest = function(url, data, callback) {
    var req = new XMLHttpRequest();

    if (data) {
        req.open('POST', url);
        req.send(data);
    } else {
        req.open('GET', url);
        req.send();
    }

    if (callback) {
        req.addEventListener('load', function() {
            callback(this.responseText);
        });
    }
}

window.openFile = function(url) {
    var req = new XMLHttpRequest();
    req.open('GET', '/open/?filepath=' + url);
    req.send();
}

window.deleteApp = function(app) {
    makeRequest('/delete_confirm/?app=' + app, null, function(response) {
        var dia = appendDialog(response);
        openDialog(dia);
    });
}

window.updateApp = function(app, appIconElem) {

    // save to change class without reloading the page
    appManager.updatedAppIconElem = appIconElem || null;

    makeRequest('/update_app_info/?app=' + app, null, function(response) {
        var dia = appendDialog(response);
        openDialog(dia);
    });
}

window.publishApp = function(app, isZip) {

    var percentageTimer = null;

    function reqListener(response) {
        closeDialog('diaPublishing');
        clearTimeout(percentageTimer);

        var dia = appendDialog(response);
        openDialog(dia);
    }

    function percentageListener() {
        var percentage = document.getElementById('publishingPercentage');
        percentage.innerHTML = Math.round(this.responseText || 0) + '%';

        percentageTimer = window.setTimeout(function() {
            var req = new XMLHttpRequest();
            req.addEventListener('load', percentageListener);
            req.open('GET', '/storage/net/?req=progress');
            req.send();
        }, 300)
    }

    openDialog('diaPublishing')
    percentageListener();

    makeRequest('/storage/net/?req=upload&app=' + app + '&zip=' + (isZip ? '1' : '0'), null, reqListener);
}

window.createQRCode = function(url) {
    var typeNumber = 0;
    var errorCorrectionLevel = 'L';
    var qr = qrcode(typeNumber, errorCorrectionLevel);
    qr.addData(url);
    qr.make();
    return qr.createDataURL(7);
}

window.createNativeApp = function(app) {
    openDialog('diaCreateNativeApp');
}

window.openSettingsDialog = function(isAppTemplates) {
    makeRequest('/settings/' + (isAppTemplates ? 'templates/' : ''), null, function(response) {
        var dia = appendDialog(response);
        openDialog(dia);
    });
}

window.copyTextArea = function(id) {
    var elem = document.getElementById(id);
    elem.select();
    document.execCommand('copy');
    elem.selectionStart = 0;
    elem.selectionEnd = 0;
}

/**
 * Activates home/network icon if class not specified
 */
window.setActiveToolbar = function(className) {

    if (!className) {
        if (window.location.pathname.indexOf('/storage/net') > -1)
            className = 'toolbar-icon-network';
        else if (window.location.pathname.indexOf('/manage') > -1)
            className = 'reserved-empty-class';
        else
            className = 'toolbar-icon-home';
    }

    document.querySelectorAll('.toolbar a').forEach(function(icon) {
        if (icon.classList.contains(className))
            icon.classList.add('toolbar-icon-active');
        else
            icon.classList.remove('toolbar-icon-active');
    });
}

window.handleDialogEscape = function(dialogID, doDestroy) {
    document.addEventListener('keydown', function(event) {
        if (event.keyCode == 27 && isDialogOpen(dialogID)) {
            if (doDestroy)
                destroyDialog(dialogID);
            else
                closeDialog(dialogID);
        }
    });
}

init();

})(); // end of closure



