<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaNewApp</%block>

<%block name="blkDialogHeader">
  Create New App
</%block>

<%block name="blkDialogContent">
  <form action="" class="new-app-cont" id="newAppForm">
    <div class="dialog-text">Displayed Name:</div>
    <span title="Displayed app name"><input type="text" id="appNameDisp" name="app_name_disp" value="My Awesome App" class="new-app-disp-name" readonly></span>

    <div class="dialog-text">Directory Name:</div>
    <span title="Name used for app directory and files"><input type="text" id="appName" name="app_name" value="my_awesome_app" class="new-app-name"></span>

    <div class="new-app-frame">
      <div class="new-app-types">
        <div class="dialog-text">App Template:</div>

        % for at in appTemplates:
          <div title="${at['description']}">
            <input type="radio" name="template_name" value="${at['name']}" ${'checked' if loop.first else ''} class="new-app-radio">${at['name']}
          </div>
        % endfor
      </div>

      <div class="new-app-modules">
        <div class="dialog-text">Modules:</div>

        <div title="Opentype.js font parsing library">
          <input type="checkbox" name="copy_opentype_module" value="1" class="new-app-checker" checked>
          Font Converter
        </div>
        <div title="Add Internet Explorer 11 compatibility support module">
          <input type="checkbox" name="copy_ie11_module" value="1" class="new-app-checker">
          IE 11
        </div>
        <div title="Add legacy VR compatibility module for older browsers which do not support WebXR technology">
          <input type="checkbox" name="copy_ar_vr_module" value="1" class="new-app-checker">
          Legacy VR
        </div>
        <div title="Add module to enable Physics Puzzles and Ammo.js API">
          <input type="checkbox" name="copy_physics_module" value="1" class="new-app-checker">
          Physics
        </div>
      </div>
    </div>

    <input type="submit" value="Create App" class="button">
  </form>
</%block>

<%block name="blkDialogScript">
  ${parent.blkDialogScript()}

  newAppForm.addEventListener('submit', function(event) {
      var newAppFormData = new FormData(newAppForm);

      makeRequest('/create/', newAppFormData, function(response) {
          closeDialog('diaNewApp');

          var dia = appendDialog(response);
          openDialog(dia);
      });

      event.preventDefault();
  });

  appName.addEventListener('keyup', function() {
      appNameDisp.value = capitalizeFirstLetters(appName.value.replace(/_/g, ' '));
  });

</%block>
