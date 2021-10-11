<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaNewAppCreated</%block>

<%block name="blkDialogHeader">
  App created
</%block>

<%block name="blkDialogContent">
  <div class="dialog-text-center">
    Application <a href="${manageURL}" class="colored-link">${nameDisp}</a> has been successfully created.
  </div>

  <button id="diaNewAppCreatedOk" class="button">Yay!</button>
</%block>

<%block name="blkDialogScript">
  diaNewAppCreated.addEventListener('click', function() {
      destroyDialog('diaNewAppCreated');
      document.location.reload(true);
  });

  focusElem('diaNewAppCreatedOk');
</%block>
