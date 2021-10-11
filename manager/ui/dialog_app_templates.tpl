<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaAppTemplates</%block>

<%block name="blkDialogHeader">
  App Templates
</%block>

<%block name="blkDialogContent">
  <div id="appTemplatesCont">
    % for template in settings['appTemplates']:
      <div class="app-template-item">
        <input type="text" name="name" value="${template['name']}" class="">
        <textarea name="description" cols="40" rows="2" class="app-template-description-area">${template['description']}</textarea>
        <a class="app-template-delete"></a>
      </div>
    % endfor
  </div>

  <div class="two-buttons">
    <div>
      <button class="button app-template-button" id="appTemplateNew" title="Append new application template"><span class="app-template-new"></span>Template</button>
    </div>
    <div>
        <button class="button app-template-button" id="appTemplatesSave" title="Save application templates and close the window">Apply</button>
    </div>
  </div>


</%block>

<%block name="blkDialogScript">
    diaAppTemplatesClose.addEventListener('click', function() {
        destroyDialog('diaAppTemplates');
    });

    appTemplatesSave.addEventListener('click', function() {
        saveTemplates();
    });

    focusElem('appTemplatesSave');

    function saveTemplates() {
        var appTemplates = [];

        diaAppTemplates.querySelectorAll('div.app-template-item').forEach(function(elem) {

            var name = elem.querySelector('[name="name"]').value;

            if (name) {
                appTemplates.push({
                    'name': name,
                    'description': elem.querySelector('[name="description"]').value
                });
            }
        });

        var jsonData = JSON.stringify({appTemplates: appTemplates});

        makeRequest('/settings/save', jsonData, function(response) {
            destroyDialog('diaAppTemplates');
            document.location.reload(true);
        });
    }

    appTemplateNew.addEventListener('click', function(event) {
        appTemplatesCont.insertAdjacentHTML('beforeend', '\
            <div class="app-template-item">\
              <input type="text" name="name" value="My App Template" class="">\
              <textarea name="description" cols="40" rows="2" class="app-template-description-area">This is my new application template</textarea>\
              <a class="app-template-delete"></a>\
            </div>\
        ');

        event.preventDefault();
    });

    diaAppTemplates.addEventListener('click', function(event) {
        var elem = event.target
        if (elem.classList.contains('app-template-delete')) {
            appTemplatesCont.removeChild(elem.parentElement);
        }
    });

</%block>
